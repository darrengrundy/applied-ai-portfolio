import sys, pathlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from engine.fatigue import Event, check, earliest_start  # noqa: E402

MEL = ZoneInfo("Australia/Melbourne")


def t(day, hm):
    h, m = map(int, hm.split(":"))
    month = 10 if day > 15 else 11  # 31 -> 31 Oct
    return datetime(2026, month, day, h, m, tzinfo=MEL)


def ev(d1, a, d2, b, act):
    return Event(t(d1, a), t(d2, b), act)


def bob_history():
    # 31 Oct 21:00 -> 1 Nov 07:00 long rest, then the original demo's day
    return [
        ev(31, "21:00", 1, "07:00", "rest"),
        ev(1, "07:00", 1, "12:00", "work"),
        ev(1, "12:00", 1, "12:15", "rest"),
        ev(1, "12:15", 1, "14:30", "work"),
        ev(1, "14:30", 1, "18:30", "rest"),
        ev(1, "18:30", 1, "20:30", "work"),
        ev(1, "20:30", 1, "20:45", "rest"),
        ev(1, "20:45", 1, "23:30", "work"),
        ev(1, "23:30", 3, "00:00", "rest"),
    ]


def planned(start, hours=8):
    return [Event(start, start + timedelta(hours=4), "work"),
            Event(start + timedelta(hours=4), start + timedelta(hours=4, minutes=30), "rest"),
            Event(start + timedelta(hours=4, minutes=30), start + timedelta(hours=hours, minutes=30), "work")]


T0, T1 = t(31, "21:00"), t(3, "12:00")


def rules(res):
    return {b.rule_id for b in res.breaches}


def test_history_alone_is_clean():
    assert check(bob_history(), T0, T1).ok


def test_0600_start_breaks_24h_rest():
    r = check(bob_history(), T0, T1, planned=planned(t(2, "06:00")), only_planned=True)
    assert "FAT-24H-REST" in rules(r)


def test_0630_start_still_breaks_24h_work():
    # The earlier demo cleared 06:30. Work 06:30-07:00 falls inside the 24 h period that
    # began 07:00 on 1 Nov, which already holds 12 h of work.
    r = check(bob_history(), T0, T1, planned=planned(t(2, "06:30")), only_planned=True)
    assert "FAT-24H-WORK" in rules(r)
    assert "FAT-24H-REST" not in rules(r)


def test_0700_start_is_clean():
    r = check(bob_history(), T0, T1, planned=planned(t(2, "07:00")), only_planned=True)
    assert r.ok, [b.detail for b in r.breaches]


def test_earliest_start_is_0700():
    s = earliest_start(bob_history(), T0, 8 * 60, "solo", not_before=t(2, "06:00"), horizon_end=T1)
    assert s == t(2, "07:00")


def test_short_period_needs_15_continuous_minutes():
    h = [ev(1, "00:00", 1, "07:00", "rest"),
         ev(1, "07:00", 1, "10:00", "work"), ev(1, "10:00", 1, "10:10", "rest"),
         ev(1, "10:10", 1, "12:30", "work"), ev(1, "12:30", 2, "07:00", "rest")]
    r = check(h, t(1, "00:00"), t(2, "07:00"))
    assert "FAT-5.5H" in rules(r)  # 10-min break does not count; 5 h 20 min work after 07:00


def test_short_period_boundary_ok():
    h = [ev(1, "00:00", 1, "07:00", "rest"),
         ev(1, "07:00", 1, "12:15", "work"), ev(1, "12:15", 1, "12:30", "rest"),
         ev(1, "12:30", 1, "14:30", "work"), ev(1, "14:30", 2, "07:00", "rest")]
    assert check(h, t(1, "00:00"), t(2, "07:00")).ok


def week(day0, n_days, shift_h, start="06:00"):
    out = []
    for d in range(n_days):
        s = datetime(2026, 10, day0, *map(int, start.split(":")), tzinfo=MEL) + timedelta(days=d)
        # 5 h, 30 min break, 5 h, 30 min break, remainder
        left, o = shift_h * 60, 0
        while left > 0:
            blk = min(300, left)
            out.append(Event(s + timedelta(minutes=o), s + timedelta(minutes=o + blk), "work"))
            o += blk
            left -= blk
            if left > 0:
                out.append(Event(s + timedelta(minutes=o), s + timedelta(minutes=o + 30), "rest"))
                o += 30
        out.append(Event(s + timedelta(minutes=o), s + timedelta(days=1), "rest"))
    return out


def test_seven_day_72h_limit():
    t0 = datetime(2026, 10, 10, 6, 0, tzinfo=MEL) - timedelta(hours=30)
    pre = [Event(t0, datetime(2026, 10, 10, 6, 0, tzinfo=MEL), "rest")]
    six = week(10, 6, 12)            # 72 h in six days -> at the limit
    assert not any(b.rule_id == "FAT-7D-WORK" for b in check(pre + six, t0, datetime(2026, 10, 17, 6, 0, tzinfo=MEL)).breaches)
    seven = week(10, 7, 11)          # 77 h, no 24 h rest
    r = check(pre + seven, t0, datetime(2026, 10, 18, 6, 0, tzinfo=MEL))
    assert {"FAT-7D-WORK", "FAT-7D-REST"} <= rules(r)


def test_missing_records_are_incomplete():
    h = [ev(1, "00:00", 1, "07:00", "rest"), ev(1, "07:00", 1, "10:00", "work")]
    r = check(h, t(1, "00:00"), t(1, "18:00"))
    assert r.incomplete


def test_day_worker_gets_night_rests_over_14_days():
    t0 = datetime(2026, 10, 4, 22, 0, tzinfo=MEL)
    pre = [Event(t0, datetime(2026, 10, 5, 6, 0, tzinfo=MEL), "rest")]
    h = pre + week(5, 14, 9)        # 06:00 starts, 9 h days: rest every night
    r = check(h, t0, datetime(2026, 10, 19, 6, 0, tzinfo=MEL))
    assert not any("NIGHTS" in b.rule_id for b in r.breaches), [b.detail for b in r.breaches]


def test_night_worker_misses_night_rests():
    t0 = datetime(2026, 10, 4, 12, 0, tzinfo=MEL)
    pre = [Event(t0, datetime(2026, 10, 4, 20, 0, tzinfo=MEL), "rest")]
    h = pre + week(4, 15, 9, start="20:00")   # works 20:00-05:30, sleeps by day
    r = check(h, t0, datetime(2026, 10, 19, 20, 0, tzinfo=MEL))
    assert any(b.rule_id == "FAT-14D-NIGHTS" for b in r.breaches)


def test_two_up_needs_10h_in_52h():
    t0 = datetime(2026, 10, 9, 20, 0, tzinfo=MEL)
    h = [Event(t0, datetime(2026, 10, 10, 6, 0, tzinfo=MEL), "rest")]
    s = datetime(2026, 10, 10, 6, 0, tzinfo=MEL)
    # 3 days: 6 h on, 6 h in berth while moving, 6 h on, 6 h stationary rest (5 h+ but <10 h)
    for d in range(3):
        b = s + timedelta(days=d)
        h += [Event(b, b + timedelta(hours=6), "work"),
              Event(b + timedelta(hours=6), b + timedelta(hours=12), "rest", stationary=False, sleeper_moving=True),
              Event(b + timedelta(hours=12), b + timedelta(hours=18), "work"),
              Event(b + timedelta(hours=18), b + timedelta(hours=24), "rest")]
    r = check(h, t0, s + timedelta(days=3), scheme="two_up")
    assert "FAT-52H-REST" in rules(r)
