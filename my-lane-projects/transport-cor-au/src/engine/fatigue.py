"""Standard-hours fatigue checks (solo and two-up) for EWD-style records.

Counting follows NHVR "Counting time" (ref/sources.md F4):
- EWD time is counted to the minute; a continuous rest under 15 minutes does not
  count toward any minimum-rest requirement.
- Periods under 24 h are counted forward from the end of any rest break.
- Periods of 24 h or more are counted forward from the end of the longest major
  rest break required for that period; if none has been taken, from the end of
  any rest break. Overlapping periods are all checked, which is the strict reading.
- All times are minutes in the driver's base time zone.

Interpretation recorded in docs: the 14-day "2 night rest breaks and 2 night rest
breaks on consecutive days" row is read as at least 4 night rest breaks, including
one pair on consecutive nights (as in NHVR's planners).

This is decision support for a demo, not a legal determination.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np

H = 60
DAY = 24 * H

WORK, REST, SLEEPER_MOVING = 1, 0, 2  # minute states; REST means stationary rest


@dataclass
class Event:
    start: datetime
    end: datetime
    activity: str  # "work" | "rest"
    stationary: bool = True
    sleeper_moving: bool = False  # two-up rest in an approved berth while moving
    record_id: str = ""


@dataclass
class Breach:
    rule_id: str
    window_start: datetime
    window_end: datetime
    detail: str
    work_minutes: int = 0
    involves_planned: bool = False


@dataclass
class Result:
    scheme: str
    breaches: list[Breach] = field(default_factory=list)
    incomplete: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.breaches


# --- rule tables (minutes) -------------------------------------------------
SHORT_PERIODS = [  # (rule_id, period, max_work, min_rest_total, min_block)
    ("FAT-5.5H", 330, 315, 15, 15),
    ("FAT-8H", 480, 450, 30, 15),
    ("FAT-11H", 660, 600, 60, 15),
]
SOLO = {
    "24h": dict(period=DAY, max_work=12 * H, major=7 * H),
    "7d": dict(period=7 * DAY, max_work=72 * H, major=24 * H),
    "14d": dict(period=14 * DAY, max_work=144 * H, nights=4),
}
TWO_UP = {
    "24h": dict(period=DAY, max_work=12 * H, major=5 * H),
    "52h": dict(period=52 * H, major=10 * H),
    "7d": dict(period=7 * DAY, max_work=60 * H, major=24 * H, blocks7=24 * H),
    "14d": dict(period=14 * DAY, max_work=120 * H, nights=4),
}


class Timeline:
    """Minute-resolution state array from t0 to t_end."""

    def __init__(self, events: list[Event], t0: datetime, t_end: datetime, planned: list[Event] = ()):
        self.t0, self.t_end = t0, t_end
        n = int((t_end - t0).total_seconds() // 60)
        self.n = n
        self.state = np.full(n, -1, dtype=np.int8)  # -1 = unknown
        self.planned = np.zeros(n, dtype=bool)
        for ev in sorted(events, key=lambda e: e.start):
            self._fill(ev, False)
        for ev in planned:
            self._fill(ev, True)

    def idx(self, t: datetime) -> int:
        return int((t - self.t0).total_seconds() // 60)

    def time(self, i: int) -> datetime:
        return self.t0 + timedelta(minutes=int(i))

    def _fill(self, ev: Event, planned: bool):
        a, b = max(0, self.idx(ev.start)), min(self.n, self.idx(ev.end))
        if b <= a:
            return
        if ev.activity == "work":
            v = WORK
        elif ev.sleeper_moving or not ev.stationary:
            v = SLEEPER_MOVING
        else:
            v = REST
        self.state[a:b] = v
        if planned:
            self.planned[a:b] = True

    # rest runs: list of (start_idx, end_idx, kind) where kind is REST or SLEEPER_MOVING
    def rest_runs(self, include_moving=False):
        ok = (self.state == REST) | ((self.state == SLEEPER_MOVING) if include_moving else False)
        runs, i, n = [], 0, self.n
        d = np.diff(np.concatenate([[0], ok.astype(np.int8), [0]]))
        starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
        return list(zip(starts.tolist(), ends.tolist()))

    def any_rest_ends(self):
        not_work = self.state != WORK
        d = np.diff(np.concatenate([[0], not_work.astype(np.int8), [0]]))
        return np.where(d == -1)[0].tolist()  # index where a rest (any length) ends


def _work_in(tl: Timeline, a: int, b: int) -> int:
    return int((tl.state[a:min(b, tl.n)] == WORK).sum())


def _planned_in(tl: Timeline, a: int, b: int) -> bool:
    return bool(tl.planned[a:min(b, tl.n)].any())


def _blocks_within(runs, a, b, min_block):
    """Continuous rest blocks clipped to [a,b) that are at least min_block long."""
    out = []
    for s, e in runs:
        s2, e2 = max(s, a), min(e, b)
        if e2 - s2 >= min_block:
            out.append((s2, e2))
    return out


def _night_rests(tl: Timeline, runs, a, b):
    """Night rest breaks inside [a,b): 7 h continuous stationary rest wholly between
    22:00 and 08:00 (base time), or any 24 h continuous stationary rest.
    Returns list of the calendar date of the night's evening."""
    nights = set()
    for s, e in _blocks_within(runs, a, b, 7 * H):
        ts = tl.time(s)
        if e - s >= 24 * H:  # a 24 h continuous rest is itself a night rest break
            nights.add(ts.date() if ts.hour >= 12 else (ts - timedelta(days=1)).date())
        # every 22:00-08:00 window the block covers for at least 7 h
        evening = (ts - timedelta(days=1)).date()
        while True:
            win_a = tl.idx(datetime.combine(evening, datetime.min.time(), tzinfo=ts.tzinfo) + timedelta(hours=22))
            if win_a >= e:
                break
            if min(e, win_a + 10 * H) - max(s, win_a) >= 7 * H:
                nights.add(evening)
            evening += timedelta(days=1)
    return sorted(nights)


