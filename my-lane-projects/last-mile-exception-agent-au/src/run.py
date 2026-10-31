"""Run the exception pipeline over the synthetic day and record every step.

Examples (from the project folder):
  python src/run.py --env "C:/path/to/.env" --sample 20 --out runs/test20
  python src/run.py --env "C:/path/to/.env" --all --workers 6 --out runs/full      # resumable
  python src/run.py --dry-run --sample 5 --out runs/dry                              # no API key needed

Writes results.jsonl (one line per parcel, with the full trace) and wismo.jsonl to --out.
Cases are chosen from the scans and customer contacts only; ground_truth.csv is never read here.
"""
import argparse
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agents as A
from config import DEFAULT_AGENT_MODEL, DEFAULT_CRITIC_MODEL, PROJECT, load_env
from graph import build
from llm import Claude
from world import World

OUTCOMES = {"ATTEMPTED", "ACCESS_ISSUE", "ADDRESS_ISSUE", "DAMAGED", "REFUSED", "WEATHER_DELAY", "HEAT_HOLD",
            "VEHICLE_DELAY", "ROAD_CLOSURE"}


def candidate_cases(world):
    """Parcels whose scans show an exception, plus delivered parcels a customer has reported missing."""
    s = world.scans
    exc = s[s.status_code.isin(OUTCOMES)].groupby("parcel_id").status_code.last().to_dict()
    for r in world.contacts.itertuples():
        if r.contact_type == "DNR":
            exc[r.parcel_id] = "DELIVERED_NOT_RECEIVED"
    return exc


def pick(world, args):
    cases = candidate_cases(world)
    rnd = random.Random(args.seed)
    if args.ids:
        ids = args.ids.split(",")
    elif args.all:
        ids = list(cases)
    else:   # stratified: round-robin across exception types so a small sample covers the day
        by = {}
        for pid, code in sorted(cases.items()):
            by.setdefault(code, []).append(pid)
        for v in by.values():
            rnd.shuffle(v)
        # always include the awkward ones
        must = [pid for pid in cases if world.contacts_for(pid)][:3]
        inj = [pid for pid in cases if any("IGNORE" in r["status_description"].upper() or "OVERRIDE" in
                                           r["status_description"].upper() for r in world.read_scans(pid))][:1]
        ids = list(dict.fromkeys(must + inj))
        keys = sorted(by)
        while len(ids) < args.sample and any(by.values()):
            for k in keys:
                if by[k] and len(ids) < args.sample:
                    pid = by[k].pop()
                    if pid not in ids:
                        ids.append(pid)
    noise = [p for p in world.parcels.index if p not in cases]
    ids += rnd.sample(noise, args.noise) if args.noise else []
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(PROJECT / "data"))
    ap.add_argument("--env", help="Path to your .env file (ANTHROPIC_API_KEY=...)")
    ap.add_argument("--out", default=str(PROJECT / "runs" / "test"))
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--sample", type=int, default=20)
    g.add_argument("--all", action="store_true")
    g.add_argument("--ids")
    ap.add_argument("--noise", type=int, default=3, help="Also run this many routine deliveries (no LLM calls)")
    ap.add_argument("--wismo", type=int, default=5, help="Answer this many 'where's my parcel?' enquiries (-1 = all)")
    ap.add_argument("--agent-model", default=DEFAULT_AGENT_MODEL)
    ap.add_argument("--critic-model", default=DEFAULT_CRITIC_MODEL)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.dry_run:
        found = load_env(args.env)
        print(f"Credentials: {'loaded from ' + str(found) if found else 'from environment'}")
    world = World(args.data)
    llm = Claude((PROJECT / "playbook" / "exception_playbook.md").read_text(encoding="utf-8"), dry_run=args.dry_run)
    graph = build(world, llm, args.agent_model, args.critic_model)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    res_path = out / "results.jsonl"
    done = {json.loads(l)["parcel_id"] for l in res_path.open()} if res_path.exists() else set()
    ids = [i for i in pick(world, args) if i not in done]
    total_cases = len(candidate_cases(world))
    print(f"{len(ids)} parcels to run ({len(done)} already done) | agents {args.agent_model} | critics {args.critic_model}")

    lock = threading.Lock(); spent = [0.0]; n_llm = [0]; t_start = time.time()

    def one(pid):
        t0 = time.time()
        s = graph.invoke({"parcel_id": pid, "trace": []}, {"recursion_limit": 60})
        cost = sum(t.get("cost_usd", 0) for t in s["trace"])
        rec = {"parcel_id": pid, "outcome": s["outcome"], "status_code": s["event"]["status_code"],
               "event": s["event"], "rule_engine": s.get("rule_engine"), "resolution": s.get("resolution"),
               "res_revisions": s.get("res_revisions"), "collection_point": s.get("collection_point"),
               "escalated": s.get("escalated", False), "escalation_reasons": s.get("escalation_reasons", []),
               "forced_by_rules": s.get("forced_by_rules", False), "message": s.get("message"),
               "msg_revisions": s.get("msg_revisions"), "cost_usd": round(cost, 6),
               "latency_s": round(time.time() - t0, 2), "trace": s["trace"]}
        return rec, cost

    with ThreadPoolExecutor(args.workers) as ex, res_path.open("a", encoding="utf-8") as f:
        futs = {ex.submit(one, pid): pid for pid in ids}
        for i, fu in enumerate(as_completed(futs), 1):
            pid = futs[fu]
            try:
                rec, cost = fu.result()
            except Exception as e:   # keep going; failed parcels can be re-run with the same --out
                print(f"  ! {pid}: {type(e).__name__}: {e}")
                continue
            with lock:
                f.write(json.dumps(rec, default=str) + "\n"); f.flush()
                spent[0] += cost; n_llm[0] += rec["outcome"] != "NOISE"
            if i % 10 == 0 or i == len(ids):
                per = spent[0] / max(1, n_llm[0])
                print(f"  {i}/{len(ids)} done | spent ${spent[0]:.3f} | ${per:.4f} per exception | "
                      f"projected full day (~{total_cases:,} exceptions) ${per * total_cases:,.2f} | "
                      f"{time.time() - t_start:.0f}s")

    if args.wismo:
        run_wismo(world, llm, args, out)


