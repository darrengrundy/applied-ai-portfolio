"""Seeded synthetic fleet for Wattlebark Haulage (fictional), Laverton North VIC.

Writes JSON feeds + ground-truth labels to --out (default data/).
History: Mon 5 Oct - Sun 1 Nov 2026. Snapshot: Mon 2 Nov 2026 05:30 AEDT.
Plan: movements departing Mon 2 Nov 05:30 - end of Wed 4 Nov.

Storylines are injected after a clean baseline and labelled with the expected
traffic light, decision, root cause and accountable CoR party.
"""
from __future__ import annotations

import argparse, json, random
from datetime import datetime, timedelta, date
from pathlib import Path
from zoneinfo import ZoneInfo

MEL = ZoneInfo("Australia/Melbourne")
SEED = 20261102
HIST_START = datetime(2026, 10, 5, 0, 0, tzinfo=MEL)
SNAPSHOT = datetime(2026, 11, 2, 5, 30, tzinfo=MEL)
PLAN_END = datetime(2026, 11, 5, 0, 0, tzinfo=MEL)

FIRST = ["Aaron", "Bree", "Callum", "Dimitri", "Ella", "Faisal", "Grace", "Hamish", "Indira", "Jarrah",
         "Kieran", "Leila", "Marco", "Nadia", "Owen", "Priya", "Quinn", "Rhys", "Sione", "Tara",
         "Usha", "Vince", "Wade", "Xavier", "Yasmin", "Zac", "Brodie", "Carmen", "Declan", "Ebony",
         "Finn", "Gemma", "Hugo", "Isla", "Jai", "Kat"]
LAST = ["Achterberg", "Bellwood", "Castellan", "Dunleavy", "Ekström", "Fairweather", "Galbraith",
        "Holloway", "Iredale", "Jankowski", "Kowalczyk", "Lombardo", "McAlister", "Nguyen-Hale",
        "O'Rourke", "Pettigrew", "Quaresma", "Rowntree", "Sefo", "Thistlewood", "Uren", "Vasilakis",
        "Whitcombe", "Xuereb", "Yallop", "Zielinski", "Brockhurst", "Cardamone", "Dellaportas", "Eastaugh",
        "Foulsham", "Greenhalgh", "Hartigan", "Ingleby", "Jessop", "Kerridge"]

# lane: (destination, one-way drive minutes, km, speed stretch)
LANES = {
    "GEE": ("Geelong (Corio)", 60, 62, "Princes Fwy, Avalon"),
    "BAL": ("Ballarat (Wendouree)", 90, 118, "Western Fwy, Bacchus Marsh"),
    "BEN": ("Bendigo (Epsom)", 120, 160, "Calder Fwy, Kyneton"),
    "ALB": ("Wodonga (Logic)", 210, 310, "Hume Fwy, Seymour"),
    "MET": ("Melbourne metro drops", 45, 40, "Western Ring Rd, Sunshine West"),
    "SYD": ("Sydney (Moorebank)", 600, 880, "Hume Hwy, Gundagai"),
}
CUSTOMERS = {
    "C1": ("Brackenridge Steel Supply", "steel"),
    "C2": ("Tumbarumba Timber Co.", "timber"),
    "C3": ("Greyfield Building Products", "building"),
    "C4": ("Corella Home Retail", "pallets"),
    "C5": ("Ashgrove Beverages", "pallets"),
    "C6": ("Kestrel Machinery Hire", "machinery"),
}
LOAD_LASHING = {"steel": ("chain", 0.2), "timber": ("webbing", 0.4), "building": ("webbing", 0.4),
                "pallets": ("webbing", 0.4), "machinery": ("chain", 0.3)}

R = random.Random(SEED)


def iso(t):
    return t.isoformat(timespec="minutes")


class Fleet:
    def __init__(self):
        self.drivers, self.vehicles, self.trailers = [], [], []
        self.movements, self.ewd, self.speed, self.trips = [], [], [], []
        self.weighbridge, self.restraint, self.equipment, self.defects = [], [], [], []
        self.bookings, self.actions, self.labels, self.feeds = [], [], [], {}
        self._n = 0

    def nid(self, p):
        self._n += 1
        return f"{p}-{self._n:05d}"