def _period_starts(tl: Timeline, runs, major: int, period: int):
    """Starts for a long period: ends of rests >= major; plus fallback ends of any
    rest break where no qualifying major rest ended in the preceding `period`."""
    major_ends = [e for s, e in runs if e - s >= major]
    starts = set(major_ends)
    for e in tl.any_rest_ends():
        if not any(0 <= e - m <= period for m in major_ends):
            starts.add(e)
    return sorted(i for i in starts if i < tl.n)


def check(events: list[Event], t0: datetime, t_end: datetime, scheme: str = "solo",
          planned: list[Event] = (), only_planned: bool = False) -> Result:
    tl = Timeline(events, t0, t_end, planned)
    res = Result(scheme=scheme)
    if (tl.state == -1).any():
        gaps = int((tl.state == -1).sum())
        res.incomplete.append(f"{gaps} minutes with no EWD record in the assessed window")
        tl.state[tl.state == -1] = REST  # assessed as rest; flagged incomplete above

    runs = tl.rest_runs(include_moving=False)
    runs_any = tl.rest_runs(include_moving=True) if scheme == "two_up" else runs
    rest_ends = tl.any_rest_ends()

    def add(rule, a, b, detail, work=0):
        if only_planned and not _planned_in(tl, a, b):
            return
        res.breaches.append(Breach(rule, tl.time(a), tl.time(min(b, tl.n)), detail, work, _planned_in(tl, a, b)))

    # short periods: forward from end of any rest break, short rests count as breaks
    seen = set()
    for rule, period, max_work, min_rest, min_block in SHORT_PERIODS:
        for a in rest_ends:
            if a >= tl.n:
                continue
            b = a + period
            w = _work_in(tl, a, b)
            if w > max_work:
                key = (rule, a)
                if key not in seen:
                    seen.add(key)
                    add(rule, a, b, f"{w/60:.2f} h work in {period/60:g} h (max {max_work/60:g} h)", w)
                continue
            if b <= tl.n and w > 0:
                blocks = _blocks_within(runs_any, a, b, min_block)
                got = sum(e - s for s, e in blocks)
                if got < min_rest:
                    add(rule, a, b, f"{got} min qualifying rest in {period/60:g} h (need {min_rest} min in blocks of {min_block})", w)

    table = SOLO if scheme == "solo" else TWO_UP
    for key, r in table.items():
        period = r["period"]
        if "nights" in r:
            nr_runs = [(s, e) for s, e in runs if e - s >= 7 * H]
            starts = sorted({e for s, e in nr_runs} | {rest_ends[0]} if rest_ends else set())
        else:
            starts = _period_starts(tl, runs if "major" in r else runs, r.get("major", 15), period)
        for a in starts:
            b = a + period
            w = _work_in(tl, a, b)
            if "max_work" in r and w > r["max_work"]:
                add(f"FAT-{key.upper()}-WORK", a, b, f"{w/60:.1f} h work in {key} (max {r['max_work']/60:g} h)", w)
            if b > tl.n or w == 0:
                continue  # rest requirement needs the full window
            if "major" in r:
                pool = runs_any if (scheme == "two_up" and key == "24h") else runs
                if not _blocks_within(pool, a, b, r["major"]):
                    add(f"FAT-{key.upper()}-REST", a, b, f"no {r['major']/60:g} h continuous stationary rest in {key}", w)
            if "blocks7" in r:
                got = sum(e - s for s, e in _blocks_within(runs, a, b, 7 * H))
                if got < r["blocks7"]:
                    add(f"FAT-{key.upper()}-BLOCKS", a, b, f"{got/60:.1f} h rest in 7 h+ blocks (need {r['blocks7']/60:g} h)", w)
            if "nights" in r:
                nights = _night_rests(tl, runs, a, b)
                consec = any((nights[i + 1] - nights[i]).days == 1 for i in range(len(nights) - 1))
                if len(nights) < r["nights"] or not consec:
                    add(f"FAT-{key.upper()}-NIGHTS", a, b, f"{len(nights)} night rests, consecutive pair: {consec}", w)
    # de-duplicate identical rule hits that start at the same minute
    uniq = {}
    for br in res.breaches:
        uniq.setdefault((br.rule_id, br.window_start), br)
    res.breaches = sorted(uniq.values(), key=lambda b: (b.window_start, b.rule_id))
    return res


def earliest_start(events, t0, shift_minutes, scheme, not_before: datetime, horizon_end: datetime,
                   step=15, max_days=3, work_pattern=None):
    """Earliest start (in `step` minutes) at which the planned shift adds no breach.
    work_pattern: list of (offset_min, length_min, activity) for the planned shift; default
    is a solo pattern with the 15-min breaks needed to satisfy short periods."""
    pattern = work_pattern or default_pattern(shift_minutes)
    t = not_before
    for _ in range(int(max_days * DAY / step)):
        planned = [Event(t + timedelta(minutes=o), t + timedelta(minutes=o + l), act) for o, l, act in pattern]
        end = max(p.end for p in planned) + timedelta(days=1)
        r = check(events, t0, max(end, horizon_end), scheme, planned, only_planned=True)
        if r.ok:
            return t
        t += timedelta(minutes=step)
    return None


def default_pattern(shift_minutes: int):
    """Work blocks of at most 5 h with 30 min breaks, so short-period rules are met."""
    out, o, left = [], 0, shift_minutes
    while left > 0:
        blk = min(300, left)
        out.append((o, blk, "work"))
        o += blk
        left -= blk
        if left > 0:
            out.append((o, 30, "rest"))
            o += 30
    return out
