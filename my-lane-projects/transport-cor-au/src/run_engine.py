"""Run the deterministic engine over a data folder and write findings.json."""
import argparse, json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine.rules import Engine  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="build/findings.json")
    a = ap.parse_args()
    eng = Engine(Path(a.data)).run()
    out = eng.output()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print("movements:", Counter(m["rag"] for m in out["movements"]))
    print("findings:", Counter((f["rule_id"], f["rag"]) for f in out["findings"]).most_common())