def build():
    f = Fleet()
    # --- people and assets -------------------------------------------------
    names = [f"{a} {b}" for a, b in zip(FIRST, LAST)]
    for i, nm in enumerate(names):
        scheme = "two_up" if i >= 32 else "solo"
        start_h = R.choice([5, 5, 6, 6, 6, 7, 7, 8]) if scheme == "solo" else 18
        f.drivers.append(dict(id=f"D{i+1:02d}", name=nm, scheme=scheme, base="Laverton North VIC",
                              base_tz="Australia/Melbourne", usual_start=f"{start_h:02d}:00",
                              lane=("SYD" if scheme == "two_up" else R.choice(["GEE", "BAL", "BEN", "ALB", "MET", "MET"])),
                              restraint_competency_expiry=(date(2027, 1, 1) + timedelta(days=R.randint(0, 600))).isoformat(),
                              pair=(f"D{33 + (i - 32) // 2 * 2:02d}-D{34 + (i - 32) // 2 * 2:02d}" if scheme == "two_up" else None)))
    for i in range(30):
        f.vehicles.append(dict(id=f"PM{i+1:02d}", type="prime mover" if i < 24 else "rigid",
                               config="6-axle semi (GML)" if i < 24 else "3-axle rigid (GML)",
                               gcm_limit_t=(44.0 if i % 3 else 43.5) if i < 24 else 22.5, steer_limit_t=6.5 if i % 3 else 6.0,
                               odometer_km=R.randint(180_000, 720_000), service_interval_km=25_000,
                               last_service_km=None, service_due_date=None, telematics_unit=f"TU{i+1:02d}"))
    for v in f.vehicles:
        v["last_service_km"] = v["odometer_km"] - R.randint(2_000, 18_000)
        v["service_due_date"] = (SNAPSHOT.date() + timedelta(days=R.randint(10, 80))).isoformat()
    for i in range(34):
        f.trailers.append(dict(id=f"TR{i+1:02d}", type=R.choice(["flat-top", "curtainsider", "drop-deck"]),
                               headboard_rated=True))
    for i in range(80):
        kind = R.choice(["webbing", "webbing", "webbing", "chain"])
        f.equipment.append(dict(id=f"EQ{i+1:03d}", kind=kind, rated=True,
                                last_inspection=(SNAPSHOT.date() - timedelta(days=R.randint(1, 80))).isoformat(),
                                result="pass", in_service=True))

    # --- baseline history and plan -------------------------------------------
    solo = [d for d in f.drivers if d["scheme"] == "solo"]
    vehicles = iter(f.vehicles)
    assigned = {d["id"]: next(vehicles) for d in solo[:24]}
    rigids = [v for v in f.vehicles if v["type"] == "rigid"]
    for k, d in enumerate(solo[24:]):
        assigned[d["id"]] = rigids[k % len(rigids)]
    day = HIST_START.date()
    while datetime.combine(day, datetime.min.time(), tzinfo=MEL) < PLAN_END - timedelta(hours=5):
        for d in solo:
            if day.weekday() == 6 or (day.weekday() == 5 and R.random() < 0.7):
                continue
            if R.random() < 0.06:
                continue  # leave / day off
            h, m = map(int, d["usual_start"].split(":"))
            start = datetime(day.year, day.month, day.day, h, m, tzinfo=MEL) + timedelta(minutes=R.choice([0, 0, 15, 30, -15] if h > 5 else [0, 0, 15, 30]))
            if start < HIST_START or start >= PLAN_END:
                continue
            shift(f, d, assigned[d["id"]], start, d["lane"])
        day += timedelta(days=1)
    linehaul(f)
    for v in f.vehicles:
        v["last_service_km"] = v["odometer_km"] - R.randint(2_000, 18_000)
    return f


