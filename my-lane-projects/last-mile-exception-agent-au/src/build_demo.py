"""Build the self-contained demo page from the synthetic day and a recorded agent run.

  python src/build_demo.py --run runs/full --out demo/index.html

Reads data/ (the day) and the run folder (results.jsonl, wismo.jsonl, metrics.json from evaluate.py).
Everything the page needs is embedded, so it makes no server or API calls when viewed."""
import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import PROJECT

CODES = ["DELIVERED", "ATTEMPTED", "ACCESS_ISSUE", "ADDRESS_ISSUE", "DAMAGED", "REFUSED", "WEATHER_DELAY",
         "HEAT_HOLD", "VEHICLE_DELAY", "ROAD_CLOSURE", "DELIVERED_NOT_RECEIVED"]
LABEL = {"ATTEMPTED": "Nobody home", "ACCESS_ISSUE": "Couldn't get in", "ADDRESS_ISSUE": "Address problem",
         "DAMAGED": "Damaged", "REFUSED": "Refused", "WEATHER_DELAY": "Storm delay", "HEAT_HOLD": "Too hot to leave",
         "VEHICLE_DELAY": "Van broke down", "ROAD_CLOSURE": "Fire road closure",
         "DELIVERED_NOT_RECEIVED": "Delivered, not received"}
RES_LABEL = {"REDELIVER_TODAY": "Back out on tonight's run", "RESCHEDULE": "Redelivered Monday",
             "TO_PARCEL_LOCKER": "Carded to a Parcel Locker", "TO_POST_OFFICE": "Carded to the Post Office",
             "REPLACE": "Replacement sent", "RETURN_TO_SENDER": "Returned and refunded"}
SHORT_REASON = {"3rd failed delivery attempt": "Third failed attempt",
                "Possible card left without a genuine attempt": "Carded without a real attempt",
                "VIP customer with 3+ exceptions in 90 days": "VIP with repeat problems",
                "Damaged perishable": "Damaged fresh food", "Damaged fragile item over $500": "Damaged, over $500",
                "Perishable delayed more than 4 hours": "Fresh food delayed 4+ hours",
                "Address pattern suggests fraud": "Possible fraud",
                "Trade delivery refused on last business day of the month": "Month-end trade refusal",
                "Repeat delivered-not-received claim": "Repeat 'not received' claim",
                "Prompt injection in driver note": "Note tried to instruct the AI",
                "Standard customer with 4+ exceptions in 90 days": "Customer with repeat problems",
                "Premium perishable affected by weather or fire": "Premium fresh food, weather or fire",
                "Agent and critic did not agree after 2 revisions": "Agent and critic disagreed"}
NODE_LABEL = {"preprocessor": "Preprocessor", "rule_engine": "Rule engine", "resolution_agent": "Resolution agent",
              "resolution_agent_retry": "Resolution agent (revised)", "critic_resolution": "Resolution critic",
              "orchestrator": "Orchestrator", "communication_agent": "Communication agent",
              "communication_agent_retry": "Communication agent (revised)",
              "critic_communication": "Message critic", "finalize": "Done"}


def hm(ts):  # ISO -> minutes after midnight
    return int(ts[11:13]) * 60 + int(ts[14:16])


