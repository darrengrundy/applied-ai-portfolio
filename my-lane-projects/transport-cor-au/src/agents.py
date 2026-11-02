"""Claude agents over the engine's findings.

analyst  -> per driver: decision, root cause, accountable party, action, explanation per issue
critic   -> checks every claim against the engine facts; must name a concrete error to send work back
patterns -> 4-week systemic issues
briefing -> the 05:30 dispatch briefing

The engine sets every colour and number. Agents explain and assign; they never recolour.
python src/agents.py --data data --findings build/findings.json --out build/agents.json
"""
from __future__ import annotations

import argparse, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_tower import patterns as find_patterns, CUST  # noqa: E402

MODEL = os.environ.get("COR_MODEL", "claude-haiku-5-5")
MAX_REVISIONS = 2

DECISIONS = {
    "HOLD": "Do not release until something about this trip is fixed (load, weight, gear, person, evidence).",
    "RESCHEDULE": "Change the time, driver or vehicle; the trip itself can still run.",
    "RELEASE_WITH_CONDITIONS": "Can go once one named pre-departure step is done.",
    "INVESTIGATE": "Something already happened that must be explained before relying on the records.",
    "MONITOR": "Can go; the follow-up sits outside this trip.",
    "RELEASE": "No action needed.",
}
ROOT_CAUSES = {
    "ROSTER_PLANNING": "the roster or schedule itself creates the problem",
    "CUSTOMER_WINDOW": "a customer's delivery or dock window drives the pressure",
    "CONSIGNOR_DECLARATION": "the consignor's paperwork (declared weight, documents) is wrong",
    "LOADING_PRACTICE": "how the load is packed or restrained",
    "TRAINING_LAPSE": "a competency or training record has lapsed or is about to",
    "EQUIPMENT_CONTROL": "failed restraint gear was not tagged out",
    "MAINTENANCE_PLANNING": "service scheduling and workshop bookings",
    "DEFECT_CONTROL": "a reported defect was not cleared before use",
    "DRIVER_BEHAVIOUR": "an individual driver's conduct",
    "DATA_QUALITY": "system data is wrong or missing (map limits, telematics feeds)",
    "RECORD_KEEPING": "required records are missing or do not match",
}
PARTIES = {
    "scheduler": "builds rosters and dispatch plans",
    "loader": "loads, packs, weighs and restrains",
    "consignor": "the customer sending the goods, incl. declared weights and delivery windows",
    "operator": "fleet, compliance and training management at the operator",
    "driver": "the driver",
    "executive": "officers with due-diligence duties",
    "data_owner": "owner of telematics, maps and systems data",
}

ANALYST_SYS = f"""You are a Chain of Responsibility (CoR) analyst for an Australian heavy vehicle operator, preparing the 05:30 before-start check.
You receive one driver's planned trips, the findings a deterministic rule engine produced (colour, facts, basis) and fleet-wide patterns from the last four weeks.

Rules:
- The engine's colour is final. Never change it, and never release a RED issue (RELEASE or RELEASE_WITH_CONDITIONS are not allowed for RED).
- Use only numbers, dates and names that appear in the input. Do not calculate new figures. If a figure is not in the facts, leave it out.
- Give one assessment per area that has findings for this driver, and only for those areas. Combine findings from the same area.
  Fleet patterns are context for the cause; never write an assessment from a pattern alone.
- A pattern applies only to trips that match its `applies_to` (same customer, or this driver at that location). Do not link a pattern to an unrelated trip.
- Name the party who can remove the cause, not only the person nearest the event. Use the fleet patterns: if the same problem appears across several drivers or loads, the cause usually sits upstream (scheduler, consignor, operator).
- Write for a busy controller: plain words, short sentences, no legal advice.

Decisions: {json.dumps(DECISIONS)}
Root causes: {json.dumps(ROOT_CAUSES)}
Parties: {json.dumps(PARTIES)}"""

