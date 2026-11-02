"""Deterministic CoR checks -> traffic-light findings per planned movement.

The engine is the only source of numbers and colours. Agents explain findings;
they never change a colour. Thresholds marked DEMO are operating procedure for the
fictional operator, not HVNL requirements (see ref/sources.md).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path

from .fatigue import Event, Timeline, check, WORK, H

RANK = {"GREEN": 0, "AMBER": 1, "RED": 2}

# DEMO operating thresholds
SERVICE_SOON_DAYS, SERVICE_SOON_KM = 2, 1000
COMPETENCY_SOON_DAYS = 14
FATIGUE_HEADROOM_MIN = 60
SPEED_RED_OVER = 10
SPEED_LOOKBACK_DAYS = 7
FEED_STALE_HOURS = 12
DECLARED_TOLERANCE = 0.05  # measured payload vs declared

# LRG 2025 tie-down, 300 kgf pre-tension, kg restrained per lashing at >=60 deg (L1 + chain row)
PER_LASHING = {("webbing", "BLOCKED", 0.4): 2000, ("webbing", "BLOCKED", 0.2): 1100,
               ("chain", "BLOCKED", 0.4): 4100, ("chain", "BLOCKED", 0.3): 3300, ("chain", "BLOCKED", 0.2): 3300}


@dataclass
class Finding:
    id: str
    area: str
    rule_id: str
    rag: str
    entity: str          # movement / vehicle / driver id the colour applies to
    movement_id: str | None
    title: str
    facts: dict
    evidence: list[str]
    source: str
    limits: str = ""


@dataclass
class MovementStatus:
    movement_id: str
    rag: str = "GREEN"
    findings: list[str] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)


def dt(s):
    return datetime.fromisoformat(s)


class Engine:
    def __init__(self, data_dir: Path):
        self.d = {p.stem: json.loads(p.read_text()) for p in Path(data_dir).glob("*.json")}
        self.meta = self.d["meta"]
        self.snapshot = dt(self.meta["snapshot"])
        self.h0 = dt(self.meta["history_start"]) - timedelta(days=1)
        self.plan_end = dt(self.meta["plan_end"])
        self.drivers = {x["id"]: x for x in self.d["drivers"]}
        self.vehicles = {x["id"]: x for x in self.d["vehicles"]}
        self.trailers = {x["id"]: x for x in self.d["trailers"]}
        self.equipment = {x["id"]: x for x in self.d["equipment"]}
        self.movements = [m for m in self.d["movements"]]
        self.planned = [m for m in self.movements if m["planned"]]
        self.findings: list[Finding] = []
        self.status = {m["id"]: MovementStatus(m["id"]) for m in self.planned}
        self._n = 0

    # ------------------------------------------------------------------
    def add(self, area, rule, rag, entity, mv, title, facts, evidence, source, limits=""):
        self._n += 1
        f = Finding(f"F{self._n:04d}", area, rule, rag, entity, mv, title, facts, evidence, source, limits)
        self.findings.append(f)
        targets = [mv] if mv else [m["id"] for m in self.planned
                                    if entity in (m["vehicle_id"], m["driver_id"], m.get("co_driver_id"), m["trailer_id"])]
        for t in targets:
            st = self.status.get(t)
            if st:
                st.findings.append(f.id)
                if RANK[rag] > RANK[st.rag]:
                    st.rag = rag
        return f

    def run(self):
        for m in self.planned:
            self.status[m["id"]].checks_run = ["fatigue", "mass", "restraint", "speed", "maintenance", "integrity"]
        self.fatigue()
        self.mass()
        self.restraint()
        self.speed()
        self.maintenance()
        self.integrity()
        return self

    # ------------------------------------------------------------------
    def events_for(self, driver_id):
        evs_h, evs_p, ids = [], [], {}
        for e in self.d["ewd"]:
            if e["driver_id"] != driver_id:
                continue
            ev = Event(dt(e["start"]), dt(e["end"]), "work" if e["activity"] == "work" else "rest",
                       stationary=e.get("stationary", True), sleeper_moving=e.get("sleeper_moving", False),
                       record_id=e["id"])
            (evs_p if e.get("planned") else evs_h).append(ev)
        return sorted(evs_h, key=lambda e: e.start), sorted(evs_p, key=lambda e: e.start)

    def fatigue(self):
        for did, drv in self.drivers.items():
            hist, plan = self.events_for(did)
            if not plan:
                continue
            # rest fills the gaps between records (rest is "any time that is not work time")
            hist = fill_rest(hist, self.h0, self.plan_end + timedelta(days=1))
            plan_ev = [e for e in plan]
            hist_wo = remove_overlap(hist, plan_ev)
            scheme = drv["scheme"]
            res = check(hist_wo, self.h0, self.plan_end + timedelta(days=1), scheme, plan_ev, only_planned=True)
            mvs = sorted([m for m in self.planned if did in (m["driver_id"], m.get("co_driver_id"))], key=lambda m: m["depart"])
            shifts = group_shifts(plan_ev)
            tl_all = Timeline(hist_wo, self.h0, self.plan_end + timedelta(days=1), plan_ev)
            for br in res.breaches:
                sh, t_point = causing_shift(tl_all, shifts, br)
                cands = [m for m in mvs if dt(m["depart"]) - timedelta(hours=1) <= t_point]
                mv = cands[-1] if cands else (mvs[0] if mvs else None)
                multi_day = any(k in br.rule_id for k in ("7D", "14D", "52H"))
                start_ok = None if multi_day else earliest_shift(hist_wo, plan_ev, sh, self.h0, self.plan_end + timedelta(days=2), scheme)
                fix = FIXES.get(br.rule_id.rsplit("-", 1)[0] if multi_day else "", "")
                self.add("Fatigue", br.rule_id, "RED", did, mv and mv["id"],
                         f"{drv['name']}: planned shift breaches {rule_label(br.rule_id)}",
                         dict(driver=drv["name"], scheme=scheme, rule=br.rule_id, detail=br.detail,
                              window_start=br.window_start.isoformat(timespec="minutes"),
                              window_end=br.window_end.isoformat(timespec="minutes"),
                              planned_start=sh[0].isoformat(timespec="minutes"),
                              earliest_compliant_start=start_ok and start_ok.isoformat(timespec="minutes"),
                              fix=fix or (start_ok and f"Earliest compliant start {start_ok:%a %H:%M}") or "Reassign the shift"),
                         [e.record_id for e in hist_wo if e.end > br.window_start and e.start < br.window_end and e.record_id][:40],
                         "F1/F2/F4", "Standard hours only; exemptions, ACH/BFM/AFM and fitness for duty not assessed.")
            if res.incomplete:
                for m in mvs:
                    self.add("Fatigue", "FAT-RECORDS", "AMBER", did, m["id"], f"{drv['name']}: work diary incomplete",
                             dict(detail="; ".join(res.incomplete)), [], "F4")
            if res.breaches:
                continue
            # headroom on 24 h and 7 d work limits for each planned shift
            tl = Timeline(hist_wo, self.h0, self.plan_end + timedelta(days=1), plan_ev)
            for sh in shifts:
                hr = headroom(tl, sh, scheme)
                if hr is not None and hr < FATIGUE_HEADROOM_MIN:
                    mv = next((m for m in mvs if sh[0] - timedelta(hours=1) <= dt(m["depart"]) <= sh[1]), None)
                    self.add("Fatigue", "FAT-HEADROOM", "AMBER", did, mv and mv["id"],
                             f"{drv['name']}: only {hr} min left on the 24 h work limit",
                             dict(driver=drv["name"], headroom_min=hr, planned_start=sh[0].isoformat(timespec="minutes")),
                             [], "F1/F4")

    # ------------------------------------------------------------------
    def mass(self):
        wb = {w["movement_id"]: w for w in self.d["weighbridge"]}
        for m in self.planned:
            w = wb.get(m["movement_id"] if "movement_id" in m else m["id"])
            v = self.vehicles[m["vehicle_id"]]
            if not w or (w["status"] == "missing"):
                self.add("Mass & dimension", "MASS-NO-EVIDENCE", "RED", m["id"], m["id"],
                         "No weighbridge ticket or JSEA for this load",
                         dict(declared_kg=m["declared_kg"], load_type=m["load_type"]), [], "M1 + DEMO",
                         "Missing evidence is treated as a stop, not a pass.")
                continue
            if not w.get("jsea", True):
                self.add("Mass & dimension", "MASS-NO-JSEA", "RED", m["id"], m["id"], "Pre-dispatch JSEA not completed",
                         dict(load_type=m["load_type"]), [w.get("ticket", "")], "DEMO")
            if w["status"] == "not_due":
                continue  # weighed closer to departure; the check reruns then
            if w["status"] == "pending":
                self.add("Mass & dimension", "MASS-PENDING", "AMBER", m["id"], m["id"],
                         "Weighbridge ticket due before departure",
                         dict(declared_kg=m["declared_kg"], depart=m["depart"]), [], "DEMO")
                continue
            gross_t = w["gross_kg"] / 1000
            facts = dict(gross_t=round(gross_t, 2), limit_t=v["gcm_limit_t"], declared_kg=m["declared_kg"],
                         measured_payload_kg=w["gross_kg"] - m["tare_kg"], customer=m["customer_id"])
            if gross_t > v["gcm_limit_t"]:
                self.add("Mass & dimension", "MASS-OVER-GML", "RED", m["id"], m["id"],
                         f"Measured {gross_t:.1f} t over the {v['gcm_limit_t']} t limit", facts, [w["ticket"]], "M1")
            payload = w["gross_kg"] - m["tare_kg"]
            if payload > m["declared_kg"] * (1 + DECLARED_TOLERANCE):
                self.add("Mass & dimension", "MASS-DECLARED-LOW", "AMBER", m["id"], m["id"],
                         f"Declared weight {100 * (payload / m['declared_kg'] - 1):.0f}% under weighbridge",
                         facts, [w["ticket"]], "DEMO")
            if w.get("steer_kg", 0) / 1000 > v["steer_limit_t"]:
                self.add("Mass & dimension", "MASS-STEER", "RED", m["id"], m["id"], "Steer axle over limit",
                         dict(steer_t=w["steer_kg"] / 1000, limit_t=v["steer_limit_t"]), [w["ticket"]], "M1")

    def restraint(self):
        rs = {r["movement_id"]: r for r in self.d["restraint"]}
        for m in self.planned:
            r = rs.get(m["id"])
            if not r:
                self.add("Load restraint", "LR-NO-PLAN", "RED", m["id"], m["id"], "No load restraint plan", {}, [], "L1")
                continue
            need = PER_LASHING.get((r["lashing"], "BLOCKED" if r["blocked"] else "UNBLOCKED", r["friction"]))
            if need:
                req = -(-r["heaviest_row_kg"] // need)
                if r["lashings_per_row"] < req:
                    self.add("Load restraint", "LR-UNDER-TABLE", "RED", m["id"], m["id"],
                             f"{r['lashings_per_row']} lashings per row; table needs {req}",
                             dict(row_kg=r["heaviest_row_kg"], lashing=r["lashing"], friction=r["friction"],
                                  per_lashing_kg=need, planned=r["lashings_per_row"], required=req), [], "L1 p.207")
            drv = self.drivers[r["competent_person_id"]]
            exp = datetime.fromisoformat(drv["restraint_competency_expiry"]).date()
            dep = dt(m["depart"]).date()
            if exp < dep:
                self.add("Load restraint", "LR-COMPETENCY-EXPIRED", "RED", m["id"], m["id"],
                         f"{drv['name']}'s restraint competency expired {exp:%d %b}",
                         dict(person=drv["name"], expiry=exp.isoformat()), [drv["id"]], "DEMO")
            elif (exp - dep).days <= COMPETENCY_SOON_DAYS:
                self.add("Load restraint", "LR-COMPETENCY-SOON", "AMBER", m["id"], m["id"],
                         f"{drv['name']}'s restraint competency expires {exp:%d %b}",
                         dict(person=drv["name"], expiry=exp.isoformat(), days=(exp - dep).days), [drv["id"]], "DEMO")
            for eid in r["equipment_ids"]:
                e = self.equipment[eid]
                if e["result"] != "pass" or not e["rated"]:
                    self.add("Load restraint", "LR-EQUIPMENT-FAILED", "RED", m["id"], m["id"],
                             f"{eid} failed inspection on {e['last_inspection']} but is on this load",
                             dict(equipment=eid, kind=e["kind"], result=e["result"], inspected=e["last_inspection"]),
                             [eid], "L1 p.205")

    def speed(self):
        ev = self.d["speed_events"]
        acts = {a["ref"] for a in self.d["actions"] if a.get("type") == "speed_followup"}
        cut = self.snapshot - timedelta(days=SPEED_LOOKBACK_DAYS)
        by_driver = {}
        for e in ev:
            if dt(e["at"]) >= cut:
                by_driver.setdefault(e["driver_id"], []).append(e)
        for did, es in by_driver.items():
            drv = self.drivers[did]
            mvs = [m for m in self.planned if m["driver_id"] == did]
            if not mvs:
                continue
            first = min(mvs, key=lambda m: m["depart"])["id"]
            uncertain = [e for e in es if e["limit_confidence"] == "low"]
            sure = [e for e in es if e["limit_confidence"] != "low"]
            big = [e for e in sure if e["peak_kph"] - e["limit_kph"] >= SPEED_RED_OVER and e["id"] not in acts]
            small_open = [e for e in sure if e["peak_kph"] - e["limit_kph"] < SPEED_RED_OVER and e["id"] not in acts]
            facts = dict(driver=drv["name"], events=len(sure),
                         max_over=max([e["peak_kph"] - e["limit_kph"] for e in sure], default=0),
                         seconds=sum(e["duration_s"] for e in sure),
                         locations=sorted({e["location"] for e in sure}),
                         followed_up=sum(e["id"] in acts for e in sure))
            if big:
                self.add("Speed", "SPD-OVER-10", "RED", did, first,
                         f"{drv['name']}: {len(big)} event(s) 10+ km/h over, no follow-up", facts,
                         [e["id"] for e in sure], "DEMO")
            elif small_open and (len(small_open) >= 2 or any(e.get("zone_transition") for e in small_open)):
                self.add("Speed", "SPD-WATCH", "AMBER", did, first,
                         f"{drv['name']}: {len(small_open)} minor event(s) under 10 km/h over",
                         facts, [e["id"] for e in small_open], "DEMO")
            for e in uncertain:
                self.add("Speed", "SPD-LIMIT-UNVERIFIED", "AMBER", did, first,
                         f"Event {e['peak_kph']} km/h against a low-confidence mapped {e['limit_kph']} km/h",
                         dict(event=e["id"], location=e["location"], limit_source=e["limit_source"]), [e["id"]], "DEMO",
                         "Verify the posted limit before treating this as speeding.")

    def maintenance(self):
        defects = self.d["defects"]
        bookings = self.d["workshop_bookings"]
        for m in self.planned:
            v = self.vehicles[m["vehicle_id"]]
            due_km = v["last_service_km"] + v["service_interval_km"]
            dep = dt(m["depart"])
            after_trip = v["odometer_km"] + projected_km(self.planned, v["id"], dep)
            due_date = datetime.fromisoformat(v["service_due_date"]).date()
            facts = dict(vehicle=v["id"], odometer_km=v["odometer_km"], due_km=due_km, km_after_trip=after_trip,
                         due_date=due_date.isoformat())
            if after_trip > due_km or due_date < dep.date():
                self.add("Maintenance", "MNT-SERVICE-OVERDUE", "RED", v["id"], m["id"],
                         f"{v['id']} passes its service point on this trip", facts, [v["id"]], "DEMO")
            elif due_km - after_trip <= SERVICE_SOON_KM or (due_date - dep.date()).days <= SERVICE_SOON_DAYS:
                self.add("Maintenance", "MNT-SERVICE-SOON", "AMBER", v["id"], m["id"],
                         f"{v['id']} service due {due_date:%a %d %b} / {due_km - after_trip:,} km", facts, [v["id"]], "DEMO")
            for d in defects:
                if d["asset_id"] in (v["id"], m["trailer_id"]) and d["status"] == "open":
                    rag = "RED" if d["severity"] == "major" else "AMBER"
                    self.add("Maintenance", "MNT-OPEN-DEFECT", rag, d["asset_id"], m["id"],
                             f"Open {d['severity']} defect on {d['asset_id']}: {d['description']}",
                             dict(defect=d["id"], severity=d["severity"], reported=d["reported"]), [d["id"]], "DEMO")
            for b in bookings:
                if b["vehicle_id"] == v["id"] and dt(b["start"]) < dt(m["arrive_window"]) + timedelta(hours=2) and dt(b["end"]) > dep:
                    self.add("Maintenance", "MNT-BOOKING-CLASH", "AMBER", v["id"], m["id"],
                             f"{v['id']} is booked into the workshop {dt(b['start']):%a %H:%M} while dispatched",
                             dict(booking=b["id"], start=b["start"], end=b["end"], depart=m["depart"]), [b["id"]], "DEMO")

    def integrity(self):
        # vehicle moved while no logged-in driver was on work time
        ewd = {}
        for e in self.d["ewd"]:
            if e["activity"] == "work" and not e.get("planned"):
                ewd.setdefault(e["driver_id"], []).append((dt(e["start"]), dt(e["end"])))
        for t in self.d["trips"]:
            s, e = dt(t["start"]), dt(t["end"])
            did = t.get("login_driver_id")
            ok = did and any(a <= s and e <= b + timedelta(minutes=1) for a, b in ewd.get(did, []))
            if not ok:
                assigned = t.get("assigned_driver_id") or did
                self.add("Integrity", "INT-UNRECORDED-DRIVER", "RED", t["vehicle_id"], None,
                         f"{t['vehicle_id']} moved {s:%a %d %b %H:%M}-{e:%H:%M} with no matching work diary entry",
                         dict(trip=t["id"], km=t["km"], login=did, assigned_driver=assigned and self.drivers[assigned]["name"]),
                         [t["id"]], "DEMO", "Driver identity is not inferred from the vehicle; someone must confirm who drove.")
        for f in self.d["feed_status"] if isinstance(self.d["feed_status"], list) else []:
            age = (self.snapshot - dt(f["last_received"])).total_seconds() / 3600
            if age > FEED_STALE_HOURS:
                self.add("Integrity", "INT-FEED-STALE", "AMBER", f["vehicle_id"], None,
                         f"No telematics from {f['vehicle_id']} for {age:.0f} h",
                         dict(unit=f["unit"], last_received=f["last_received"], hours=round(age)), [], "DEMO",
                         "Speed and trip checks for this vehicle are incomplete.")

    # ------------------------------------------------------------------
    def output(self):
        return dict(meta=self.meta,
                    movements=[dict(asdict(s), **{k: m[k] for k in ("driver_id", "co_driver_id", "vehicle_id", "trailer_id",
                                                                   "customer_id", "lane", "destination", "depart", "load_type")})
                               for s, m in ((self.status[m["id"]], m) for m in self.planned)],
                    findings=[asdict(f) for f in self.findings])


FIXES = {"FAT-7D": "Give a 24 h continuous rest before the next shift, or reassign",
         "FAT-14D": "Plan night rest breaks before more work in this 14-day period",
         "FAT-52H": "Give a 10 h continuous stationary rest before the next shift"}


def causing_shift(tl, shifts, br):
    """Returns (shift, time point). WORK rules: the minute the window's work first exceeds the
    limit. REST rules: the last planned work minute inside the window (it interrupts the rest)."""
    a, b = tl.idx(br.window_start), min(tl.idx(br.window_end), tl.n)
    seg_work = tl.state[a:b] == WORK
    if br.rule_id.endswith("WORK"):
        mx = {"24H": 720, "7D": 72 * 60, "14D": 144 * 60}.get(br.rule_id.split("-")[1], 720)
        cum = seg_work.cumsum()
        k = int((cum > mx).argmax()) if (cum > mx).any() else len(cum) - 1
    else:
        pk = (seg_work & tl.planned[a:b]).nonzero()[0]
        k = int(pk[-1]) if len(pk) else len(seg_work) - 1
    t = tl.time(a + k)
    sh = next((s for s in shifts if s[0] <= t <= s[1]), shifts[-1])
    return sh, t


def rule_label(rule):
    return {"FAT-24H-REST": "the 7 h major rest in its 24 h period", "FAT-24H-WORK": "12 h work in 24 h",
            "FAT-7D-WORK": "72 h work in 7 days", "FAT-7D-REST": "the 24 h rest in 7 days",
            "FAT-14D-WORK": "144 h work in 14 days", "FAT-14D-NIGHTS": "night rests in 14 days",
            "FAT-52H-REST": "the two-up 10 h rest in 52 h", "FAT-5.5H": "the 5.5 h rule",
            "FAT-8H": "the 8 h rule", "FAT-11H": "the 11 h rule"}.get(rule, rule)


def fill_rest(events, t0, t1):
    out, cur = [], t0
    for e in sorted(events, key=lambda e: e.start):
        if e.start > cur:
            out.append(Event(cur, e.start, "rest"))
        out.append(e)
        cur = max(cur, e.end)
    if cur < t1:
        out.append(Event(cur, t1, "rest"))
    return out


def remove_overlap(hist, plan):
    """Drop gap-filled rest that sits under planned events (planned records win)."""
    out = []
    for e in hist:
        if e.record_id:
            out.append(e)
            continue
        pieces = [(e.start, e.end)]
        for p in plan:
            nxt = []
            for a, b in pieces:
                if p.end <= a or p.start >= b:
                    nxt.append((a, b))
                else:
                    if a < p.start:
                        nxt.append((a, p.start))
                    if p.end < b:
                        nxt.append((p.end, b))
            pieces = nxt
        out += [Event(a, b, "rest") for a, b in pieces if b > a]
    return out


def group_shifts(plan):
    work = sorted([e for e in plan if e.activity == "work"], key=lambda e: e.start)
    shifts = []
    for e in work:
        if shifts and e.start - shifts[-1][1] < timedelta(hours=5):
            shifts[-1][1] = max(shifts[-1][1], e.end)
        else:
            shifts.append([e.start, e.end])
    return [tuple(s) for s in shifts]


def earliest_shift(hist, plan, shift, t0, t1, scheme, step=15, max_hours=36):
    sh_ev = [e for e in plan if e.start >= shift[0] - timedelta(minutes=1) and e.end <= shift[1] + timedelta(minutes=1)]
    others = [e for e in plan if e not in sh_ev and e.start < shift[0]]
    for k in range(0, max_hours * 60 // step + 1):
        d = timedelta(minutes=k * step)
        moved = [Event(e.start + d, e.end + d, e.activity, e.stationary, e.sleeper_moving) for e in sh_ev]
        r = check(remove_overlap(hist, others + moved), t0, t1 + d, scheme, others + moved, only_planned=True)
        if not any(b.window_end > moved[0].start for b in r.breaches):
            return moved[0].start
    return None


def headroom(tl: Timeline, shift, scheme):
    """Least spare work minutes in any 24 h period (from end of a 7 h rest) that holds this shift."""
    major = 7 * H if scheme == "solo" else 5 * H
    a_i, b_i = tl.idx(shift[0]), tl.idx(shift[1])
    best = None
    for s, e in tl.rest_runs():
        if e - s >= major and e <= a_i and e + 24 * H > a_i:
            w = int((tl.state[e:e + 24 * H] == WORK).sum())
            spare = 12 * H - w
            best = spare if best is None else min(best, spare)
    return best


def projected_km(planned, vehicle_id, until):
    return sum(m["distance_km"] * 2 for m in planned if m["vehicle_id"] == vehicle_id and dt(m["depart"]) <= until)