def step_summary(t):
    n, o, d = t["node"], t.get("output") or {}, t.get("detail") or {}
    if n == "preprocessor":
        s = f"{d.get('rows_raw')} scans in, {d.get('rows_after_dedup')} after removing duplicates."
        if d.get("noise"):
            s += " Routine delivery: no action."
        if d.get("delay_hours") is not None:
            s += " Delay read from note: " + ("rest of day" if d["delay_hours"] >= 24 else f"{d['delay_hours']:g} h") + "."
        if d.get("injection_flagged"):
            s += " Driver note tried to instruct the AI: withheld."
        return s
    if n == "rule_engine":
        a = d.get("automatic_triggers") or []; ds = d.get("discretionary_signals") or []
        return ("Must escalate: " + "; ".join(a + ds)) if (a or ds) else "No escalation triggers."
    if n.startswith("resolution_agent"):
        return f"{RES_LABEL.get(o.get('resolution'), o.get('resolution'))}. {o.get('reasoning', '')}".strip()
    if n.startswith("critic"):
        return "Approved." if o.get("decision") == "ACCEPT" else "Sent back: " + (o.get("feedback") or "; ".join(o.get("issues", [])))
    if n == "orchestrator":
        if not d.get("escalated"):
            return "Handled without a person."
        s = "Handed to a team leader"
        if d.get("forced_by_rule_engine"):
            s += " (rule engine overrode the agent)"
        return s + "."
    if n.startswith("communication_agent"):
        return f"{o.get('channel')} drafted, {str(o.get('tone', '')).lower()} tone."
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(PROJECT / "runs" / "full"))
    ap.add_argument("--data", default=str(PROJECT / "data"))
    ap.add_argument("--out", default=str(PROJECT / "demo" / "index.html"))
    ap.add_argument("--note", default="", help="Optional banner, e.g. for a preview build")
    a = ap.parse_args()
    D, R = Path(a.data), Path(a.run)

    story = json.load(open(D / "storylines.json"))
    P = pd.read_csv(D / "parcels.csv")
    C = pd.read_csv(D / "customers.csv", keep_default_na=False).set_index("customer_id")
    S = pd.read_csv(D / "scan_log.csv", keep_default_na=False, dtype=str)
    S = S[S.is_duplicate_scan != "True"]
    scans = {k: g for k, g in S.groupby("parcel_id", sort=False)}
    pts = pd.read_csv(D / "collection_points.csv")
    dep = pd.read_csv(D / "depots.csv")
    vans = json.load(open(D / "vans.json"))
    gt = pd.read_csv(D / "ground_truth.csv", keep_default_na=False).set_index("parcel_id") \
        if (D / "ground_truth.csv").exists() else None
    res = {}
    for line in (R / "results.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        res[r["parcel_id"]] = r
    wismo = [json.loads(l) for l in (R / "wismo.jsonl").open(encoding="utf-8")] if (R / "wismo.jsonl").exists() else []
    metrics = json.load(open(R / "metrics.json")) if (R / "metrics.json").exists() else {}

    # ---- parcels (one dot each) ---------------------------------------------------------
    P["t"] = (P.stop_time * 60).round().astype(int)
    PI = P.set_index("parcel_id", drop=False)
    case_ix = {}
    cases = []
    model = ""
    for pid, r in res.items():
        if r["outcome"] == "NOISE" or not r.get("resolution"):
            continue
        p = PI.loc[pid]; cu = C.loc[r["event"]["customer_id"]]
        msg = r.get("message") or {}
        steps = [[t["node"], round(t.get("latency_s") or 0, 1), trim(step_summary(t))]
                 for t in r["trace"] if t["node"] != "finalize"]
        model = model or next((t.get("model") for t in r["trace"] if t.get("model")), "")
        tl = [[hm(x.timestamp), x.status_code, x.status_description] for x in scans[pid].itertuples()] if pid in scans else []
        for cm in r["event"].get("customer_messages", []):
            tl.append([int(cm["time"][:2]) * 60 + int(cm["time"][3:5]), "CUSTOMER", cm["message"]])
        tl.sort(key=lambda x: x[0])
        pt = r.get("collection_point") or {}
        g = gt.loc[pid] if gt is not None and pid in gt.index else None
        case = {
            "id": pid, "city": p.city, "x": round(float(p.lon), 5),
            "y": round(float(p.lat), 5), "t": hm(r["event"]["event_time"]), "code": r["status_code"],
            "label": LABEL.get(r["status_code"], r["status_code"]),
            "res": r["resolution"]["resolution"], "resl": RES_LABEL.get(r["resolution"]["resolution"], ""),
            "pt": pt.get("name", ""), "pth": pt.get("operating_hours", ""), "ptd": pt.get("hold_business_days", ""),
            "esc": bool(r["escalated"]), "why": short_reasons(r.get("escalation_reasons", []), r.get("rule_engine") or {}), "forced": bool(r.get("forced_by_rules")),
            "who": cu.business_name if cu.customer_type == "TRADE" and cu.business_name else cu["name"].split()[0],
            "tier": cu.tier, "type": cu.customer_type, "suburb": cu.suburb,
            "ch": msg.get("channel", ""), "tone": msg.get("tone", ""), "subj": msg.get("subject", ""),
            "msg": msg.get("message", ""), "sec": round(sum(t.get("latency_s") or 0 for t in r["trace"]), 1),
            "cost": round(r.get("cost_usd", 0), 5), "steps": steps, "tl": tl,
            "sub": (g.sub_type if g is not None else ""), "ok": None,
            "complaint": bool(r["event"].get("customer_messages")), "inj": bool(r["event"].get("guardrail_injection")),
            "val": round(float(p.value), 0), "perish": p.package_type == "PERISHABLE",
        }
        if g is not None:
            case["ok"] = bool(case["res"] == g.expected_resolution and case["esc"] == (g.should_escalate == "YES"))
        case_ix[pid] = len(cases); cases.append(case)

    cities = {}
    for city in ["MEL", "SYD"]:
        q = P[P.city == city]
        cities[city] = {
            "x": [round(v, 4) for v in q.lon], "y": [round(v, 4) for v in q.lat], "t": q.t.tolist(),
            "c": [case_ix.get(pid, -1) for pid in q.parcel_id],
            "vans": [{"p": [[round(pp[0], 4), round(pp[1], 4)] for pp in v["path"]], "t": [round(pp[2] * 60, 1) for pp in v["path"]]}
                     for v in vans if v["city"] == city],
            "depots": dep[dep.city == city][["name", "lon", "lat"]].round(4).to_dict("records"),
            "points": pts[pts.city == city][["type", "name", "lon", "lat"]].round(4).to_dict("records"),
        }

    # fire zone: hull of the closed localities
    fire_pts = P[(P.city == "MEL") & (P.status_code == "ROAD_CLOSURE")][["lon", "lat"]].values.tolist()
    story["fire"]["hull"] = hull(fire_pts) if len(fire_pts) > 2 else []

    W = []
    for w in wismo:
        W.append({"t": hm(w["time"]), "q": w["question"], "a": w["reply"], "now": w.get("status_now", ""),
                  "id": w["parcel_id"], "case": case_ix.get(w["parcel_id"], -1)})

    tour = pick_tour(cases, story)
    summary = {
        "parcels": int(len(P)), "cases": len(cases), "escalated": sum(c["esc"] for c in cases),
        "forced": sum(c["forced"] for c in cases), "complaints": sum(c["complaint"] for c in cases),
        "cost": round(sum(r.get("cost_usd", 0) for r in res.values()) + sum(w.get("cost_usd", 0) for w in wismo), 2),
        "sec_avg": round(sum(c["sec"] for c in cases) / max(1, len(cases)), 1),
        "by_code": pd.Series([c["code"] for c in cases]).value_counts().to_dict(),
        "by_res": pd.Series([c["res"] for c in cases]).value_counts().to_dict(),
        "esc_reasons": pd.Series([w for c in cases for w in c["why"]]).value_counts().head(8).to_dict(),
        "metrics": metrics, "model": model,
    }
    # keep the page under the 16 MB artifact limit: if needed, drop step text for routine cases
    keep = {t["case"] for t in tour}
    for limit in (None, 600, 300, 0):
        if limit is not None:
            for i, c in enumerate(cases):
                if i not in keep and not c["esc"] and not c["complaint"]:
                    for st in c["steps"]:
                        st[2] = st[2][:limit]
        size = len(json.dumps(cases, separators=(",", ":"), default=str)) + 3_000_000
        if size < 14_500_000:
            break
    payload = {"note": a.note, "node_labels": NODE_LABEL, "story": story, "cities": cities, "cases": cases, "wismo": W, "tour": tour, "summary": summary,
               "labels": LABEL, "res_labels": RES_LABEL}
    html = (PROJECT / "src" / "demo_template.html").read_text(encoding="utf-8")
    html = html.replace("__DATA__", json.dumps(payload, separators=(",", ":"), default=str))
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"{out} written: {out.stat().st_size / 1e6:.1f} MB | {len(cases):,} cases | {len(W)} enquiries | "
          f"tour stops {len(tour)}")


