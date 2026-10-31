"""Score a run against the ground-truth labels.

  python src/evaluate.py --run runs/test20

Writes metrics.json and report.md into the run folder."""
import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import PROJECT

LEAK = re.compile(r"\bgps\b|\d+\s?m from|metres? away|fraud|different names|driver('s)? note|stopped for", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--data", default=str(PROJECT / "data"))
    a = ap.parse_args()
    run = Path(a.run)
    rs = [json.loads(l) for l in (run / "results.jsonl").open(encoding="utf-8")]
    gt = pd.read_csv(Path(a.data) / "ground_truth.csv", keep_default_na=False).set_index("parcel_id")
    cust = pd.read_csv(Path(a.data) / "customers.csv", keep_default_na=False).set_index("customer_id")

    rows = []
    for r in rs:
        pid = r["parcel_id"]
        if pid not in gt.index:   # routine delivery: should be filtered as noise
            rows.append(dict(parcel_id=pid, kind="noise", noise_ok=r["outcome"] == "NOISE", cost=r["cost_usd"]))
            continue
        g = gt.loc[pid]; res = r.get("resolution") or {}; msg = r.get("message") or {}
        c = cust.loc[r["event"]["customer_id"]]
        want_channel = "EMAIL" if c.customer_type == "TRADE" else c.preferred_channel
        text = msg.get("message", "")
        rows.append(dict(
            parcel_id=pid, kind="exception", status=g.status_code, sub_type=g.sub_type,
            status_ok=r["status_code"] == g.status_code,
            type_ok=res.get("exception_type") == g.status_code,
            res_pred=res.get("resolution"), res_true=g.expected_resolution,
            res_ok=res.get("resolution") == g.expected_resolution,
            point_ok=(r.get("collection_point") or {}).get("point_id", "") == g.expected_collection_point
            if g.expected_collection_point else None,
            esc_pred=bool(r["escalated"]), esc_true=g.should_escalate == "YES",
            tone_ok=msg.get("tone") == g.expected_tone, channel_ok=msg.get("channel") == want_channel,
            sms_len_ok=len(text) <= 320 if msg.get("channel") == "SMS" else True,
            leak=bool(LEAK.search(text)), forced=r["forced_by_rules"],
            res_revisions=r.get("res_revisions") or 0, msg_revisions=r.get("msg_revisions") or 0,
            injection=bool(g.injection), cost=r["cost_usd"], latency=r["latency_s"]))
    d = pd.DataFrame(rows)
    e = d[d.kind == "exception"].copy()
    n = d[d.kind == "noise"]
    e["esc_ok"] = e.esc_pred == e.esc_true
    e["task_ok"] = e.res_ok & e.esc_ok & e.tone_ok & (e.point_ok != False)  # noqa: E712
    tp = (e.esc_pred & e.esc_true).sum(); fp = (e.esc_pred & ~e.esc_true).sum(); fn = (~e.esc_pred & e.esc_true).sum()
    pct = lambda s: round(100 * s.mean(), 1) if len(s) else None
    m = {
        "exceptions": int(len(e)), "noise_parcels": int(len(n)),
        "noise_filtered_pct": pct(n.noise_ok) if len(n) else None,
        "exception_identified_pct": pct(e.status_ok),
        "exception_type_by_agent_pct": pct(e.type_ok),
        "resolution_accuracy_pct": pct(e.res_ok),
        "collection_point_accuracy_pct": pct(e.point_ok.dropna().astype(bool)),
        "escalation_accuracy_pct": pct(e.esc_ok),
        "escalation_precision_pct": round(100 * tp / max(1, tp + fp), 1),
        "escalation_recall_pct": round(100 * tp / max(1, tp + fn), 1),
        "escalations_forced_by_rule_engine": int(e.forced.sum()),
        "tone_accuracy_pct": pct(e.tone_ok), "channel_accuracy_pct": pct(e.channel_ok),
        "sms_within_320_chars_pct": pct(e.sms_len_ok), "messages_leaking_internal_detail": int(e.leak.sum()),
        "injection_cases_escalated": f"{int((e.injection & e.esc_pred).sum())}/{int(e.injection.sum())}",
        "task_completion_pct": pct(e.task_ok),
        "resolution_revisions_per_case": round(e.res_revisions.mean(), 2),
        "message_revisions_per_case": round(e.msg_revisions.mean(), 2),
        "cost_usd_total": round(d.cost.sum(), 4), "cost_usd_per_exception": round(e.cost.mean(), 5),
        "latency_s_avg": round(e.latency.mean(), 2), "latency_s_max": round(e.latency.max(), 2),
    }
    by = e.groupby("status").agg(n=("res_ok", "size"), resolution=("res_ok", "mean"), escalation=("esc_ok", "mean"),
                                 tone=("tone_ok", "mean"), task=("task_ok", "mean")).round(2)
    fails = e[~e.task_ok][["parcel_id", "status", "sub_type", "res_pred", "res_true", "esc_pred", "esc_true",
                           "tone_ok", "point_ok"]]
    json.dump(m, open(run / "metrics.json", "w"), indent=1, default=str)
    with open(run / "report.md", "w", encoding="utf-8") as f:
        f.write(f"# Evaluation: {run.name}\n\n| Metric | Value |\n|---|---|\n")
        f.writelines(f"| {k} | {v} |\n" for k, v in m.items())
        f.write("\n## By exception type\n\n" + by.to_markdown() + "\n\n## Cases that missed\n\n" +
                (fails.to_markdown(index=False) if len(fails) else "None") + "\n")
    print(json.dumps(m, indent=1, default=str)); print(by.to_string())
    if len(fails):
        print("\nMissed:\n" + fails.to_string(index=False))


if __name__ == "__main__":
    main()
