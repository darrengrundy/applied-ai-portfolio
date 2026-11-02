"""Build the Before Start check screen from engine output (no LLM needed).

python src/build_tower.py --data data --findings build/findings.json --out demo/tower.html
"""
import argparse, json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RANK = {"GREEN": 0, "AMBER": 1, "RED": 2}
AREAS = ["Fatigue", "Mass & dimension", "Load restraint", "Speed", "Maintenance", "Integrity"]
CHECKPOINT = {"Fatigue": "ewd", "Maintenance": "vehicle", "Mass & dimension": "weighbridge",
              "Load restraint": "loadcheck", "Speed": "road", "Integrity": "road"}
DO_NOW = {
    "MASS-OVER-GML": "Take weight off and re-weigh before release",
    "MASS-NO-EVIDENCE": "Weigh the load and complete the JSEA before release",
    "MASS-NO-JSEA": "Complete the pre-dispatch JSEA",
    "MASS-DECLARED-LOW": "Query the consignor's declared weight",
    "MASS-PENDING": "Get the weighbridge ticket before departure",
    "MASS-STEER": "Re-position the load and re-weigh",
    "LR-NO-PLAN": "Prepare a restraint plan before loading",
    "LR-COMPETENCY-EXPIRED": "A competent person must restrain and sign off the load",
    "LR-COMPETENCY-SOON": "Book the restraint refresher",
    "LR-EQUIPMENT-FAILED": "Tag out the failed strap and fit a passed one",
    "LR-UNDER-TABLE": "Add lashings to meet the tie-down table",
    "SPD-OVER-10": "Speak with the driver and record follow-up before release",
    "SPD-WATCH": "Review the delivery window with the scheduler",
    "SPD-LIMIT-UNVERIFIED": "Verify the posted limit and correct the map layer",
    "MNT-SERVICE-OVERDUE": "Swap the vehicle, or service it first",
    "MNT-SERVICE-SOON": "Book a workshop slot",
    "MNT-OPEN-DEFECT": "Swap the trailer, or repair and clear the defect",
    "MNT-BOOKING-CLASH": "Move the booking or swap the vehicle",
    "INT-UNRECORDED-DRIVER": "Confirm who drove on Saturday before release",
    "INT-FEED-STALE": "Check the telematics unit",
    "FAT-HEADROOM": "Agree a fallback if the dock runs late",
    "FAT-RECORDS": "Complete the work diary before release",
}
ROAD_POINT = {"Corio": ("GEE", 0.78), "Sunshine": ("MET", 0.5), "Bacchus Marsh": ("BAL", 0.45),
              "Kyneton": ("BEN", 0.55), "Seymour": ("ALB", 0.38), "Gundagai": ("SYD", 0.75)}
CUST = {"C1": "Brackenridge Steel", "C2": "Tumbarumba Timber", "C3": "Greyfield Building", "C4": "Corella Home Retail",
        "C5": "Ashgrove Beverages", "C6": "Kestrel Machinery"}


def dt(s):
    return datetime.fromisoformat(s)


def do_now(f):
    return (f["facts"] or {}).get("fix") or DO_NOW.get(f["rule_id"], "")