def shift(f, d, v, start, lane, planned=None, extra_work=0):
    """One driver day: pre-start + load, drive out, unload, drive back, breaks every <=5 h."""
    dest, mins, km, _ = LANES[lane]
    runs = 3 if lane == "MET" else (2 if mins <= 90 else 1)
    t = start
    blocks = []
    blocks.append(("work", 45 + extra_work, "pre-start checks and loading"))
    for r in range(runs):
        blocks += [("work", mins, f"drive to {dest}"), ("work", 30, "unloading"), ("work", mins, "return to Laverton North")]
        if r < runs - 1:
            blocks += [("work", 40, "reload")]
    blocks.append(("work", 20, "post-trip and depot duties"))
    # insert 30-min breaks so no more than 4 h 45 m continuous work
    out, run = [], 0
    for kind, m, desc in blocks:
        while m > 0:
            take = min(m, 285 - run)
            out.append((kind, take, desc))
            run += take
            m -= take
            if run >= 285:
                out.append(("rest", 30, "meal break"))
                run = 0
    is_planned = start >= SNAPSHOT if planned is None else planned
    mv_ids = []
    for r in range(runs):
        cust = R.choice([c for c in CUSTOMERS if (lane != "SYD")])
        mv_ids.append(movement(f, d, v, start + timedelta(minutes=45 + r * (2 * mins + 70)), lane, cust, is_planned))
    for kind, m, desc in out:
        f.ewd.append(dict(id=f.nid("EWD"), driver_id=d["id"], start=iso(t), end=iso(t + timedelta(minutes=m)),
                          activity=kind, stationary=True, detail=desc, planned=is_planned,
                          provider="DemoEWD", base_tz="Australia/Melbourne"))
        if kind == "work" and desc.startswith(("drive", "return")) and not is_planned:
            f.trips.append(dict(id=f.nid("TRP"), vehicle_id=v["id"], start=iso(t), end=iso(t + timedelta(minutes=m)),
                                login_driver_id=d["id"], km=round(km * m / mins)))
            v["odometer_km"] += round(km * m / mins)
        t += timedelta(minutes=m)
    return mv_ids


