"""Deterministic preprocessing: dedupe scans, consolidate a parcel's events, read the delay
estimate from free text, attach customer messages, and screen driver notes for prompt injection."""
import re

NOISE = {"SCANNED", "OUT_FOR_DELIVERY", "DELIVERED"}
INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior) instructions", r"disregard (the )?(playbook|rules|instructions)",
    r"\bsystem\s*:", r"admin mode", r"new instruction", r"override\s*:", r"skip the critic",
    r"reveal (the )?customer", r"(full name|phone number) in your reply", r"issue a \$?\d+ credit",
    r"approve a (full )?refund", r"do not tell anyone", r"\bassistant\b\s*[,:-]", r"you are now",
    r"mark (it |this )?as delivered", r"classify as delivered", r"send (a )?message to all customers",
    r"jailbreak",
]
INJ = re.compile("|".join(INJECTION_PATTERNS), re.I)
EST = re.compile(r"est(?:imated)?\.?\s*(?:delay\s*)?(\d+(?:\.\d+)?)\s*h(?:rs?|ours?)?", re.I)
REST_OF_DAY = re.compile(r"rest of (the )?day|not expected to reopen today|until further notice", re.I)


def consolidate(world, parcel_id):
    """Return the consolidated event for one parcel, or a noise marker."""
    rows = world.read_scans(parcel_id)
    raw = len(rows)
    rows = [r for r in rows if r["is_duplicate_scan"] != "True"]
    contacts = world.contacts_for(parcel_id)
    dnr = [c for c in contacts if c["contact_type"] == "DNR"]
    complaints = [c for c in contacts if c["contact_type"] in ("FALSE_CARD", "DNR")]
    outcome = [r for r in rows if r["status_code"] not in ("SCANNED", "OUT_FOR_DELIVERY")]
    last = outcome[-1] if outcome else rows[-1]
    first_out = outcome[0] if outcome else last
    code = last["status_code"]
    notes = [r["status_description"] for r in outcome]

    delay = None
    for n in notes:
        m = EST.findall(n)
        if m:
            delay = float(m[-1])
        if REST_OF_DAY.search(n):
            delay = 99.0
    injected = [n for n in notes if INJ.search(n)]

    ev = dict(parcel_id=parcel_id, customer_id=last["customer_id"], status_code=code,
              event_time=first_out["timestamp"], hour=_hour(first_out["timestamp"]),
              driver_notes=["[note withheld: flagged as possible prompt injection]" if INJ.search(n) else n
                            for n in notes],
              label_address=last["delivery_address"], package_type=last["package_type"],
              package_size=last["package_size"], attempt_number=int(last["attempt_number"]),
              gps_offset_m=_num(first_out.get("gps_offset_m")), dwell_s=_num(first_out.get("dwell_s")),
              delay_hours=delay, rows_raw=raw, rows_after_dedup=len(rows),
              customer_messages=[dict(time=c["contact_time"][11:16], channel=c["channel"], message=c["message"])
                                 for c in complaints],
              guardrail_injection=bool(injected), injected_text=injected)
    if dnr:   # the case is the customer's report that a delivered parcel isn't there
        ev.update(status_code="DELIVERED_NOT_RECEIVED", event_time=dnr[0]["contact_time"],
                  hour=_hour(dnr[0]["contact_time"]))
    ev["is_noise"] = ev["status_code"] in NOISE and not complaints
    return ev


def _hour(ts):
    hh, mm = ts[11:13], ts[14:16]
    return round(int(hh) + int(mm) / 60, 3)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