def patterns(d):
    """Deterministic 28-day patterns the controller would not see in one day's list."""
    out = []
    wb = {w["movement_id"]: w for w in d["weighbridge"]}
    cust = {"C1": "Brackenridge Steel Supply", "C4": "Corella Home Retail", "C3": "Greyfield Building Products"}
    by = defaultdict(list)
    for m in d["movements"]:
        w = wb.get(m["id"])
        if not m["planned"] and w and w.get("gross_kg"):
            by[m["customer_id"]].append((w["gross_kg"] - m["tare_kg"]) / m["declared_kg"] - 1)
    for c, xs in by.items():
        light = [x for x in xs if x > 0.05]
        if len(light) >= 5 and len(light) / len(xs) > 0.5:
            out.append(dict(rag="RED", area="Mass & dimension", title=f"{cust.get(c, c)} declares light on {len(light)} of {len(xs)} loads",
                            detail=f"Weighbridge payload averages {100 * sum(xs) / len(xs):.1f}% above the declared weight over 4 weeks. "
                                   "A consignor duty issue: today's coil load is over the combination limit.",
                            owner="Consignor + loader", applies_to=dict(customer=CUST.get(c, c))))
    done = {a["ref"] for a in d["actions"]}
    loc = defaultdict(list)
    for e in d["speed_events"]:
        if e["id"] not in done:
            loc[e["location"]].append(e)
    mvs = defaultdict(list)
    for m in d["movements"]:
        mvs[m["driver_id"]].append(m)
    for l, es in loc.items():
        drivers = {e["driver_id"] for e in es}
        if len(drivers) >= 3 and len(es) >= 8:
            overs = sorted(e["peak_kph"] - e["limit_kph"] for e in es)
            # which trip and delivery slot was each event on?
            ctx = []
            for e in es:
                t = datetime.fromisoformat(e["at"])
                m = next((m for m in mvs[e["driver_id"]] if datetime.fromisoformat(m["depart"]) <= t <= datetime.fromisoformat(m["arrive_window"])), None)
                if m:
                    ctx.append((m["customer_id"], (datetime.fromisoformat(m["arrive_window"]) - t).total_seconds() / 60))
            cust_n = defaultdict(int)
            for c, _ in ctx:
                cust_n[c] += 1
            top = max(cust_n, key=cust_n.get) if cust_n else None
            lead = sorted(round(x) for c, x in ctx if c == top)
            extra = (f" {cust_n[top]} of {len(es)} were on trips to {CUST[top]}, {lead[0]}-{lead[-1]} minutes before the "
                     f"booked delivery slot." if top else "")
            out.append(dict(rag="AMBER", area="Speed", title=f"{len(drivers)} drivers, {len(es)} events at {l}",
                            detail=f"All {overs[0]}-{overs[-1]} km/h over entering the lower zone, none followed up.{extra} "
                                   "Same place, different drivers: check the delivery slot before talking to drivers one by one.",
                            owner="Scheduler + consignor",
                            applies_to=dict(location=l, drivers=sorted(drivers), customer=CUST.get(top))))
    return out


def scene_metric(f, d):
    """Big number + supporting lines for the replay overlay. Numbers come only from engine facts."""
    x, r = f["facts"] or {}, f["rule_id"]
    if r == "MASS-OVER-GML":
        return f"{x['gross_t']:.1f} t", [f"Limit {x['limit_t']} t · over by {x['gross_t'] - x['limit_t']:.1f} t",
                                          f"Declared payload {x['declared_kg']:,} kg · weighbridge {x['measured_payload_kg']:,} kg"]
    if r == "MASS-NO-EVIDENCE":
        return "No ticket", ["No weighbridge ticket", "No pre-dispatch JSEA"]
    if r.startswith("FAT-") and "detail" in x:
        big = x["detail"].split(" in ")[0] if r.endswith("WORK") else "Rest short"
        return big, [x["detail"], f"Planned start {dt(x['planned_start']):%a %H:%M}"]
    if r == "LR-UNDER-TABLE":
        return f"{x['planned']} of {x['required']}", [f"Lashings per {x['row_kg']:,} kg row",
                                                      f"{x['lashing']} at friction {x['friction']}: {x['per_lashing_kg']:,} kg each"]
    if r == "LR-EQUIPMENT-FAILED":
        return x["equipment"], [f"Failed {x['inspected']}: {x['result'].removeprefix('fail: ')}"]
    if r == "LR-COMPETENCY-EXPIRED":
        return "Expired", [f"Restraint competency lapsed {x['expiry']}"]
    if r == "SPD-OVER-10":
        return f"+{x['max_over']} km/h", [f"{x['events']} events, {x['seconds']} s over, none followed up", ", ".join(x["locations"])]
    if r == "MNT-SERVICE-OVERDUE":
        return f"{x['km_after_trip'] - x['due_km']:,} km", ["past the service point by end of trip",
                                                            f"Service due at {x['due_km']:,} km"]
    if r == "MNT-OPEN-DEFECT":
        return x["severity"].title(), [f"Reported {x['reported'][:10]}, still open"]
    if r == "INT-UNRECORDED-DRIVER":
        return f"{x['km']} km", ["driven with no matching work diary entry", f"Login: {x['assigned_driver']}"]
    return "", []


