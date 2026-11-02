"""Labelled storylines and decoys injected on top of the clean baseline.

Each label records what a careful controller should conclude:
expected traffic light, decision, root cause and the accountable CoR party
(several parties are accepted where the chain genuinely shares the fix).
"""
from __future__ import annotations

from datetime import datetime, timedelta, date

DECISIONS = ["HOLD", "RESCHEDULE", "RELEASE_WITH_CONDITIONS", "MONITOR", "INVESTIGATE", "RELEASE"]
ROOT_CAUSES = ["ROSTER_PLANNING", "CUSTOMER_WINDOW", "CONSIGNOR_DECLARATION", "LOADING_PRACTICE",
               "TRAINING_LAPSE", "EQUIPMENT_CONTROL", "MAINTENANCE_PLANNING", "DEFECT_CONTROL",
               "DRIVER_BEHAVIOUR", "DATA_QUALITY", "RECORD_KEEPING", "NONE"]
PARTIES = ["scheduler", "loader", "consignor", "operator", "driver", "executive", "data_owner"]


def inject(f, R, g):
    S = Story(f, R, g)
    S.fatigue_short_rest()
    S.fatigue_seven_day()
    S.fatigue_two_up()
    S.fatigue_headroom()
    S.mass()
    S.restraint()
    S.speed()
    S.maintenance()
    S.integrity()
    S.decoys()
    S.background_speed()


def at(d, hm):
    h, m = map(int, hm.split(":"))
    return datetime(d.year, d.month, d.day, h, m, tzinfo=MON.tzinfo)


MON = None  # set in Story


