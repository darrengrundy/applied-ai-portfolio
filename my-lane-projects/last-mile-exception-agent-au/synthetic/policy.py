"""Single source of truth for the Australian exception policy.

Used to write the ground-truth labels in generate.py, mirrored in plain English in the
operations playbook, and (for escalation) reused by the deterministic rule engine.
The agents never import this file: they must reach the same answers from the playbook.

Demo assumption: carded parcels go to Australia Post (nearest Post Office or Parcel Locker),
because that is the network every Australian recognises. Locations in the demo are
illustrative, not real Australia Post sites.
"""

RESOLUTIONS = ["REDELIVER_TODAY", "RESCHEDULE", "TO_PARCEL_LOCKER", "TO_POST_OFFICE", "REPLACE",
               "RETURN_TO_SENDER"]
EXCEPTION_CODES = ["ATTEMPTED", "ACCESS_ISSUE", "ADDRESS_ISSUE", "DAMAGED", "REFUSED", "WEATHER_DELAY",
                   "HEAT_HOLD", "VEHICLE_DELAY", "ROAD_CLOSURE", "DELIVERED_NOT_RECEIVED"]
NOISE_CODES = ["DELIVERED", "SCANNED", "OUT_FOR_DELIVERY"]

LOCKER_RADIUS_KM = 3.0          # nearest eligible Parcel Locker must be within this distance
PERISHABLE_MAX_DELAY_H = 4.0    # perishables delayed longer than this are replaced
HEAT_LIMIT_C = 30.0             # perishables are never left unattended above this
SAME_DAY_CUTOFF_H = 15.0        # failed attempts before 3pm can go back out on the evening run
LAST_RUN_H = 19.0               # evening run must arrive by 7pm
HIGH_VALUE = 500.0              # damaged fragile goods above this value are escalated
EOM_REVENUE = 1000.0            # trade orders at or above this refused on the last business day of the month
FALSE_CARD_DWELL_S = 45         # a "nobody home" scan this short ...
FALSE_CARD_GPS_M = 150          # ... or this far from the address suggests no genuine attempt
REPEAT_DNR = 2                  # prior delivered-not-received claims in 90 days that trigger review
SIZE = {"SMALL": 1, "MEDIUM": 2, "LARGE": 3}


def locker_ok(locker, size, package_type, signature_required):
    """Can this parcel go into this Parcel Locker?"""
    if locker is None or package_type == "PERISHABLE" or signature_required:
        return False
    if locker["capacity_status"] == "FULL":
        return False
    if locker["capacity_status"] == "LIMITED" and size != "SMALL":
        return False
    return SIZE[size] <= SIZE[locker["max_package_size"]]


def false_card(ev):
    return ev["status_code"] in ("ATTEMPTED", "ACCESS_ISSUE") and \
        (ev.get("dwell_s", 999) < FALSE_CARD_DWELL_S or ev.get("gps_offset_m", 0) > FALSE_CARD_GPS_M)


def escalation_triggers(c, p, ev):
    """Deterministic triggers. c=customer, p=parcel, ev=consolidated event dict."""
    auto, disc = [], []
    code = ev["status_code"]
    if code in ("ATTEMPTED", "ACCESS_ISSUE") and ev["attempt_number"] >= 3:
        auto.append("3rd failed delivery attempt")
    if false_card(ev):
        auto.append("Possible card left without a genuine attempt")
    if c["tier"] == "VIP" and c["exceptions_last_90d"] >= 3:
        auto.append("VIP customer with 3+ exceptions in 90 days")
    if code == "DAMAGED" and p["package_type"] == "PERISHABLE":
        auto.append("Damaged perishable")
    if code == "DAMAGED" and p["package_type"] == "FRAGILE" and p["value"] > HIGH_VALUE:
        auto.append("Damaged fragile item over $500")
    if p["package_type"] == "PERISHABLE" and code in ("WEATHER_DELAY", "VEHICLE_DELAY", "ROAD_CLOSURE") \
            and ev.get("delay_hours", 0) > PERISHABLE_MAX_DELAY_H:
        auto.append("Perishable delayed more than 4 hours")
    if code == "ADDRESS_ISSUE" and ev.get("fraud_pattern"):
        auto.append("Address pattern suggests fraud")
    if code == "REFUSED" and ev.get("no_booking") and ev.get("eom") and p["value"] >= EOM_REVENUE:
        auto.append("Trade delivery refused on last business day of the month")
    if code == "DELIVERED_NOT_RECEIVED" and c.get("dnr_claims_90d", 0) >= REPEAT_DNR:
        auto.append("Repeat delivered-not-received claim")
    if c["tier"] == "STANDARD" and c["exceptions_last_90d"] >= 4:
        disc.append("Standard customer with 4+ exceptions in 90 days")
    if c["tier"] == "PREMIUM" and p["package_type"] == "PERISHABLE" and \
            code in ("WEATHER_DELAY", "HEAT_HOLD", "ROAD_CLOSURE"):
        disc.append("Premium perishable affected by weather or fire")
    return auto, disc


def label(c, p, ev, nearest_locker):
    """Expected resolution, tone and escalation for one consolidated exception.
    nearest_locker = nearest Parcel Locker within LOCKER_RADIUS_KM that this parcel fits, or None."""
    code, hour = ev["status_code"], ev["hour"]
    perish = p["package_type"] == "PERISHABLE"
    trade = c.get("customer_type") == "TRADE"
    can_locker = locker_ok(nearest_locker, p["package_size"], p["package_type"], p["signature_required"])
    delay = ev.get("delay_hours", 0)

    if code in ("ATTEMPTED", "ACCESS_ISSUE"):
        if false_card(ev):
            res = "REDELIVER_TODAY" if hour < SAME_DAY_CUTOFF_H else ("REPLACE" if perish else "RESCHEDULE")
        elif perish:
            res = "REDELIVER_TODAY" if hour < SAME_DAY_CUTOFF_H else "REPLACE"
        elif ev["attempt_number"] >= 3:
            res = "TO_POST_OFFICE"
        elif c["tier"] == "VIP" or trade:
            res = "RESCHEDULE"
        elif can_locker:
            res = "TO_PARCEL_LOCKER"
        else:
            res = "TO_POST_OFFICE"
    elif code == "ADDRESS_ISSUE":
        res = "RESCHEDULE"                      # confirm address (or unit number) with customer, then redeliver
    elif code in ("DAMAGED", "DELIVERED_NOT_RECEIVED"):
        res = "REPLACE"
    elif code == "REFUSED":
        res = "RESCHEDULE" if ev.get("no_booking") else "RETURN_TO_SENDER"
    elif code == "HEAT_HOLD":
        res = "REDELIVER_TODAY"                 # evening run once it has cooled
    else:                                       # WEATHER_DELAY, VEHICLE_DELAY, ROAD_CLOSURE
        if perish and delay > PERISHABLE_MAX_DELAY_H:
            res = "REPLACE"
        elif hour + delay <= LAST_RUN_H:
            res = "REDELIVER_TODAY"
        else:
            res = "RESCHEDULE"

    auto, disc = escalation_triggers(c, p, ev)
    escalate = bool(auto) or bool(disc)
    tone = "FORMAL" if c["tier"] in ("VIP", "PREMIUM") or trade or escalate else "CASUAL"
    return {"expected_resolution": res, "expected_tone": tone,
            "should_escalate": "YES" if escalate else "NO",
            "auto_triggers": "; ".join(auto), "discretionary_triggers": "; ".join(disc)}