CRITIC_SYS = """You review a CoR analyst's assessment against the rule engine's facts. Check, for each assessment:
1. Every number, time, date and name in `action` and `explanation` appears in the input facts or trips.
2. The decision respects the colour: RED may not be RELEASE or RELEASE_WITH_CONDITIONS.
3. The root cause and accountable party are supported by the facts or the fleet patterns.
4. Each cited fact exists and says what the explanation claims.
For each item you list, set is_error true only for a concrete error: quote the exact wrong text and the fact it conflicts with. Do not list things that are correct. Style preferences, wording and alternative reasonable choices are not errors. If nothing is concretely wrong, pass."""

ASSESS_TOOL = {
    "name": "submit_assessment",
    "description": "Submit the assessment for this driver.",
    "input_schema": {
        "type": "object",
        "properties": {
            "assessments": {"type": "array", "items": {"type": "object", "properties": {
                "area": {"type": "string"},
                "finding_ids": {"type": "array", "items": {"type": "string"}},
                "decision": {"type": "string", "enum": list(DECISIONS)},
                "root_cause": {"type": "string", "enum": list(ROOT_CAUSES)},
                "accountable_parties": {"type": "array", "items": {"type": "string", "enum": list(PARTIES)}, "minItems": 1},
                "action": {"type": "string", "description": "One imperative sentence, under 20 words."},
                "explanation": {"type": "string", "description": "Under 60 words: what the evidence shows and why the cause sits where it does."},
                "cited_facts": {"type": "array", "items": {"type": "object", "properties": {
                    "finding_id": {"type": "string"}, "key": {"type": "string"}}, "required": ["finding_id", "key"]}},
            }, "required": ["area", "finding_ids", "decision", "root_cause", "accountable_parties", "action", "explanation", "cited_facts"]}},
            "driver_summary": {"type": "string", "description": "Under 25 words."},
        },
        "required": ["assessments", "driver_summary"],
    },
}
REVIEW_TOOL = {
    "name": "submit_review",
    "description": "Submit the review.",
    "input_schema": {"type": "object", "properties": {
        "verdict": {"type": "string", "enum": ["pass", "revise"]},
        "errors": {"type": "array", "items": {"type": "object", "properties": {
            "area": {"type": "string"}, "quote": {"type": "string"}, "problem": {"type": "string"},
            "is_error": {"type": "boolean", "description": "true only if the quoted text is concretely wrong"}},
            "required": ["area", "quote", "problem", "is_error"]}},
    }, "required": ["verdict", "errors"]},
}
PATTERN_TOOL = {
    "name": "submit_patterns",
    "description": "Submit systemic issues.",
    "input_schema": {"type": "object", "properties": {"issues": {"type": "array", "items": {"type": "object", "properties": {
        "title": {"type": "string"}, "evidence": {"type": "string"}, "root_cause": {"type": "string", "enum": list(ROOT_CAUSES)},
        "accountable_parties": {"type": "array", "items": {"type": "string", "enum": list(PARTIES)}},
        "recommendation": {"type": "string"}}, "required": ["title", "evidence", "root_cause", "accountable_parties", "recommendation"]}}},
        "required": ["issues"]},
}


