"""Read-only access to the synthetic day: scans, customers, parcels, Australia Post points, calendar.

Only operational facts are exposed. The generator's answer columns (status_code, sub_type,
delay_hours in parcels.csv; everything in ground_truth.csv) are never loaded here.
"""
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

PII_FIELDS = ["name", "phone", "email", "address", "unit", "street"]
CUSTOMER_FIELDS = ["customer_id", "customer_type", "business_name", "tier", "preferred_channel",
                   "authority_to_leave", "booking_required", "exceptions_last_90d", "dnr_claims_90d",
                   "dwelling", "concierge", "suburb", "postcode", "state", "city"]
PARCEL_FIELDS = ["parcel_id", "customer_id", "city", "package_type", "package_size", "value",
                 "signature_required", "van_id"]
LOCKER_RADIUS_KM = 3.0


def km(lat1, lon1, lat2, lon2):
    r = np.pi / 180
    a = (np.sin((lat2 - lat1) * r / 2) ** 2 +
         np.cos(lat1 * r) * np.cos(lat2 * r) * np.sin((lon2 - lon1) * r / 2) ** 2)
    return 6371 * 2 * np.arcsin(np.sqrt(a))


class World:
    def __init__(self, data_dir):
        d = Path(data_dir)
        self.scans = pd.read_csv(d / "scan_log.csv", dtype=str, keep_default_na=False)
        self.scans_by_parcel = {k: g for k, g in self.scans.groupby("parcel_id", sort=False)}
        cu = pd.read_csv(d / "customers.csv", dtype={"postcode": str}, keep_default_na=False)
        self.customers = cu.set_index("customer_id", drop=False)
        pa = pd.read_csv(d / "parcels.csv")
        self.parcels = pa.set_index("parcel_id", drop=False)
        self.points = pd.read_csv(d / "collection_points.csv", dtype={"postcode": str})
        self.contacts = pd.read_csv(d / "contacts.csv", keep_default_na=False)
        self.story = json.load(open(d / "storylines.json"))
        self.day = dt.date.fromisoformat(self.story["day"])

    # --- tools -------------------------------------------------------------------------
    def read_scans(self, parcel_id):
        g = self.scans_by_parcel.get(parcel_id)
        return [] if g is None else g.to_dict("records")

    def lookup_customer(self, customer_id, include_pii=False):
        row = self.customers.loc[customer_id]
        fields = CUSTOMER_FIELDS + (PII_FIELDS if include_pii else [])
        out = {k: _py(row[k]) for k in fields}
        if out.get("customer_type") != "TRADE":
            out.pop("business_name", None)
        return out

    def lookup_parcel(self, parcel_id):
        row = self.parcels.loc[parcel_id]
        return {k: _py(row[k]) for k in PARCEL_FIELDS}

    def collection_options(self, parcel_id):
        """Nearest Australia Post Parcel Lockers (within 3 km) and the nearest Post Office."""
        p = self.parcels.loc[parcel_id]
        L = self.points[self.points.city == p.city].copy()
        L["distance_km"] = km(p.lat, p.lon, L.lat.values, L.lon.values).round(2)
        L = L.sort_values("distance_km")
        cols = ["point_id", "type", "name", "suburb", "distance_km", "capacity_status", "max_package_size",
                "operating_hours", "hold_business_days"]
        lockers = L[(L.type == "PARCEL_LOCKER") & (L.distance_km <= LOCKER_RADIUS_KM)].head(4)[cols]
        po = L[L.type == "POST_OFFICE"].head(1)[cols]
        return {"parcel_lockers_within_3km": [_rec(r) for r in lockers.to_dict("records")],
                "nearest_post_office": _rec(po.to_dict("records")[0])}

    def point(self, point_id):
        r = self.points[self.points.point_id == point_id]
        return _rec(r.iloc[0].to_dict()) if len(r) else None

    def calendar(self):
        d = self.day
        nxt = d + dt.timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += dt.timedelta(days=1)
        return {"today": d.isoformat(), "weekday": d.strftime("%A"),
                "is_last_business_day_of_month": nxt.month != d.month,
                "next_business_day": f"{nxt.strftime('%A')} {nxt.isoformat()}", "timezone": "AEDT"}

    def contacts_for(self, parcel_id):
        return self.contacts[self.contacts.parcel_id == parcel_id].to_dict("records")


def _py(v):
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    return v


def _rec(r):
    return {k: _py(v) for k, v in r.items()}