def road_point(f, lane):
    locs = " ".join((f["facts"] or {}).get("locations", [])) + (f["facts"] or {}).get("location", "")
    for k, v in ROAD_POINT.items():
        if k in locs:
            return v
    return lane, 0.6


def main(a):
    d = {p.stem: json.loads(p.read_text()) for p in Path(a.data).glob("*.json")}
    out = json.loads(Path(a.findings).read_text())
    drv_meta = {x["id"]: x for x in d["drivers"]}
    wb = {w["movement_id"]: w for w in d["weighbridge"]}
    fs = {f["id"]: f for f in out["findings"]}
    moves, by_driver = {}, defaultdict(list)
    for m in sorted(out["movements"], key=lambda m: m["depart"]):
        mm = dict(id=m["movement_id"], rag=m["rag"], depart=m["depart"], dest=m["destination"], lane=m["lane"],
                  driver_id=m["driver_id"], co_driver_id=m.get("co_driver_id"), vehicle=m["vehicle_id"], trailer=m["trailer_id"],
                  customer=CUST[m["customer_id"]], load=m["load_type"], findings=m["findings"],
                  weigh=wb.get(m["movement_id"], {}).get("status"))
        moves[mm["id"]] = mm
        for did in (m["driver_id"], m.get("co_driver_id")):
            if did:
                by_driver[did].append(mm["id"])

    drivers, scenes, timelines = [], [], {}
    for did, mids in by_driver.items():
        meta = drv_meta[did]
        ms = [moves[i] for i in mids]
        rag = max((m["rag"] for m in ms), key=RANK.get)
        fids = sorted({f for m in ms for f in m["findings"]},
                      key=lambda i: (-RANK[fs[i]["rag"]], fs[i]["area"] != "Fatigue" or not fs[i]["rule_id"].endswith("WORK"), i))
        areas = {}
        for ar in AREAS:
            hits = [fs[i]["rag"] for i in fids if fs[i]["area"] == ar]
            if hits:
                areas[ar] = max(hits, key=RANK.get)
            elif ar == "Mass & dimension" and all(m["weigh"] == "not_due" for m in ms):
                areas[ar] = "DUE"
            else:
                areas[ar] = "GREEN"
        focus = [m for m in ms if m["rag"] == rag]
        nxt = focus[0]
        top = fs[fids[0]] if fids else None
        co = nxt["co_driver_id"] if nxt["driver_id"] == did else nxt["driver_id"]
        drivers.append(dict(id=did, name=meta["name"], scheme=meta["scheme"], rag=rag, areas=areas, moves=mids,
                            next=nxt["id"], partner=drv_meta[co]["name"] if co and co != did else None,
                            more=len(focus) - 1, top=fids[0] if fids else None, do=do_now(top) if top else "",
                            findings=fids))
        # fatigue timeline for drivers with fatigue findings
        ff = [fs[i] for i in fids if fs[i]["area"] == "Fatigue" and "window_start" in (fs[i]["facts"] or {})]
        if ff:
            f0 = ff[0]["facts"]
            ws, we, ps = dt(f0["window_start"]), dt(f0["window_end"]), dt(f0["planned_start"])
            lo, hi = min(ws, ps - timedelta(hours=24)) - timedelta(hours=2), max(we, ps + timedelta(hours=12))
            ev = [dict(s=e["start"], e=e["end"], w=e["activity"] == "work", p=bool(e.get("planned")))
                  for e in d["ewd"] if e["driver_id"] == did and dt(e["end"]) > lo and dt(e["start"]) < hi]
            timelines[did] = dict(lo=lo.isoformat(timespec="minutes"), hi=hi.isoformat(timespec="minutes"),
                                  ws=f0["window_start"], we=f0["window_end"], ps=f0["planned_start"],
                                  label=f0["detail"], rule=ff[0]["rule_id"], events=ev)
        # one replay scene per stopped driver, on their worst finding
        if rag == "RED" and top and not any(s["move"] == nxt["id"] and s["finding"] == top["id"] for s in scenes):
            ar = top["area"]
            cp = CHECKPOINT[ar]
            lane, frac = (road_point(top, nxt["lane"]) if cp == "road" else (nxt["lane"], 0))
            big, lines = scene_metric(top, d)
            scenes.append(dict(driver=did, name=meta["name"], partner=drivers[-1]["partner"], move=nxt["id"], finding=top["id"],
                               area=ar, checkpoint=cp, lane=lane, frac=frac, title=top["title"], big=big, lines=lines,
                               do=do_now(top), areas=areas, depart=nxt["depart"]))
    drivers.sort(key=lambda x: (-RANK[x["rag"]], moves[x["next"]]["depart"]))
    scenes.sort(key=lambda s: s["depart"])
    # agent layer (optional): per-driver assessments, systemic issues, briefing, evaluation
    agents, evalm = {}, None
    ap_, ep_ = Path(a.findings).parent / "agents.json", Path(a.findings).parent / "eval.json"
    if ap_.exists():
        ag = json.loads(ap_.read_text())
        for r in ag["drivers"]:
            agents[r["driver"]] = dict(items=r["assessment"]["assessments"], summary=r["assessment"]["driver_summary"],
                                       rounds=len(r["review"]), passed=r["passed"])
        agents_meta = dict(model=ag["model"], systemic=ag["systemic"], briefing=ag["briefing"])
    else:
        agents_meta = None
    if ep_.exists():
        evalm = json.loads(ep_.read_text())["metrics"]
        sp_ = Path(a.findings).parent / "series.json"
        if sp_.exists():
            evalm["series"] = json.loads(sp_.read_text())["summary"]
    for dr in drivers:
        A = agents.get(dr["id"])
        if A and dr["top"]:
            area = fs[dr["top"]]["area"]
            x = next((x for x in A["items"] if x["area"] == area), None)
            if x:
                dr["do"], dr["decision"], dr["parties"] = x["action"], x["decision"], x["accountable_parties"]
    for sc in scenes:
        A = agents.get(sc["driver"])
        x = A and next((x for x in A["items"] if x["area"] == sc["area"]), None)
        if x:
            sc["do"], sc["decision"], sc["parties"] = x["action"], x["decision"], x["accountable_parties"]
    entity = [f["id"] for f in out["findings"] if not f["movement_id"]]
    data = dict(meta=d["meta"], drivers=drivers, moves=moves, findings=fs, entity=entity, patterns=patterns(d),
                scenes=scenes, timelines=timelines, areas=AREAS, agents=agents, agents_meta=agents_meta, eval=evalm)
    html = (ROOT / "demo/tower_template.html").read_text().replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    if a.hosted:
        html = hosted(html, a.base_url)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(html)
    print(a.out, len(html) // 1024, "KB;", len(drivers), "drivers;", len(scenes), "scenes")


DESC = ("Before Start Safety/CoR Check: a control-tower view of 159 planned heavy vehicle trips. Rules set the traffic light; "
        "Claude agents explain each stop and name who in the chain owns the fix. Synthetic data.")


def hosted(html, base_url=""):
    """Wrap the page as a standalone document for static hosting, with link-preview tags."""
    i = html.index("</style>") + len("</style>")
    head, body = html[:i], html[i:]
    img = f"{base_url.rstrip('/')}/preview.png" if base_url else "preview.png"
    meta = (f'<meta name="description" content="{DESC}">'
            f'<meta property="og:type" content="website"><meta property="og:title" content="Before Start Safety/CoR Check">'
            f'<meta property="og:description" content="{DESC}"><meta property="og:image" content="{img}">'
            f'<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
            + (f'<meta property="og:url" content="{base_url}">' if base_url else "")
            + '<meta name="twitter:card" content="summary_large_image">'
            '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 16%22%3E'
            '%3Ccircle cx=%228%22 cy=%228%22 r=%227%22 fill=%22%23ff4d4d%22/%3E%3C/svg%3E">'
            '<style>html,body{margin:0}[hidden]{display:none!important}:root{padding-top:env(safe-area-inset-top,0px);'
            'padding-bottom:env(safe-area-inset-bottom,0px)}</style>')
    return ('<!doctype html><html lang="en-AU"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            + meta + head + "</head><body>" + body + "</body></html>")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--findings", default="build/findings.json")
    ap.add_argument("--out", default="demo/tower.html")
    ap.add_argument("--hosted", action="store_true", help="standalone document with link-preview tags")
    ap.add_argument("--base-url", default="", help="public URL of the hosted page, for the preview image")
    main(ap.parse_args())