class Client:
    def __init__(self):
        key = os.environ.get("ANTHROPIC_API_KEY")
        env = Path(__file__).resolve().parents[1] / ".env"
        if not key and env.exists():
            key = env.read_text().split("=", 1)[1].strip().strip("'\"")
        self.c = anthropic.Anthropic(api_key=key, max_retries=4)
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0}

    def review(self, system, user):
        rev = self.tool(system, user, REVIEW_TOOL)
        rev["errors"] = [e for e in rev.get("errors", []) if e.get("is_error")]
        rev["verdict"] = "revise" if rev["errors"] else "pass"
        return rev

    def tool(self, system, user, tool, max_tokens=6000):
        r = self.c.messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                                   tools=[tool], tool_choice={"type": "tool", "name": tool["name"]},
                                   messages=[{"role": "user", "content": user}])
        self.usage["calls"] += 1
        self.usage["input_tokens"] += r.usage.input_tokens
        self.usage["output_tokens"] += r.usage.output_tokens
        return next(b.input for b in r.content if b.type == "tool_use")

    def text(self, system, user, max_tokens=6000):
        for _ in range(3):  # an occasional reply is all reasoning and no text; retry
            r = self.c.messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                                       messages=[{"role": "user", "content": user}])
            self.usage["calls"] += 1
            self.usage["input_tokens"] += r.usage.input_tokens
            self.usage["output_tokens"] += r.usage.output_tokens
            if r.stop_reason == "max_tokens":
                max_tokens = min(max_tokens * 2, 32000)
                continue
            if "".join(b.text for b in r.content if b.type == "text").strip():
                break
        return "".join(b.text for b in r.content if b.type == "text")


# --------------------------------------------------------------------------
def packets(d, out):
    """One input packet per driver with any non-green trip."""
    drivers = {x["id"]: x for x in d["drivers"]}
    fs = {f["id"]: f for f in out["findings"]}
    mv_raw = {m["id"]: m for m in d["movements"]}
    byd = {}
    for m in out["movements"]:
        for did in (m["driver_id"], m.get("co_driver_id")):
            if did:
                byd.setdefault(did, []).append(m)
    pk = []
    for did, ms in byd.items():
        fids = sorted({i for m in ms for i in m["findings"]})
        if not fids:
            continue
        pk.append(dict(
            driver=dict(id=did, name=drivers[did]["name"], scheme=drivers[did]["scheme"]),
            trips=[dict(id=m["movement_id"], colour=m["rag"], depart=m["depart"], destination=m["destination"],
                        delivery_slot=mv_raw[m["movement_id"]]["arrive_window"], plan_change=mv_raw[m["movement_id"]].get("plan_change"),
                        vehicle=m["vehicle_id"], trailer=m["trailer_id"], customer=CUST[m["customer_id"]], load=m["load_type"],
                        co_driver=drivers[m["co_driver_id"]]["name"] if m.get("co_driver_id") and m["co_driver_id"] != did else None)
                   for m in sorted(ms, key=lambda m: m["depart"])],
            findings=[dict(id=i, colour=fs[i]["rag"], area=fs[i]["area"], rule=fs[i]["rule_id"], title=fs[i]["title"],
                           facts=fs[i]["facts"], basis=fs[i]["source"], limits=fs[i]["limits"]) for i in fids]))
    return pk


NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def ungrounded_numbers(text, packet, extra=None):
    """Numbers in agent text that do not occur anywhere in the packet (deterministic grounding check)."""
    hay = json.dumps([packet, extra], ensure_ascii=False)
    hay_n = set(n.replace(",", "") for n in NUM.findall(hay))
    # allow derived forms that appear in titles, e.g. "06:00" -> "06", "00"
    bad = []
    for n in NUM.findall(text):
        k = n.replace(",", "").rstrip(".")
        if k and k not in hay_n and k.rstrip("0").rstrip(".") not in {h.rstrip("0").rstrip(".") for h in hay_n}:
            bad.append(n)
    return bad


# rest hours each fatigue rule refers to, by hours option (ref/sources.md F1, F2)
REST_HOURS = {
    "FAT-24H-REST": {"solo": {7}, "two_up": {5}}, "FAT-24H-WORK": {"solo": {7}, "two_up": {5}},
    "FAT-52H-REST": {"two_up": {10}}, "FAT-7D-REST": {"solo": {24}, "two_up": {24}},
    "FAT-7D-WORK": {"solo": {24}, "two_up": {24}}, "FAT-7D-BLOCKS": {"two_up": {7, 24}},
    "FAT-14D-NIGHTS": {"solo": {7, 24}, "two_up": {7, 24}}, "FAT-HEADROOM": {"solo": {7}, "two_up": {5}},
}
WORK_LIMITS = {"solo": {5.25, 7.5, 10, 12, 72, 144}, "two_up": {5.25, 7.5, 10, 12, 60, 120}}
REST_RE = re.compile(r"(?<![\w.-])(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hour|hours)\b(?:[\s-]+(?:continuous|major|stationary|night))*[\s-]+rest", re.I)
LIMIT_RE = re.compile(r"(?<![\w.-])(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hour|hours)\b(?:\s+(?:work|of work))?\s+(?:limit|maximum|max)\b|"
                      r"\b(?:limit|maximum|max)\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hours)\b", re.I)