class Story:
    def __init__(self, f, R, g):
        global MON
        self.f, self.R, self.g = f, R, g
        MON = g.SNAPSHOT
        self.used_d, self.used_v, self.used_m = set(), set(), set()
        self.drv = {d["id"]: d for d in f.drivers}
        self.veh = {v["id"]: v for v in f.vehicles}

    # ---- helpers -----------------------------------------------------------
    def label(self, story, area, entity, movement_ids, rag, decision, cause, parties, rules, summary, kind="storyline"):
        assert decision in DECISIONS and cause in ROOT_CAUSES and all(p in PARTIES for p in parties)
        self.f.labels.append(dict(story=story, kind=kind, area=area, entity=entity, movement_ids=movement_ids,
                                  expected_rag=rag, decision=decision, root_cause=cause, parties=parties,
                                  expected_rules=rules, summary=summary))

    def planned_of(self, did, day=None):
        out = [m for m in self.f.movements if m["planned"] and did in (m["driver_id"], m.get("co_driver_id"))]
        if day:
            out = [m for m in out if m["depart"][:10] == day.isoformat()]
        return sorted(out, key=lambda m: m["depart"])

    def pick_driver(self, pred):
        for d in self.f.drivers:
            if d["id"] not in self.used_d and d["scheme"] == "solo" and pred(d) and self.planned_of(d["id"]):
                self.used_d.add(d["id"])
                return d
        raise RuntimeError("no driver fits")

    def pick_movement(self, pred):
        for m in self.f.movements:
            if (m["planned"] and m["id"] not in self.used_m and m["driver_id"] not in self.used_d
                    and m["vehicle_id"] not in self.used_v and pred(m)):
                self.used_m.add(m["id"])
                self.used_d.add(m["driver_id"])
                self.used_v.add(m["vehicle_id"])
                return m
        raise RuntimeError("no movement fits")

    def clear_driver(self, did, start, end):
        """Remove a driver's EWD events and movements that start in [start, end)."""
        f = self.f
        f.ewd = [e for e in f.ewd if not (e["driver_id"] == did and start <= datetime.fromisoformat(e["start"]) < end)]
        gone = {m["id"] for m in f.movements if m["driver_id"] == did and start <= datetime.fromisoformat(m["depart"]) < end}
        f.movements = [m for m in f.movements if m["id"] not in gone]
        f.restraint = [r for r in f.restraint if r["movement_id"] not in gone]
        f.weighbridge = [w for w in f.weighbridge if w["movement_id"] not in gone]
        f.trips = [t for t in f.trips if not (t["login_driver_id"] == did and start <= datetime.fromisoformat(t["start"]) < end)]

    def vehicle_of(self, did):
        ms = self.planned_of(did)
        return self.veh[ms[0]["vehicle_id"]] if ms else None

    def ewd(self, did, a, b, act, detail, planned, **kw):
        self.f.ewd.append(dict(id=self.f.nid("EWD"), driver_id=did, start=a.isoformat(timespec="minutes"),
                               end=b.isoformat(timespec="minutes"), activity=act, stationary=kw.get("stationary", True),
                               sleeper_moving=kw.get("sleeper_moving", False), detail=detail, planned=planned,
                               provider="DemoEWD", base_tz="Australia/Melbourne"))

    # ---- fatigue -----------------------------------------------------------
    def fatigue_short_rest(self):
        d = self.pick_driver(lambda d: d["usual_start"] == "06:00" and d["lane"] in ("BAL", "GEE", "BEN"))
        v = self.vehicle_of(d["id"])
        sun, mon = date(2026, 11, 1), date(2026, 11, 2)
        self.clear_driver(d["id"], at(date(2026, 10, 31), "00:00"), at(date(2026, 11, 3), "00:00"))
        # Sunday call-out for Kestrel Machinery: the long day from the original demo
        day = [("07:00", "12:00", "work", "pre-start, load and drive to Dandenong South"), ("12:00", "12:15", "rest", "break"),
               ("12:15", "14:30", "work", "unload and return"), ("14:30", "18:30", "rest", "standby at depot"),
               ("18:30", "20:30", "work", "second call-out: drive to Tullamarine"), ("20:30", "20:45", "rest", "break"),
               ("20:45", "23:30", "work", "unload, return and depot duties")]
        for a, b, act, det in day:
            self.ewd(d["id"], at(sun, a), at(sun, b), act, det, False)
        hist_mv = self.g.movement(self.f, d, v, at(sun, "07:45"), "MET", "C6", False)
        ids = self.g.shift(self.f, d, v, at(mon, "06:00"), d["lane"], planned=True)
        self.label("S01", "Fatigue", d["id"], ids[:1], "RED", "RESCHEDULE", "ROSTER_PLANNING", ["scheduler"],
                   ["FAT-24H-REST", "FAT-24H-WORK"],
                   f"{d['name']} finished a Sunday call-out at 23:30 and is rostered 06:00 Monday. The 24 h period that "
                   "began 07:00 Sunday already holds 12 h work, so the earliest compliant start is 07:00.")

    def fatigue_seven_day(self):
        d = self.pick_driver(lambda d: d["lane"] == "BEN" and d["usual_start"] in ("06:00", "07:00"))
        v = self.vehicle_of(d["id"])
        self.clear_driver(d["id"], at(date(2026, 10, 26), "00:00"), at(date(2026, 11, 5), "00:00"))
        ids = []
        for k in range(8):  # Tue 27 Oct .. Tue 3 Nov, every day, ~11 h work, covering an absent driver
            day = date(2026, 10, 27) + timedelta(days=k)
            planned = day >= date(2026, 11, 2)
            ids += self.g.shift(self.f, d, v, at(day, "07:00"), "BEN", planned=planned, extra_work=325)
        mon = [m for m in self.planned_of(d["id"], date(2026, 11, 2))]
        self.label("S02", "Fatigue", d["id"], [mon[0]["id"]], "RED", "HOLD", "ROSTER_PLANNING", ["scheduler", "executive"],
                   ["FAT-7D-WORK", "FAT-7D-REST"],
                   f"{d['name']} has covered an absent driver every day since Tue 27 Oct without a 24 h rest. "
                   "Monday's shift takes the 7-day total past 72 h.")

    def fatigue_two_up(self):
        a, b = self.drv["D33"], self.drv["D34"]
        self.used_d |= {"D33", "D34"}
        v = self.veh["PM23"]
        self.used_v.add("PM23")
        s, e = at(date(2026, 11, 2), "00:00"), at(date(2026, 11, 5), "00:00")
        for did in ("D33", "D34"):
            self.clear_driver(did, s, e)
        north = at(date(2026, 11, 2), "18:00")
        m1 = self.g.movement(self.f, a, v, north + timedelta(minutes=45), "SYD", "C4", True, co_driver="D34")
        self.g.two_up_day(self.f, a, b, north, True)
        ret = at(date(2026, 11, 3), "08:00")  # pulled forward from 18:00 for Corella's cross-dock
        m2 = self.g.movement(self.f, b, v, ret + timedelta(minutes=45), "SYD", "C4", True, co_driver="D33")
        next(m for m in self.f.movements if m["id"] == m2)["plan_change"] = dict(
            original_depart="2026-11-03T18:45+11:00", changed="2026-11-02T16:10+11:00", changed_by="Customer service",
            reason="Brought forward at Corella Home Retail's request to meet a 22:00 Moorebank cross-dock slot")
        self.g.two_up_day(self.f, b, a, ret, True)
        self.label("S03", "Fatigue", "D33/D34", [m2], "RED", "RESCHEDULE", "CUSTOMER_WINDOW", ["scheduler", "consignor"],
                   ["FAT-24H-REST", "FAT-24H-WORK"],
                   "The two-up pair's Sydney return was pulled forward from 18:00 to 08:00 to meet Corella Home Retail's "
                   "cross-dock, leaving 2.5 h stationary rest after unloading.")

    def fatigue_headroom(self):
        d = self.pick_driver(lambda d: d["lane"] == "ALB")
        v = self.vehicle_of(d["id"])
        tue = date(2026, 11, 3)
        self.clear_driver(d["id"], at(tue, "00:00"), at(tue + timedelta(days=1), "00:00"))
        h, m = map(int, d["usual_start"].split(":"))
        ids = self.g.shift(self.f, d, v, at(tue, f"{h:02d}:{m:02d}"), "ALB", planned=True, extra_work=170)
        self.label("S04", "Fatigue", d["id"], ids[:1], "AMBER", "MONITOR", "ROSTER_PLANNING", ["scheduler"],
                   ["FAT-HEADROOM"],
                   f"{d['name']}'s Tuesday Wodonga run has an added pickup: about 11.4 h work, leaving under an hour "
                   "on the 12 h limit if the dock runs late.")

    # ---- mass --------------------------------------------------------------
    def mass(self):
        f = self.f
        wb = {w["movement_id"]: w for w in f.weighbridge}
        # C1 declares light across the history (pattern evidence)
        for m in f.movements:
            if m["customer_id"] == "C1" and not m["planned"]:
                w = wb[m["id"]]
                w["gross_kg"] = round(m["declared_kg"] * self.R.uniform(1.06, 1.09) + m["tare_kg"])
        early = lambda m: m["depart"] < "2026-11-02T07:31"
        m = self.pick_movement(lambda m: early(m) and self.veh[m["vehicle_id"]]["type"] == "prime mover"
                               and m["lane"] != "SYD")
        m["customer_id"], m["load_type"], m["declared_kg"] = "C1", "steel", 25_200
        v = self.veh[m["vehicle_id"]]
        wb[m["id"]].update(status="ticketed", gross_kg=round(v["gcm_limit_t"] * 1000 + 1_250), ticket=f.nid("WB"),
                           steer_kg=5_850, at=m["depart"])
        self._fix_restraint(m, "chain", 0.2)
        self.label("S05", "Mass & dimension", m["id"], [m["id"]], "RED", "HOLD", "CONSIGNOR_DECLARATION",
                   ["consignor", "loader"], ["MASS-OVER-GML", "MASS-DECLARED-LOW"],
                   "Brackenridge Steel's coil load weighs 1.25 t over the combination limit; its declared weight is "
                   "about 8% light, as on every Brackenridge load this month.")
        m = self.pick_movement(lambda m: early(m) and m["lane"] != "SYD")
        wb[m["id"]].update(status="pending")
        wb[m["id"]].pop("gross_kg", None)
        self.label("S06", "Mass & dimension", m["id"], [m["id"]], "AMBER", "RELEASE_WITH_CONDITIONS", "RECORD_KEEPING",
                   ["loader"], ["MASS-PENDING"], "Departs within two hours and the weighbridge ticket is still pending.")
        m = self.pick_movement(lambda m: m["depart"][:10] == "2026-11-02" and m["lane"] != "SYD")
        m["customer_id"], m["load_type"] = "C6", "machinery"
        wb[m["id"]].update(status="missing", jsea=False)
        self._fix_restraint(m, "chain", 0.3)
        self.label("S07", "Mass & dimension", m["id"], [m["id"]], "RED", "HOLD", "RECORD_KEEPING", ["loader", "operator"],
                   ["MASS-NO-EVIDENCE"], "Kestrel Machinery excavator load with no weighbridge ticket and no pre-dispatch JSEA.")

    def _fix_restraint(self, m, kind, mu):
        r = next(r for r in self.f.restraint if r["movement_id"] == m["id"])
        per = {("chain", 0.2): 3300, ("chain", 0.3): 3300, ("webbing", 0.4): 2000}[(kind, mu)]
        r.update(lashing=kind, friction=mu, rows=max(1, m["declared_kg"] // 6000))
        r["heaviest_row_kg"] = round(m["declared_kg"] / r["rows"])
        r["lashings_per_row"] = -(-r["heaviest_row_kg"] // per)
        r["equipment_ids"] = [e["id"] for e in self.f.equipment if e["kind"] == kind and e["result"] == "pass"][:4]
        return r

    # ---- restraint ---------------------------------------------------------
    def restraint(self):
        d = self.pick_driver(lambda d: True)
        d["restraint_competency_expiry"] = "2026-10-28"
        ids = [m["id"] for m in self.planned_of(d["id"])]
        self.label("S08", "Load restraint", d["id"], ids, "RED", "HOLD", "TRAINING_LAPSE", ["operator"],
                   ["LR-COMPETENCY-EXPIRED"], f"{d['name']}'s load restraint competency lapsed on 28 Oct and no refresher is booked.")
        d = self.pick_driver(lambda d: True)
        d["restraint_competency_expiry"] = "2026-11-12"
        ids = [m["id"] for m in self.planned_of(d["id"])]
        self.label("S09", "Load restraint", d["id"], ids, "AMBER", "MONITOR", "TRAINING_LAPSE", ["operator"],
                   ["LR-COMPETENCY-SOON"], f"{d['name']}'s restraint competency expires 12 Nov; book the refresher.")
        m = self.pick_movement(lambda m: m["lane"] != "SYD" and m["depart"][:10] == "2026-11-02")
        r = next(r for r in self.f.restraint if r["movement_id"] == m["id"])
        eq = self.f.equipment[r["equipment_ids"] and int(r["equipment_ids"][0][2:]) - 1]
        eq.update(result="fail: cut webbing near hook", last_inspection="2026-10-30", in_service=True)
        # nobody else should carry that strap
        for r2 in self.f.restraint:
            if r2 is not r and eq["id"] in r2["equipment_ids"]:
                r2["equipment_ids"] = [x for x in r2["equipment_ids"] if x != eq["id"]]
        self.label("S10", "Load restraint", m["id"], [m["id"]], "RED", "HOLD", "EQUIPMENT_CONTROL", ["operator", "loader"],
                   ["LR-EQUIPMENT-FAILED"], f"{eq['id']} failed inspection on 30 Oct (cut webbing) but was not tagged out "
                   "and is assigned to this load.")
        m = self.pick_movement(lambda m: m["lane"] != "SYD" and self.veh[m["vehicle_id"]]["type"] == "prime mover"
                               and m["depart"][:10] == "2026-11-03")
        m["customer_id"], m["load_type"], m["declared_kg"] = "C1", "steel", 20_400
        r = self._fix_restraint(m, "chain", 0.2)
        r["rows"], r["heaviest_row_kg"], r["lashings_per_row"] = 3, 6_800, 2
        self.label("S11", "Load restraint", m["id"], [m["id"]], "RED", "HOLD", "LOADING_PRACTICE", ["loader"],
                   ["LR-UNDER-TABLE"], "Steel coil rows of 6.8 t planned with two chains each; the tie-down table "
                   "needs three at this friction level.")

    # ---- speed -------------------------------------------------------------
    def sp(self, d, v, when, loc, limit, peak, dur, transition=False, conf="high", source="posted, verified"):
        e = dict(id=self.f.nid("SPD"), driver_id=d["id"], vehicle_id=v, at=when.isoformat(timespec="minutes"),
                 location=loc, limit_kph=limit, peak_kph=peak, duration_s=dur, zone_transition=transition,
                 limit_confidence=conf, limit_source=source)
        self.f.speed.append(e)
        return e

    def speed(self):
        d = self.pick_driver(lambda d: d["lane"] == "MET")
        v = self.vehicle_of(d["id"])["id"]
        for k, (dd, hm, peak, dur) in enumerate([(27, "07:12", 71, 48), (28, "15:40", 74, 62), (29, "08:05", 76, 35),
                                                 (30, "14:22", 72, 71)]):
            self.sp(d, v, at(date(2026, 10, dd), hm), "Western Ring Rd, Sunshine West (60 roadworks)" if k % 2 else
                    "Ballarat Rd, Sunshine (60)", 60, peak, dur)
        ids = [m["id"] for m in self.planned_of(d["id"])]
        self.label("S12", "Speed", d["id"], ids[:1], "RED", "HOLD", "DRIVER_BEHAVIOUR", ["driver", "operator"],
                   ["SPD-OVER-10"], f"{d['name']}: four events 11-16 km/h over in 60 zones in four days, none followed up.")
        # Geelong lane: several drivers, small overs entering the 60 zone at Corio before a 07:00 dock
        gee = [x for x in self.f.drivers if x["lane"] == "GEE" and x["id"] not in self.used_d and self.planned_of(x["id"])]
        for x in gee:
            self.used_d.add(x["id"])
            vx = self.vehicle_of(x["id"])["id"]
            hist = sorted([m for m in self.f.movements if m["driver_id"] == x["id"] and not m["planned"] and m["lane"] == "GEE"],
                          key=lambda m: m["depart"])
            weeks = {}
            for m in hist:
                weeks.setdefault(datetime.fromisoformat(m["depart"]).isocalendar().week, m)
            for m in list(weeks.values())[:4]:
                dep = datetime.fromisoformat(m["depart"])
                m["customer_id"] = "C3"
                m["arrive_window"] = (dep + timedelta(minutes=65)).isoformat(timespec="minutes")  # Greyfield dock slot
                self.sp(x, vx, dep + timedelta(minutes=50 + self.R.randint(-3, 3)), "Princes Hwy, Corio (80 to 60)", 60,
                        60 + self.R.randint(5, 9), self.R.randint(15, 40), transition=True)
            for m in self.planned_of(x["id"])[:1]:
                m["customer_id"] = "C3"
                m["arrive_window"] = (datetime.fromisoformat(m["depart"]) + timedelta(minutes=65)).isoformat(timespec="minutes")
            self.label("S13", "Speed", x["id"], [m["id"] for m in self.planned_of(x["id"])][:1], "AMBER", "MONITOR",
                       "CUSTOMER_WINDOW", ["scheduler", "consignor"], ["SPD-WATCH"],
                       f"{x['name']} enters the Corio 60 zone 5-9 km/h over most weeks, about 15 minutes before "
                       "the Greyfield dock slot.")
        d = self.pick_driver(lambda d: d["lane"] == "BAL")
        v = self.vehicle_of(d["id"])["id"]
        self.sp(d, v, at(date(2026, 10, 30), "09:31"), "Western Fwy, Bacchus Marsh", 60, 94, 140, conf="low",
                source="map layer (roadworks zone ended 12 Oct)")
        self.label("S14", "Speed", d["id"], [m["id"] for m in self.planned_of(d["id"])][:1], "AMBER", "MONITOR",
                   "DATA_QUALITY", ["data_owner"], ["SPD-LIMIT-UNVERIFIED"],
                   "A 94 km/h 'event' against a 60 limit from an expired roadworks zone in the map layer; posted limit is 100.")

    # ---- maintenance -------------------------------------------------------
    def maintenance(self):
        f = self.f
        m = self.pick_movement(lambda m: m["lane"] in ("ALB", "BEN") and m["depart"][:10] == "2026-11-02")
        v = self.veh[m["vehicle_id"]]
        v["last_service_km"] = v["odometer_km"] + 200 - v["service_interval_km"]
        rt = m["distance_km"] * 2
        ids15 = [x["id"] for x in f.movements if x["planned"] and x["vehicle_id"] == v["id"]]
        self.used_m |= set(ids15)
        self.label("S15", "Maintenance", v["id"], ids15, "RED", "RESCHEDULE", "MAINTENANCE_PLANNING", ["operator"],
                   ["MNT-SERVICE-OVERDUE"], f"{v['id']} is 200 km from its 25,000 km service and is planned on a "
                   f"{rt} km round trip to {m['destination']}.")
        m = self.pick_movement(lambda m: m["lane"] in ("GEE", "MET", "BAL") and m["depart"][:10] == "2026-11-02")
        v = self.veh[m["vehicle_id"]]
        v["service_due_date"] = "2026-11-04"
        ids = [x["id"] for x in f.movements if x["planned"] and x["vehicle_id"] == v["id"]]
        self.used_m |= set(ids)
        self.label("S16", "Maintenance", v["id"], ids, "AMBER", "MONITOR", "MAINTENANCE_PLANNING", ["operator", "scheduler"],
                   ["MNT-SERVICE-SOON"], f"{v['id']} is due for its scheduled service on Wed 4 Nov; no workshop slot is booked.")
        m = self.pick_movement(lambda m: m["lane"] != "SYD" and m["depart"][:10] == "2026-11-02")
        f.defects.append(dict(id=f.nid("DEF"), asset_id=m["trailer_id"], severity="major",
                              description="air leak at trailer brake chamber (axle 2, nearside)", reported="2026-10-31T16:20+11:00",
                              reported_by="pre-trip inspection", status="open"))
        ids = [x["id"] for x in f.movements if x["planned"] and x["trailer_id"] == m["trailer_id"]]
        self.used_m |= set(ids)
        self.label("S17", "Maintenance", m["trailer_id"], ids, "RED", "HOLD", "DEFECT_CONTROL", ["operator"],
                   ["MNT-OPEN-DEFECT"], f"Trailer {m['trailer_id']} has an open major brake defect from Saturday's pre-trip "
                   "check and is coupled to Monday's run.")
        m = self.pick_movement(lambda m: m["lane"] in ("BAL", "BEN") and m["depart"][:10] == "2026-11-03")
        b = dict(id=f.nid("WS"), vehicle_id=m["vehicle_id"], start="2026-11-03T09:00+11:00", end="2026-11-03T13:00+11:00",
                 job="brake reline and annual inspection prep")
        f.bookings.append(b)
        self.label("S18", "Maintenance", m["vehicle_id"], [m["id"]], "AMBER", "RESCHEDULE", "MAINTENANCE_PLANNING",
                   ["scheduler", "operator"], ["MNT-BOOKING-CLASH"],
                   f"{m['vehicle_id']} is booked into the workshop Tue 09:00-13:00 but is dispatched on that morning's run.")

    # ---- integrity ---------------------------------------------------------
    def integrity(self):
        f = self.f
        d = self.pick_driver(lambda d: d["lane"] in ("MET", "GEE", "BAL"))
        v = self.vehicle_of(d["id"])
        sat = date(2026, 10, 31)
        self.clear_driver(d["id"], at(sat, "00:00"), at(sat, "23:59"))
        f.trips.append(dict(id=f.nid("TRP"), vehicle_id=v["id"], start=at(sat, "14:10").isoformat(timespec="minutes"),
                            end=at(sat, "16:40").isoformat(timespec="minutes"), login_driver_id=d["id"], km=96,
                            assigned_driver_id=d["id"]))
        self.used_v.add(v["id"])
        self.label("S19", "Integrity", v["id"], [], "RED", "INVESTIGATE", "RECORD_KEEPING", ["operator", "driver"],
                   ["INT-UNRECORDED-DRIVER"],
                   f"{v['id']} drove 96 km on Saturday afternoon under {d['name']}'s login while {d['name']}'s diary shows rest. "
                   "Someone drove without a work diary record, or the login was shared.")
        m = self.pick_movement(lambda m: m["lane"] != "SYD")
        v = self.veh[m["vehicle_id"]]
        f.feeds = [dict(vehicle_id=v["id"], unit=v["telematics_unit"], last_received="2026-10-31T11:04+11:00")]
        ids = [x["id"] for x in f.movements if x["planned"] and x["vehicle_id"] == v["id"]]
        self.used_m |= set(ids)
        self.label("S20", "Integrity", v["id"], ids, "AMBER", "MONITOR", "DATA_QUALITY", ["data_owner", "operator"],
                   ["INT-FEED-STALE"], f"No telematics from {v['id']} since Saturday 11:04; speed and trip checks are blind.")

    # ---- decoys (should stay green) ----------------------------------------
    def decoys(self):
        f = self.f
        d = self.pick_driver(lambda d: d["lane"] == "ALB")
        v = self.vehicle_of(d["id"])
        wed = date(2026, 11, 4)
        self.clear_driver(d["id"], at(wed, "00:00"), at(wed + timedelta(days=1), "00:00"))
        h = d["usual_start"]
        ids = self.g.shift(f, d, v, at(wed, h), "ALB", planned=True, extra_work=90)
        self.label("D01", "Fatigue", d["id"], ids[:1], "GREEN", "RELEASE", "NONE", [], [],
                   "A long but compliant 10 h day: more than an hour's headroom.", kind="decoy")
        m = self.pick_movement(lambda m: self.veh[m["vehicle_id"]]["type"] == "prime mover" and m["lane"] != "SYD")
        v = self.veh[m["vehicle_id"]]
        w = next(w for w in f.weighbridge if w["movement_id"] == m["id"])
        w.update(status="ticketed", gross_kg=round(v["gcm_limit_t"] * 1000 - 400), ticket=f.nid("WB"), steer_kg=5_700)
        m["declared_kg"] = w["gross_kg"] - m["tare_kg"] - 200
        self._fix_restraint(m, "webbing", 0.4)
        self.label("D02", "Mass & dimension", m["id"], [m["id"]], "GREEN", "RELEASE", "NONE", [], [],
                   "Heavy but legal: 0.4 t under the limit with a ticket that matches the declaration.", kind="decoy")
        d = self.pick_driver(lambda d: True)
        v = self.vehicle_of(d["id"])["id"]
        e = self.sp(d, v, at(date(2026, 10, 29), "11:02"), "Western Fwy, Rockbank", 100, 104, 22)
        f.actions.append(dict(id=f.nid("ACT"), type="speed_followup", ref=e["id"], by="Fleet coordinator",
                              at="2026-10-29T15:30+11:00", note="Discussed with driver; overtaking on decline."))
        e = self.sp(d, v, at(date(2026, 10, 30), "13:48"), "Calder Fwy, Gisborne", 100, 112, 31)
        f.actions.append(dict(id=f.nid("ACT"), type="speed_followup", ref=e["id"], by="Transport manager",
                              at="2026-10-30T17:05+11:00", note="Toolbox talk held; delivery window widened."))
        self.label("D03", "Speed", d["id"], [m["id"] for m in self.planned_of(d["id"])][:1], "GREEN", "RELEASE", "NONE", [], [],
                   "Two events including one 12 km/h over, both followed up and closed.", kind="decoy")
        d = self.pick_driver(lambda d: True)
        d["restraint_competency_expiry"] = "2026-11-24"
        self.label("D04", "Load restraint", d["id"], [m["id"] for m in self.planned_of(d["id"])][:1], "GREEN", "RELEASE",
                   "NONE", [], [], "Competency expires in three weeks: outside the 14-day watch window.", kind="decoy")
        m = self.pick_movement(lambda m: m["depart"][:10] == "2026-11-02" and m["lane"] != "SYD")
        f.defects.append(dict(id=f.nid("DEF"), asset_id=m["trailer_id"], severity="minor", description="marker lamp out",
                              reported="2026-10-30T07:10+11:00", reported_by="pre-trip inspection", status="closed",
                              closed="2026-10-30T12:40+11:00"))
        self.label("D05", "Maintenance", m["trailer_id"], [m["id"]], "GREEN", "RELEASE", "NONE", [], [],
                   "A defect was raised last week and closed the same day.", kind="decoy")

    def background_speed(self):
        """Older, small, followed-up events across the fleet: realistic noise for the pattern agent."""
        f = self.f
        for _ in range(26):
            d = self.R.choice([x for x in f.drivers if x["scheme"] == "solo"])
            v = self.vehicle_of(d["id"])
            if not v:
                continue
            day = date(2026, 10, 5) + timedelta(days=self.R.randint(0, 17))
            lane = self.g.LANES[d["lane"]]
            e = self.sp(d, v["id"], at(day, f"{self.R.randint(6, 16):02d}:{self.R.randint(0, 59):02d}"), lane[3], 100,
                        100 + self.R.randint(3, 8), self.R.randint(10, 40))
            f.actions.append(dict(id=f.nid("ACT"), type="speed_followup", ref=e["id"], by="Fleet coordinator",
                                  at=(at(day, "17:00")).isoformat(timespec="minutes"), note="Reviewed; no further action."))
