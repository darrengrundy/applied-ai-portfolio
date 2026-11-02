"""Run the agents N times on the same data and summarise the spread of each metric.

python src/run_series.py --runs 3
"""
import argparse, json, statistics, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["stop_recall", "accountable_party", "root_cause", "decision_exact", "decision_family",
        "ungrounded_numbers", "rule_mismatches", "floor_overrides", "critic_unresolved", "briefing_missing", "seconds"]


def main(a):
    runs = ROOT / "build/runs"
    runs.mkdir(parents=True, exist_ok=True)
    res = []
    for k in range(1, a.runs + 1):
        ag, ev = runs / f"agents_{k}.json", runs / f"eval_{k}.json"
        subprocess.run([sys.executable, "src/agents.py", "--out", str(ag)], cwd=ROOT, check=True)
        subprocess.run([sys.executable, "src/evaluate_agents.py", "--agents", str(ag), "--out", str(ev)], cwd=ROOT,
                       check=True, stdout=subprocess.DEVNULL)
        m = json.loads(ev.read_text())["metrics"]
        res.append(m)
        print(f"run {k}: " + ", ".join(f"{x}={m[x]}" for x in KEYS), flush=True)
    summ = {x: dict(mean=round(statistics.mean(r[x] for r in res), 1), min=min(r[x] for r in res), max=max(r[x] for r in res))
            for x in KEYS}
    summ["runs"] = len(res)
    summ["calls"] = sum(r["usage"]["calls"] for r in res)
    (ROOT / "build/series.json").write_text(json.dumps(dict(summary=summ, runs=res), indent=1))
    # the last run becomes the one shown on the screen
    (ROOT / "build/agents.json").write_text((runs / f"agents_{a.runs}.json").read_text())
    (ROOT / "build/eval.json").write_text((runs / f"eval_{a.runs}.json").read_text())
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    main(ap.parse_args())