PERIODS = {5.5, 8, 11, 24, 52}  # counting periods (hours), never work limits themselves
PERIOD_BEFORE = re.compile(r"(?:\bin|\bper|\bwithin|-in|\bany)[\s-]*$", re.I)
WEEKDAY_RE = re.compile(r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\.?,?\s+(\d{1,2})\s+(Oct|Nov)[a-z]*\b", re.I)


def weekday_mismatches(text, year=2026):
    """'Tuesday 2 Nov' when 2 Nov 2026 is a Monday."""
    from datetime import date
    bad = []
    for m in WEEKDAY_RE.finditer(text):
        d = date(year, 10 if m.group(3).lower().startswith("oct") else 11, int(m.group(2)))
        if d.strftime("%a").lower() != m.group(1).lower()[:3]:
            bad.append(f"'{m.group(0)}': {d.day} {d:%b} {year} is a {d:%A}")
    return bad


def rule_mismatches(x, packet):
    """Fatigue only: rest hours and work limits quoted must belong to this driver's hours option and rules."""
    if x["area"] != "Fatigue":
        return []
    scheme = packet["driver"]["scheme"]
    rules = {f["rule"] for f in packet["findings"] if f["area"] == "Fatigue"}
    rest_ok = set().union(*[REST_HOURS.get(r, {}).get(scheme, set()) for r in rules]) or {7 if scheme == "solo" else 5}
    text = x["action"] + " " + x["explanation"]
    bad = []
    for m in REST_RE.finditer(text):
        if re.match(r"\s*(?:window|period)", text[m.end():], re.I):
            continue  # "24 h rest window" names the period
        if float(m.group(1)) not in rest_ok:
            bad.append(f"'{m.group(0)}': the {scheme.replace('_', '-')} rule here is {' or '.join(f'{h:g} h' for h in sorted(rest_ok))} rest")
    for m in LIMIT_RE.finditer(text):
        if PERIOD_BEFORE.search(text[:m.start()]):
            continue  # "12 h work in 24 h limit": 24 h is the period, not the limit
        v = float(m.group(1) or m.group(2))
        if v in PERIODS:
            continue  # "the 24 h work limit" means the limit for a 24 h period
        if v not in WORK_LIMITS[scheme]:
            bad.append(f"'{m.group(0)}': not a {scheme.replace('_', '-')} standard-hours work limit")
    return bad


def enforce_floor(a, packet):
    """Code-level guard: RED issues are never released, and invalid decisions never pass through."""
    col = {f["id"]: f["colour"] for f in packet["findings"]}
    fixes = []
    for x in a["assessments"]:
        if x.get("root_cause") not in ROOT_CAUSES:
            fixes.append((x["area"], f"root_cause {x.get('root_cause')}"))
            x["root_cause_model"], x["root_cause"] = x.get("root_cause"), "UNCLASSIFIED"
        bad = [p for p in x.get("accountable_parties", []) if p not in PARTIES]
        if bad:
            fixes.append((x["area"], f"parties {bad}"))
            x["accountable_parties"] = [p for p in x["accountable_parties"] if p in PARTIES] or ["operator"]
        worst = "RED" if any(col.get(i) == "RED" for i in x["finding_ids"]) else "AMBER"
        x["colour"] = worst
        if x["decision"] not in DECISIONS or (worst == "RED" and x["decision"] in ("RELEASE", "RELEASE_WITH_CONDITIONS", "MONITOR")):
            fixes.append((x["area"], x["decision"]))
            x["decision_model"] = x["decision"]
            x["decision"] = "HOLD" if worst == "RED" else "MONITOR"
    return fixes


def analyse(cl, packet, pats):
    user = json.dumps(dict(**packet, fleet_patterns=pats), ensure_ascii=False, indent=1)
    msgs = user
    log = []
    a = cl.tool(ANALYST_SYS, msgs, ASSESS_TOOL)
    areas = {f["area"] for f in packet["findings"]}
    for rnd in range(MAX_REVISIONS + 1):
        a["assessments"] = [x for x in a["assessments"] if x["area"] in areas]
        nums = {x["area"]: ungrounded_numbers(x["action"] + " " + x["explanation"], packet, pats) for x in a["assessments"]}
        rev = cl.review(CRITIC_SYS, f"INPUT:\n{user}\n\nASSESSMENT:\n{json.dumps(a, indent=1)}\n\n"
                                    f"Numbers not found anywhere in the input (from an automatic check): {json.dumps(nums)}")
        for x in a["assessments"]:  # deterministic rule check: these are errors whatever the reviewer says
            for b in rule_mismatches(x, packet) + weekday_mismatches(x["action"] + " " + x["explanation"]):
                rev["errors"].append(dict(area=x["area"], quote=b.split("'")[1], problem=b, is_error=True, source="rule check"))
        rev["verdict"] = "revise" if rev["errors"] else "pass"
        log.append(dict(round=rnd, verdict=rev["verdict"], errors=rev.get("errors", []), ungrounded=nums))
        if rev["verdict"] == "pass" or rnd == MAX_REVISIONS:
            break
        a = cl.tool(ANALYST_SYS, f"{user}\n\nYour previous assessment:\n{json.dumps(a, indent=1)}\n\n"
                                 f"The reviewer found these errors. Fix them and resubmit the whole assessment:\n"
                                 f"{json.dumps(rev['errors'], indent=1)}", ASSESS_TOOL)
    a["assessments"] = [x for x in a["assessments"] if x["area"] in areas]
    floor = enforce_floor(a, packet)
    final_nums = {x["area"]: ungrounded_numbers(x["action"] + " " + x["explanation"], packet, pats) for x in a["assessments"]}
    return dict(driver=packet["driver"]["id"], name=packet["driver"]["name"], assessment=a, review=log,
                floor_overrides=floor, ungrounded_final=final_nums, passed=log[-1]["verdict"] == "pass",
                rule_mismatch_final={x["area"]: rule_mismatches(x, packet) + weekday_mismatches(x["action"] + " " + x["explanation"])
                                     for x in a["assessments"]})


def pattern_agent(cl, d, out, pats):
    fs = out["findings"]
    summary = {}
    for f in fs:
        summary.setdefault(f["rule_id"], []).append(dict(entity=f["entity"], title=f["title"]))
    user = json.dumps(dict(engine_patterns=pats, todays_findings_by_rule=summary), ensure_ascii=False, indent=1)
    sys_p = ("You look across a fleet's CoR findings for systemic causes a controller would miss trip by trip. "
             "Report at most 5 issues, strongest first. Each must be supported by several findings or an engine "
             "pattern; quote counts only from the input. Describe only what the input shows: no past behaviour, "
             "motives or events that are not in it. Name the party who can remove the cause.\n"
             f"Root causes: {json.dumps(ROOT_CAUSES)}\nParties: {json.dumps(PARTIES)}")
    res = cl.tool(sys_p, user, PATTERN_TOOL)
    for _ in range(MAX_REVISIONS):
        rev = cl.review(CRITIC_SYS + " Here the 'assessment' is a list of systemic issues; apply the same checks to "
                        "`evidence` and `recommendation`, and treat any claim about events not in the input as an error.",
                        f"INPUT:\n{user}\n\nASSESSMENT:\n{json.dumps(res, indent=1)}")
        res["review"] = rev
        if rev["verdict"] == "pass":
            break
        res = cl.tool(sys_p, f"{user}\n\nYour previous answer:\n{json.dumps(res, indent=1)}\n\nFix these errors:\n"
                             f"{json.dumps(rev['errors'], indent=1)}", PATTERN_TOOL)
    return res


BRIEF_SYS = ("You write the 05:30 dispatch briefing for a transport controller. Plain text with three short sections: "
             "'Stop before release' (each RED item, earliest trips first, one line per driver or two-up pair: driver, trip "
             "time, action, owner), 'Watch today' (AMBER, one line each, grouped where they share a cause), 'Fix upstream' "
             "(systemic issues and who owns them). Under 260 words. Use only the input. Each time you mention must be a "
             "trip departure from the input; never present another timestamp as a shift or trip time. No new numbers.")


def briefing(cl, results, sys_issues, meta, trips=None):
    items = []
    for r in results:
        for x in r["assessment"]["assessments"]:
            items.append(dict(driver=r["name"], colour=x["colour"], area=x["area"], decision=x["decision"],
                              action=x["action"], parties=x["accountable_parties"],
                              trips=(trips or {}).get(r["driver"], [])))
    user = json.dumps(dict(snapshot=meta["snapshot"], items=items, systemic=sys_issues), ensure_ascii=False, indent=1)
    text = cl.text(BRIEF_SYS, user)
    review = []
    red_names = sorted({i["driver"] for i in items if i["colour"] == "RED"})
    for _ in range(MAX_REVISIONS):
        missing = [n for n in red_names if n not in text]
        rev = cl.review(CRITIC_SYS + " Here the assessment is a dispatch briefing: check every name, time and number "
                        "against the input, that each driver appears once in the right section, and that times are trip "
                        "departures.", f"INPUT:\n{user}\n\nBRIEFING:\n{text}")
        for b in weekday_mismatches(text):
            rev["errors"].append(dict(area="briefing", quote=b.split("'")[1], problem=b, is_error=True))
            rev["verdict"] = "revise"
        if missing:  # deterministic completeness check: every stopped driver must appear
            rev["errors"].append(dict(area="briefing", quote="", is_error=True,
                                      problem=f"Stopped drivers missing from the briefing: {', '.join(missing)}"))
            rev["verdict"] = "revise"
        review.append(rev)
        if rev["verdict"] == "pass":
            break
        new = cl.text(BRIEF_SYS, f"{user}\n\nYour previous briefing:\n{text}\n\nFix these errors and rewrite it:\n"
                                 f"{json.dumps(rev['errors'], indent=1)}")
        if new.strip():
            text = new
    missing = [n for n in red_names if n not in text]
    return dict(text=text, review=review, missing=missing)


def main(a):
    d = {p.stem: json.loads(p.read_text()) for p in Path(a.data).glob("*.json")}
    out = json.loads(Path(a.findings).read_text())
    pats = find_patterns(d)
    pk = packets(d, out)
    if a.limit:
        pk = pk[:a.limit]
    cl = Client()
    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        results = list(ex.map(lambda p: analyse(cl, p, pats), pk))
    sys_issues = pattern_agent(cl, d, out, pats)["issues"]
    trips = {p["driver"]["id"]: [dict(depart=t["depart"], destination=t["destination"], colour=t["colour"]) for t in p["trips"]]
             for p in pk}
    brief = briefing(cl, results, [{k: v for k, v in x.items() if k != "review"} for x in sys_issues], d["meta"], trips)
    res = dict(model=MODEL, seconds=round(time.time() - t0, 1), usage=cl.usage, drivers=results,
               systemic=sys_issues, briefing=brief["text"], briefing_review=brief["review"],
               briefing_missing=brief["missing"])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(f"{len(results)} drivers, {cl.usage}, {res['seconds']} s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--findings", default="build/findings.json")
    ap.add_argument("--out", default="build/agents.json")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    main(ap.parse_args())