def movement(f, d, v, depart, lane, cust, planned, co_driver=None):
    dest, mins, km, stretch = LANES[lane]
    load_type = CUSTOMERS[cust][1]
    trailer = f.trailers[(int(v["id"][2:]) - 1) % len(f.trailers)]
    payload = R.randint(14_000, 24_000) if v["type"] == "prime mover" else R.randint(6_000, 11_000)
    tare = 16_500 if v["type"] == "prime mover" else 9_800
    f._mv = getattr(f, "_mv", 0) + 1
    mid = f"MV{depart:%m%d}-{f._mv:04d}"
    lash_kind, mu = LOAD_LASHING[load_type]
    per_lash = {"webbing": 2000, "chain": 4100}[lash_kind] if mu >= 0.4 else {"webbing": 1100, "chain": 3300}[lash_kind]
    rows = max(1, payload // 2800)
    m = dict(id=mid, planned=planned, driver_id=d["id"], co_driver_id=co_driver, vehicle_id=v["id"], trailer_id=trailer["id"],
             customer_id=cust, lane=lane, origin="Laverton North VIC", destination=dest, depart=iso(depart),
             arrive_window=iso(depart + timedelta(minutes=mins + 30)), load_type=load_type,
             declared_kg=payload, tare_kg=tare, distance_km=km)
    f.movements.append(m)
    eq = R.sample([e for e in f.equipment if e["kind"] == lash_kind], k=min(4, sum(e["kind"] == lash_kind for e in f.equipment)))
    f.restraint.append(dict(movement_id=mid, method="tie-down", blocked=True, friction=mu, lashing=lash_kind,
                            pretension_kgf=300, angle_deg=R.choice([65, 70, 80]), rows=rows,
                            heaviest_row_kg=round(payload / rows), lashings_per_row=max(1, -(-round(payload / rows) // per_lash)),
                            equipment_ids=[e["id"] for e in eq], competent_person_id=d["id"],
                            plan_reviewed=True))
    measured = payload * R.uniform(0.98, 1.02) + tare
    if planned:
        status = "not_due" if depart > SNAPSHOT + timedelta(hours=2) else "ticketed"
    else:
        status = "ticketed"
    wb = dict(movement_id=mid, status=status, jsea=True)
    if status == "ticketed":
        wb.update(gross_kg=round(measured), steer_kg=round(min(5_900, 5_400 + payload * 0.01)),
                  ticket=f.nid("WB"), at=iso(depart - timedelta(minutes=20)))
    f.weighbridge.append(wb)
    return mid


def linehaul(f):
    pairs = [(f.drivers[32], f.drivers[33]), (f.drivers[34], f.drivers[35])]
    vs = [f.vehicles[22], f.vehicles[23]]
    for (a, b), v in zip(pairs, vs):
        day = HIST_START.date()
        k = 0
        while datetime.combine(day, datetime.min.time(), tzinfo=MEL) < PLAN_END - timedelta(hours=18):
            if day.weekday() in (0, 3):  # Mon/Thu northbound 18:00, back 18:00 next day
                start = datetime(day.year, day.month, day.day, 18, 0, tzinfo=MEL)
                planned = start >= SNAPSHOT
                movement(f, a, v, start + timedelta(minutes=45), "SYD", "C4", planned, co_driver=b["id"])
                two_up_day(f, a, b, start, planned)
                ret = start + timedelta(hours=24)
                movement(f, b, v, ret + timedelta(minutes=30), "SYD", "C5", planned, co_driver=a["id"])
                two_up_day(f, b, a, ret, planned)
                k += 1
            day += timedelta(days=1)


def two_up_day(f, first, second, start, planned):
    """~11 h run: each driver works ~5 h then rests in the berth while the other drives."""
    t = start
    seq = [(first, "work", 270, second, "rest_berth", 270), (second, "work", 270, first, "rest_berth", 270),
           (first, "work", 60, second, "rest_berth", 60)]
    f.ewd.append(dict(id=f.nid("EWD"), driver_id=second["id"], start=iso(t - timedelta(minutes=45)), end=iso(t),
                      activity="work", stationary=True, detail="loading", planned=planned, provider="DemoEWD",
                      base_tz="Australia/Melbourne"))
    f.ewd.append(dict(id=f.nid("EWD"), driver_id=first["id"], start=iso(t - timedelta(minutes=45)), end=iso(t),
                      activity="work", stationary=True, detail="pre-start", planned=planned, provider="DemoEWD",
                      base_tz="Australia/Melbourne"))
    for d1, a1, m, d2, a2, _ in seq:
        f.ewd.append(dict(id=f.nid("EWD"), driver_id=d1["id"], start=iso(t), end=iso(t + timedelta(minutes=m)),
                          activity="work", stationary=True, detail="driving", planned=planned, provider="DemoEWD",
                          base_tz="Australia/Melbourne"))
        f.ewd.append(dict(id=f.nid("EWD"), driver_id=d2["id"], start=iso(t), end=iso(t + timedelta(minutes=m)),
                          activity="rest", stationary=False, sleeper_moving=True, detail="sleeper berth (moving)",
                          planned=planned, provider="DemoEWD", base_tz="Australia/Melbourne"))
        t += timedelta(minutes=m)
    for d in (first, second):
        f.ewd.append(dict(id=f.nid("EWD"), driver_id=d["id"], start=iso(t), end=iso(t + timedelta(minutes=45)),
                          activity="work", stationary=True, detail="unloading", planned=planned, provider="DemoEWD",
                          base_tz="Australia/Melbourne"))


def write(f, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    tables = dict(drivers=f.drivers, vehicles=f.vehicles, trailers=f.trailers, equipment=f.equipment,
                  movements=f.movements, ewd=f.ewd, trips=f.trips, speed_events=f.speed,
                  weighbridge=f.weighbridge, restraint=f.restraint, defects=f.defects,
                  workshop_bookings=f.bookings, actions=f.actions, feed_status=f.feeds, labels=f.labels)
    meta = dict(operator="Wattlebark Haulage (fictional)", snapshot=iso(SNAPSHOT), history_start=iso(HIST_START),
                plan_end=iso(PLAN_END), seed=SEED, note="All people, companies and records are fictional.")
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    for k, v in tables.items():
        (out / f"{k}.json").write_text(json.dumps(v, indent=1, ensure_ascii=False, default=str))
    return {k: len(v) for k, v in tables.items()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    a = ap.parse_args()
    from storylines import inject  # noqa: E402
    fl = build()
    import sys
    inject(fl, R, sys.modules[__name__])
    print(write(fl, Path(a.out)))