def run_wismo(world, llm, args, out):
    decisions = {}
    p = out / "results.jsonl"
    if p.exists():
        for l in p.open():
            r = json.loads(l)
            if r.get("resolution"):
                decisions[r["parcel_id"]] = r
    q = world.contacts[world.contacts.contact_type == "WISMO"]
    q = q if args.wismo < 0 else q.head(args.wismo)
    with (out / "wismo.jsonl").open("w", encoding="utf-8") as f:
        for r in q.itertuples():
            scans = [s for s in world.read_scans(r.parcel_id)
                     if s["timestamp"] <= r.contact_time and s["is_duplicate_scan"] != "True"]
            for s in scans:
                s.pop("customer_id", None); s.pop("delivery_address", None)
            d = decisions.get(r.parcel_id)
            decided = d and d["event"]["event_time"] <= r.contact_time
            payload = {"question_time": r.contact_time, "question": r.message, "scans_so_far": scans,
                       "calendar": world.calendar(),
                       "decision_already_made": {"resolution": d["resolution"]["resolution"],
                                                 "collection_point": d.get("collection_point"),
                                                 "escalated": d["escalated"]} if decided else None}
            ans, use = llm.call(args.agent_model, A.WISMO_TASK, payload, A.WismoOut, max_tokens=300)
            f.write(json.dumps({"contact_id": r.contact_id, "parcel_id": r.parcel_id, "time": r.contact_time,
                                "question": r.message, **ans, "cost_usd": use["cost_usd"]}) + "\n")
    print(f"WISMO: answered {len(q)} enquiries -> {out / 'wismo.jsonl'}")


if __name__ == "__main__":
    main()
