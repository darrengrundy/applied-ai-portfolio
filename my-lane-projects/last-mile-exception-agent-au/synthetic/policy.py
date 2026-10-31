"""Single source of truth for the Australian exception policy.

Used to write the ground-truth labels in generate.py, mirrored in plain English in the
operations playbook, and (for escalation) reused by the deterministic rule engine.
The agents never import this file: they must reach the same answers from the playbook.
"""

RESOLUTIONS = ["REDELIVER_TODAY", "RESCHEDULE", "REROUTE_TO_LOCKER", "REPLACE", "RETURN_TO_SENDER"]
EXCEPTION_CODES = ["ATTEMPTED", "ACCESS_ISSUE", "ADDRESS_ISSUE", "DAMAGED", "REFUSED",
                   "WEATHER_DELAY", "HEAT_HOLD", "VEHICLE_DELAY"]
NOISE_CODES = ["DELIVERED", "SCANNED", "OUT_FOR_DELIVERY"]

LOCKER_RADIUS_KM = 3.0          # nearest eligible locker must be within this distance
PERISHABLE_MAX_DELAY_H = 4.0    # perishables delayed longer than this are replaced
HEAT_LIMIT_C = 30.0             # perishables are never left unattended above this
SAME_DAY_CUTOFF_H = 15.0        # failed attempts before 3pm can go back out on the evening run
HIGH_VALUE = 500.0              # damaged fragile goods above this value are escalated
SIZE = {"SMALL": 1, "MEDIUM": 2, "LARGE": 3}


def locker_ok(locker, size, package_type, signature_required):
    """Can this parcel go into this locker?"""
    if locker is None or package_type == "PERISHABLE" or signature_required:
        return False
    if locker["capacity_status"] == "FULL":
        return False
    if locker["capacity_status"] == "LIMITED" and size != "SMALL":
        return False
    return SIZE[size] <= SIZE[locker["max_package_size"]]


def escalation_triggers(c, p, ev):
    """Deterministic triggers. c=customer, p=parcel, ev=consolidated event dict."""
    auto, disc = [], []
    code = ev["status_code"]
    if code in ("ATTEMPTED", "ACCESS_ISSUE") and ev["attempt_number"] >= 3:
        auto.append("3rd failed delivery attempt")
    if c["tier"] == "VIP" and c["exceptions_last_90d"] >= 3:
        auto.append("VIP customer with 3+ exceptions in 90 days")
    if code == "DAMAGED" and p["package_type"] == "PERISHABLE":
        auto.append("Damaged perishable")
    if code == "DAMAGED" and p["package_type"] == "FRAGILE" and p["value"] > HIGH_VALUE:
        auto.append("Damaged fragile item over $500")
    if p["package_type"] == "PERISHABLE" and code in ("WEATHER_DELAY", "VEHICLE_DELAY") \
            and ev.get("delay_hours", 0) > PERISHABLE_MAX_DELAY_H:
        auto.append("Perishable delayed more than 4 hours")
    if code == "ADDRESS_ISSUE" and ev.get("fraud_pattern"):
        auto.append("Address pattern suggests fraud")
    if c["tier"] == "STANDARD" and c["exceptions_last_90d"] >= 4:
        disc.append("Standard customer with 4+ exceptions in 90 days")
    if c["tier"] == "PREMIUM" and p["package_type"] == "PERISHABLE" and code in ("WEATHER_DELAY", "HEAT_HOLD"):
        disc.append("Premium perishable affected by weather")
    return auto, disc


def label(c, p, ev, nearest_locker):
    """Expected resolution, tone and escalation for one consolidated exception."""
    code, hour = ev["status_code"], ev["hour"]
    perish = p["package_type"] == "PERISHABLE"
    can_locker = locker_ok(nearest_locker, p["package_size"], p["package_type"], p["signature_required"])

    if code in ("ATTEMPTED", "ACCESS_ISSUE"):
        if perish:
            res = "REDELIVER_TODAY" if hour < SAME_DAY_CUTOFF_H else "REPLACE"
        elif ev["attempt_number"] >= 3:
            res = "REROUTE_TO_LOCKER" if can_locker else "RETURN_TO_SENDER"
        elif c["tier"] == "STANDARD" and can_locker:
            res = "REROUTE_TO_LOCKER"
        else:
            res = "RESCHEDULE"
    elif code == "ADDRESS_ISSUE":
        res = "RESCHEDULE"                      # confirm address with customer, then redeliver
    elif code == "DAMAGED":
        res = "REPLACE"
    elif code == "REFUSED":
        res = "RETURN_TO_SENDER"
    elif code == "HEAT_HOLD":
        res = "REDELIVER_TODAY"                 # evening run once it has cooled
    else:                                       # WEATHER_DELAY, VEHICLE_DELAY
        if perish and ev.get("delay_hours", 0) > PERISHABLE_MAX_DELAY_H:
            res = "REPLACE"
        elif ev.get("delay_hours", 0) + hour <= 19:
            res = "REDELIVER_TODAY"
        else:
            res = "RESCHEDULE"

    auto, disc = escalation_triggers(c, p, ev)
    escalate = bool(auto) or bool(disc)
    tone = "FORMAL" if c["tier"] in ("VIP", "PREMIUM") or escalate else "CASUAL"
    return {"expected_resolution": res, "expected_tone": tone,
            "should_escalate": "YES" if escalate else "NO",
            "auto_triggers": "; ".join(auto), "discretionary_triggers": "; ".join(disc)}