def short_reasons(reasons, rule_engine):
    """Rule-engine triggers in plain words first, then anything the agent added (deduplicated)."""
    known = [SHORT_REASON[x] for x in (rule_engine.get("automatic_triggers", []) +
                                       rule_engine.get("discretionary_signals", [])) if x in SHORT_REASON]
    extra = [SHORT_REASON.get(x, x) for x in reasons if x in SHORT_REASON and SHORT_REASON[x] not in known]
    other = [x for x in reasons if x not in SHORT_REASON]
    out = list(dict.fromkeys(known + extra))
    if not out and other:
        out = [trim(other[0], 90)]
    return out[:3]


def trim(text, n=320):
    """Keep the first sentences of agent reasoning, up to about n characters."""
    if len(text) <= n:
        return text
    cut = text[:n]
    end = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[:end + 1] if end > n * 0.5 else cut.rstrip() + "…")


def hull(points):
    """Convex hull (monotone chain), padded slightly so it reads as an area."""
    pts = sorted(set(map(tuple, points)))
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    h = lo[:-1] + up[:-1]
    cx = sum(p[0] for p in h) / len(h); cy = sum(p[1] for p in h) / len(h)
    return [[round(cx + (x - cx) * 1.35, 4), round(cy + (y - cy) * 1.35, 4)] for x, y in h]


