"""Deterministic escalation rule engine. No LLM. The orchestrator treats automatic triggers as
authoritative: no prompt or model output can remove them. Discretionary signals are passed to the
agents, who decide."""
import re

FRAUD = re.compile(r"different names|empty shopfront|abandoned house|meet (the )?driver|asked for the parcel by tracking",
                   re.I)
NO_BOOKING = re.compile(r"\bbook(ing|ed)?\b", re.I)
FALSE_CARD_GPS_M, FALSE_CARD_DWELL_S = 150, 45
PERISHABLE_MAX_DELAY_H, HIGH_VALUE, EOM_REVENUE, REPEAT_DNR = 4.0, 500.0, 1000.0, 2


def evaluate(ev, customer, parcel, calendar):
    code = ev["status_code"]
    notes = " | ".join(ev["driver_notes"])
    auto, disc = [], []
    door = code in ("ATTEMPTED", "ACCESS_ISSUE")
    false_card = door and ((ev.get("gps_offset_m") or 0) > FALSE_CARD_GPS_M or
                           (ev.get("dwell_s") or 999) < FALSE_CARD_DWELL_S)
    if door and ev["attempt_number"] >= 3:
        auto.append("3rd failed delivery attempt")
    if false_card:
        auto.append("Possible card left without a genuine attempt")
    if customer["tier"] == "VIP" and customer["exceptions_last_90d"] >= 3:
        auto.append("VIP customer with 3+ exceptions in 90 days")
    if code == "DAMAGED" and parcel["package_type"] == "PERISHABLE":
        auto.append("Damaged perishable")
    if code == "DAMAGED" and parcel["package_type"] == "FRAGILE" and parcel["value"] > HIGH_VALUE:
        auto.append("Damaged fragile item over $500")
    if parcel["package_type"] == "PERISHABLE" and code in ("WEATHER_DELAY", "VEHICLE_DELAY", "ROAD_CLOSURE") \
            and (ev.get("delay_hours") or 0) > PERISHABLE_MAX_DELAY_H:
        auto.append("Perishable delayed more than 4 hours")
    if code == "ADDRESS_ISSUE" and FRAUD.search(notes):
        auto.append("Address pattern suggests fraud")
    if code == "REFUSED" and customer["customer_type"] == "TRADE" and NO_BOOKING.search(notes) \
            and calendar["is_last_business_day_of_month"] and parcel["value"] >= EOM_REVENUE:
        auto.append("Trade delivery refused on last business day of the month")
    if code == "DELIVERED_NOT_RECEIVED" and customer.get("dnr_claims_90d", 0) >= REPEAT_DNR:
        auto.append("Repeat delivered-not-received claim")
    if ev.get("guardrail_injection"):
        auto.append("Prompt injection in driver note")
    if customer["tier"] == "STANDARD" and customer["exceptions_last_90d"] >= 4:
        disc.append("Standard customer with 4+ exceptions in 90 days")
    if customer["tier"] == "PREMIUM" and parcel["package_type"] == "PERISHABLE" and \
            code in ("WEATHER_DELAY", "HEAT_HOLD", "ROAD_CLOSURE"):
        disc.append("Premium perishable affected by weather or fire")
    return {"automatic_triggers": auto, "discretionary_signals": disc, "possible_false_card": false_card,
            "must_escalate": bool(auto)}
