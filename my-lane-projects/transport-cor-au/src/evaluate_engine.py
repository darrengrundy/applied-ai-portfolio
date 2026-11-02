"""Score the deterministic engine against generator labels.

- Each labelled storyline: did the expected rules fire on its movements, at the expected colour?
- Each decoy: is it green?
- Any finding on a movement no label covers is an unexpected finding (baseline leak).
"""
import json, sys
from pathlib import Path

RANK = {"GREEN": 0, "AMBER": 1, "RED": 2}


def main(data="data", findings="build/findings.json"):
    labels = json.loads(Path(data, "labels.json").read_text())
    out = json.loads(Path(findings).read_text())
    mv = {m["movement_id"]: m for m in out["movements"]}
    fs = out["findings"]
    covered, ok, rows = set(), 0, []
    for lb in labels:
        ids = lb["movement_ids"]
        covered |= set(ids)
        if lb["kind"] == "decoy":
            got = {mv[i]["rag"] for i in ids if i in mv}
            passed = got <= {"GREEN"}
            rows.append((lb["story"], "decoy", "GREEN", ",".join(sorted(got)), passed, ""))
        else:
            hit = [f for f in fs if f["rule_id"] in lb["expected_rules"] and
                   (f["movement_id"] in ids or (f["movement_id"] is None and f["entity"] == lb["entity"]))]
            worst = max((f["rag"] for f in hit), key=RANK.get, default="none")
            passed = bool(hit) and worst == lb["expected_rag"]
            rows.append((lb["story"], lb["area"], lb["expected_rag"], worst, passed,
                         ",".join(sorted({f["rule_id"] for f in hit}))))
        ok += passed
    unexpected = [f for f in fs if f["movement_id"] and f["movement_id"] not in covered]
    for r in rows:
        print(f"{'PASS' if r[4] else 'FAIL'}  {r[0]:4} {r[1]:17} expect {r[2]:5} got {r[3]:6} {r[5]}")
    print(f"\n{ok}/{len(labels)} labels met; unexpected findings on unlabelled movements: {len(unexpected)}")
    for f in unexpected[:20]:
        print("  unexpected:", f["rule_id"], f["rag"], f["movement_id"], f["title"])
    return ok == len(labels) and not unexpected


if __name__ == "__main__":
    sys.exit(0 if main(*sys.argv[1:]) else 1)