def pick_tour(cases, story):
    """The parcels the autoplay tour stops on: one per storyline, chosen from the data."""
    def first(f, after=0):
        for c in sorted(cases, key=lambda c: c["t"]):
            if c["t"] >= after and f(c):
                return c
        return None
    picks = [
        ("Van breaks down in Botany", first(lambda c: c["code"] == "VEHICLE_DELAY" and c["city"] == "SYD" and c["perish"])
         or first(lambda c: c["code"] == "VEHICLE_DELAY" and c["city"] == "SYD")),
        ("\"I was home!\"", first(lambda c: c["sub"] == "FALSE_CARD" and c["complaint"])
         or first(lambda c: c["complaint"] and c["code"] in ("ATTEMPTED", "ACCESS_ISSUE"))),
        ("A driver note tries to trick the AI", first(lambda c: c["inj"])),
        ("Fire closes the Dandenong Ranges", first(lambda c: c["code"] == "ROAD_CLOSURE" and c["perish"])
         or first(lambda c: c["code"] == "ROAD_CLOSURE")),
        ("Hail and flash flooding in Sydney", first(lambda c: c["code"] == "WEATHER_DELAY" and c["perish"])
         or first(lambda c: c["code"] == "WEATHER_DELAY")),
        ("39° in Melbourne: fresh food can't be left", first(lambda c: c["code"] == "HEAT_HOLD")),
        ("Month-end: the DC won't take it", first(lambda c: c["code"] == "REFUSED" and c["type"] == "TRADE" and c["esc"])
         or first(lambda c: c["code"] == "REFUSED" and c["type"] == "TRADE")),
        ("Carded to the local Parcel Locker", first(lambda c: c["res"] == "TO_PARCEL_LOCKER", 16 * 60)),
        ("\"It says delivered. It's not here.\"", first(lambda c: c["code"] == "DELIVERED_NOT_RECEIVED")),
    ]
    return [{"title": t, "case": cases.index(c)} for t, c in picks if c is not None]


if __name__ == "__main__":
    main()
