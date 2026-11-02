"""Score agent assessments against generator labels.

For each labelled storyline (decoys are green, so agents never see them):
  decision exact, decision family (stop / go-with-follow-up), root cause, accountable party (overlap),
  stop recall (RED labels must get a stop decision), grounding (numbers not in input), critic outcome.
python src/evaluate_agents.py --agents build/agents.json --out build/eval.json
"""
import argparse, json
from collections import Counter
from pathlib import Path

STOP = {"HOLD", "RESCHEDULE", "INVESTIGATE"}


def family(d):
    return "stop" if d in STOP else "go"


def main(a):
    labels = [l for l in json.loads(Path(a.data, "labels.json").read_text()) if l["kind"] == "storyline"]
    out = json.loads(Path(a.findings).read_text())
    ag = json.loads(Path(a.agents).read_text())
    fs = {f["id"]: f for f in out["findings"]}
    mv_find = {m["movement_id"]: m["findings"] for m in out["movements"]}
    rows = []
    for lb in labels:
        fids = {i for mid in lb["movement_ids"] for i in mv_find.get(mid, []) if fs[i]["rule_id"] in lb["expected_rules"]}
        fids |= {f["id"] for f in out["findings"] if f["movement_id"] is None and f["entity"] == lb["entity"]
                 and f["rule_id"] in lb["expected_rules"]}
        hit = None
        for d in ag["drivers"]:
            for x in d["assessment"]["assessments"]:
                if fids & set(x["finding_ids"]):
                    hit = (d, x)
                    break
            if hit:
                break
        if not hit:
            rows.append(dict(story=lb["story"], area=lb["area"], found=False))
            continue
        d, x = hit
        rows.append(dict(story=lb["story"], area=lb["area"], entity=lb["entity"], found=True, driver=d["name"],
                         expected=dict(decision=lb["decision"], root_cause=lb["root_cause"], parties=lb["parties"], rag=lb["expected_rag"]),
                         got=dict(decision=x["decision"], root_cause=x["root_cause"], parties=x["accountable_parties"]),
                         decision_exact=x["decision"] == lb["decision"],
                         decision_family=family(x["decision"]) == family(lb["decision"]),
                         root_cause=x["root_cause"] == lb["root_cause"],
                         party=bool(set(x["accountable_parties"]) & set(lb["parties"])),
                         stop_ok=(family(x["decision"]) == "stop") if lb["expected_rag"] == "RED" else None,
                         action=x["action"], explanation=x["explanation"]))
    found = [r for r in rows if r["found"]]
    reds = [r for r in found if r["stop_ok"] is not None]
    pct = lambda k, rs: round(100 * sum(r[k] for r in rs) / max(1, len(rs)), 1)
    ungrounded = sum(len(v) for d in ag["drivers"] for v in d["ungrounded_final"].values())
    claims = sum(len(d["assessment"]["assessments"]) for d in ag["drivers"])
    metrics = dict(
        labels=len(labels), assessed=len(found),
        decision_exact=pct("decision_exact", found), decision_family=pct("decision_family", found),
        root_cause=pct("root_cause", found), accountable_party=pct("party", found),
        stop_recall=pct("stop_ok", reds), red_labels=len(reds),
        assessments=claims, ungrounded_numbers=ungrounded,
        critic_first_pass=sum(len(d["review"]) == 1 and d["passed"] for d in ag["drivers"]),
        critic_unresolved=sum(not d["passed"] for d in ag["drivers"]),
        floor_overrides=sum(len(d["floor_overrides"]) for d in ag["drivers"]),
        rule_mismatches=sum(len(v) for d in ag["drivers"] for v in d.get("rule_mismatch_final", {}).values()),
        rule_fixed_by_revision=sum(1 for d in ag["drivers"] for r in d["review"] for e in r["errors"] if e.get("source") == "rule check"),
        briefing_missing=len(ag.get("briefing_missing", [])),
        drivers=len(ag["drivers"]), model=ag["model"], usage=ag["usage"], seconds=ag["seconds"])
    Path(a.out).write_text(json.dumps(dict(metrics=metrics, rows=rows), indent=1, ensure_ascii=False))
    for r in rows:
        if not r["found"]:
            print(f"MISS  {r['story']} {r['area']}")
            continue
        flag = "".join("✓" if r[k] else "✗" for k in ("decision_exact", "decision_family", "root_cause", "party"))
        print(f"{flag}  {r['story']} {r['area']:16} {r['expected']['decision']:>23} → {r['got']['decision']:23} "
              f"{r['expected']['root_cause']:>21} → {r['got']['root_cause']:21} {r['expected']['parties']} → {r['got']['parties']}")
    print(json.dumps(metrics, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--findings", default="build/findings.json")
    ap.add_argument("--agents", default="build/agents.json")
    ap.add_argument("--out", default="build/eval.json")
    main(ap.parse_args())
