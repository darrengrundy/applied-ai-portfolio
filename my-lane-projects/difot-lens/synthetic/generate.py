"""Synthetic connote generator for the DIFOT Lens demo.

Banksia Trade Supply Co. is a FICTITIOUS plumbing and building-products wholesaler with three
east-coast DCs. Customers, carrier, accounts and every number are invented; only real
Australian postcodes/suburbs are used for geography. Output matches the carrier
"ConnoteList" CSV schema so the same pipeline runs unchanged.

Built-in storylines (so the root-cause views have something to find):
  1. Truganina (VIC) DC capacity crunch, Apr-Jul; a second shift from 3 Aug fixes it.
  2. North/regional QLD wet season, Feb-Mar: late deliveries into outer/remote QLD.
  3. Melbourne -> Perth linehaul disruption, 7-27 Sep.
  4. Friday dispatch on next-day lanes misses the carrier cut-off more often.
  5. Fuel levy creeps up all year and a 4.5% rate review lands on 1 Jul (cost/kg rises).

Usage: python generate.py --out data/ --seed 7
"""
import argparse, os
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, '..', 'ref', 'pc.csv')
START, END = pd.Timestamp('2026-01-05'), pd.Timestamp('2026-10-23')
TARGET_ROWS = 318_000
HOLIDAYS = np.array(['2026-01-26', '2026-04-03', '2026-04-06', '2026-06-08'], dtype='datetime64[D]')
DCS = {  # state served -> DC
    'QLD': dict(acct='71001', name='BANKSIA TRADE SUPPLY - QLD DC', suburb='Larapinta', pc='4110', st='QLD'),
    'NSW': dict(acct='71002', name='BANKSIA TRADE SUPPLY - NSW DC', suburb='Eastern Creek', pc='2766', st='NSW'),
    'VIC': dict(acct='71003', name='BANKSIA TRADE SUPPLY - VIC DC', suburb='Truganina', pc='3029', st='VIC'),
}
HOME_DC = {'QLD': 'QLD', 'NT': 'QLD', 'NSW': 'NSW', 'ACT': 'NSW', 'VIC': 'VIC', 'TAS': 'VIC', 'SA': 'VIC', 'WA': 'VIC'}
STATE_SHARE = {'VIC': .29, 'NSW': .29, 'QLD': .26, 'SA': .07, 'WA': .045, 'TAS': .022, 'ACT': .014, 'NT': .009}
RA_W = {'Major Cities of Australia': 1.0, 'Inner Regional Australia': .45, 'Outer Regional Australia': .22,
        'Remote Australia': .07, 'Very Remote Australia': .03}
CHAINS = ['TradeHub Plumbing', 'PipeLine Supplies', 'BuildMate Hardware', 'Coastal Plumbing Centre',
          'Ridgeway Trade Depot', 'Southern Bathroom Co', 'Copperfield Hardware', 'Waratah Water Supplies']

RA_CODES = {1: 'Major Cities of Australia', 2: 'Inner Regional Australia', 3: 'Outer Regional Australia', 4: 'Remote Australia', 5: 'Very Remote Australia'}

def haversine(a1, o1, a2, o2):
    a1, o1, a2, o2 = map(np.radians, (a1, o1, a2, o2))
    h = np.sin((a2 - a1) / 2) ** 2 + np.cos(a1) * np.cos(a2) * np.sin((o2 - o1) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(h))

def destinations(rng):
    pc = pd.read_csv(REF, dtype={'postcode': str}, low_memory=False)
    pc['RA_2021_NAME'] = pc.RA_2021_NAME.fillna(pc.RA_2016.map(RA_CODES))   # NT has no 2021 class in the source
    pc = pc[(pc.lat.abs() > 1) & (pc.type == 'Delivery Area') & pc.RA_2021_NAME.isin(RA_W) & pc.state.isin(STATE_SHARE)].copy()
    pc = pc[pc.postcode != '4875']                                   # skip Torres Strait (shared coordinate)
    pc['la'] = pd.to_numeric(pc.Lat_precise, errors='coerce').fillna(pc.lat)
    pc['lo'] = pd.to_numeric(pc.Long_precise, errors='coerce').fillna(pc.long)
    pc = pc.sort_values('locality').groupby('postcode').head(1)       # one delivery suburb per postcode
    pc = pc.sample(frac=.55, random_state=int(rng.integers(1e9)))     # customers in about half the postcodes
    w = pc.RA_2021_NAME.map(RA_W) * rng.lognormal(0, .9, len(pc))     # uneven customer sizes
    pc['w'] = w / w.groupby(pc.state).transform('sum') * pc.state.map(STATE_SHARE)
    pc['w'] /= pc.w.sum()
    pc['cust'] = rng.choice(CHAINS, len(pc), p=np.array([.2, .18, .16, .12, .1, .09, .08, .07]))
    return pc.reset_index(drop=True)

def volume_index(days):
    t = (days - START).days.values / 7.0
    base = .55 + .72 / (1 + np.exp(-(t - 16) / 4.5))                  # growth Jan -> Sep
    base *= np.where((t >= 22) & (t < 26), 1.12, 1)                    # June EOFY push
    base *= np.where(t < 2, .85, 1)
    return base

def service_days(st_o, st_d, km, ra):
    s = np.select([km < 60, (st_o == st_d) & (km < 220), (st_o == st_d) & (km < 800), st_o == st_d,
                   km < 1100, km < 2100, km < 3000], [1, 1, 2, 3, 2, 3, 4], 6)
    s = s + np.select([ra == 'Remote Australia', ra == 'Very Remote Australia'], [1, 2], 0)
    s = s + ((st_o == st_d) & (km >= 220) & (km < 800) & (ra != 'Major Cities of Australia'))
    return s

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='data'); ap.add_argument('--seed', type=int, default=7)
    a = ap.parse_args(); rng = np.random.default_rng(a.seed); os.makedirs(a.out, exist_ok=True)
    dest = destinations(rng)
    days = pd.bdate_range(START, END, freq='C', holidays=HOLIDAYS.astype(str).tolist())
    dw = np.array([1.06, 1.05, 1.0, .99, .9])[days.weekday]
    per_day = volume_index(days) * dw
    counts = rng.poisson(per_day / per_day.sum() * TARGET_ROWS)
    cdate = np.repeat(days.values, counts)
    n = len(cdate)
    di = rng.choice(len(dest), n, p=dest.w.values)
    D = dest.iloc[di].reset_index(drop=True)
    # origin DC: home DC, 11% cross-supplied from another DC (stock balancing)
    home = D.state.map(HOME_DC).values
    other = np.array([rng.choice([k for k in DCS if k != h]) for h in home])
    orig = np.where(rng.random(n) < .11, other, home)
    O = pd.DataFrame([DCS[o] for o in orig])
    pcref = pd.read_csv(REF, dtype={'postcode': str}, low_memory=False)
    dc_xy = {k: pcref[(pcref.postcode == v['pc']) & (pcref.locality.str.upper() == v['suburb'].upper())][['Lat_precise', 'Long_precise']].astype(float).iloc[0].values for k, v in DCS.items()}
    olat = np.array([dc_xy[o][0] for o in orig]); olon = np.array([dc_xy[o][1] for o in orig])
    km = haversine(olat, olon, D.la.values, D.lo.values) * 1.25
    svc = service_days(O.st.values, D.state.values, km, D.RA_2021_NAME.values)
    cd = cdate.astype('datetime64[D]')
    eta = np.busday_offset(cd, svc, roll='forward', holidays=HOLIDAYS)
    # ---------------- lateness model
    wk = ((pd.to_datetime(cdate) - START).days.values // 7)
    vol = volume_index(pd.to_datetime(cdate))
    p = np.select([svc == 1, svc == 2, svc == 3, svc == 4], [.13, .085, .07, .06], .05)
    p = p * (.75 + .35 * vol)                                                      # busier = worse
    p = p * np.where(orig == 'NSW', .8, 1)                                          # NSW DC runs best
    vic_crunch = np.interp(wk, [0, 12, 16, 20, 29, 30, 42], [1, 1, 1.9, 2.3, 2.1, 1.05, 1])
    p = p * np.where(orig == 'VIC', vic_crunch, 1)                                  # story 1
    wet = (D.state.values == 'QLD') & (D.la.values > -24.5) & (wk >= 4) & (wk <= 10)
    p = p * np.where(wet, 3.0, 1)                                                   # story 2
    perth = (orig == 'VIC') & (D.state.values == 'WA') & (wk >= 35) & (wk <= 37)
    p = p * np.where(perth, 4.5, 1)                                                 # story 3
    fri = (pd.to_datetime(cdate).weekday == 4) & (svc == 1)
    p = p * np.where(fri, 1.6, 1)                                                   # story 4
    p = p + np.where((D.RA_2021_NAME.values == 'Major Cities of Australia') & (svc == 1), .02, 0)
    noise = rng.lognormal(0, .13, (3, 60))                                          # week-to-week wobble per DC
    p = p * noise[np.searchsorted(list(DCS), orig), wk]
    late = rng.random(n) < np.clip(p, 0, .85)
    lateby = rng.choice([1, 2, 3, 4, 6], n, p=[.79, .13, .05, .02, .01])
    early = (~late) & (svc >= 2) & (rng.random(n) < .07)
    delv = np.busday_offset(eta, np.where(late, lateby, np.where(early, -1, 0)), roll='forward', holidays=HOLIDAYS)
    delv = np.maximum(delv, cd + np.timedelta64(1, 'D'))
    # ---------------- freight profile
    pallet = rng.random(n) < .21
    items = np.where(pallet, 0, 1 + rng.poisson(1.6, n))
    pallets = np.where(pallet, 1 + rng.poisson(.35, n), 0)
    kgs = np.where(pallet, pallets * rng.uniform(110, 480, n), items * rng.lognormal(1.7, .7, n)).round()
    kgs = np.maximum(kgs, 1)
    cubic = np.where(pallet, pallets * rng.uniform(1.0, 1.7, n), kgs / rng.uniform(110, 260, n)).round(4)
    ckg = np.maximum(kgs, np.ceil(cubic * 250))
    units = items + pallets
    infull_miss = rng.random(n) < .0018
    delv_items = np.where(infull_miss, np.maximum(units - 1, 0), units)
    # ---------------- cost: rate card x fuel levy x July rate review
    zone = np.select([km < 60, O.st.values == D.state.values, km < 2100], [0, 1, 2], 3)
    base = np.array([9.5, 13.0, 15.5, 24.0])[zone]; perkg = np.array([.105, .17, .22, .43])[zone]
    perpal = np.array([58, 92, 135, 290])[zone]
    remote = np.select([D.RA_2021_NAME.values == 'Remote Australia', D.RA_2021_NAME.values == 'Very Remote Australia'], [1.2, 1.4], 1)
    linehaul = np.where(pallet, pallets * perpal, base + perkg * ckg) * remote
    month = pd.to_datetime(cdate).month.values
    fuel = 1 + np.interp(month, [1, 10], [.155, .225])
    review = np.where(month >= 7, 1.045, 1)
    charge = (linehaul * fuel * review * rng.uniform(.97, 1.03, n)).round(2)
    # ---------------- open consignments (not yet delivered at extract date)
    extract = np.datetime64(END.date())
    open_ = delv > extract
    fmt = lambda x: pd.to_datetime(x).strftime('%d/%m/%Y')
    df = pd.DataFrame({
        'ConnoteDate': fmt(cd),
        'Connote': [f'{acc}{i:08d}' for acc, i in zip(O.acct.values, range(5_000_000, 5_000_000 + n))],
        'AccountNo': O.acct.values, 'SenderName': O.name.values, 'SenderSuburb': O.suburb.values,
        'SenderPostCode': O.pc.values, 'SenderState': O.st.values,
        'ReceiverName': [f'{c} {s.title()}' for c, s in zip(D.cust.values, D.locality.values)],
        'ReceiverSuburb': D.locality.str.title().values, 'ReceiverPostCode': D.postcode.values, 'ReceiverState': D.state.values,
        'CustomerRef': [f'SO{x:07d}' for x in rng.integers(1_000_000, 9_999_999, n)],
        'Items': items, 'Pallets': pallets, 'Kgs': kgs.astype(int), 'ChargedKgs': ckg.astype(int), 'Cubic': cubic,
        'TotalCharge': charge, 'ETADate': fmt(eta),
        'DelvDate': np.where(open_, '', fmt(delv)), 'DelvItems': np.where(open_, '', delv_items.astype(str)),
    })
    df = df.sort_values(['ConnoteDate', 'Connote'], key=lambda s: pd.to_datetime(s, dayfirst=True) if s.name == 'ConnoteDate' else s)
    # split into monthly files like the carrier portal export
    m = pd.to_datetime(df.ConnoteDate, dayfirst=True).dt.month
    for k, g in df.groupby(m):
        g.to_csv(os.path.join(a.out, f'ConnoteList_banksia_2026-{k:02d}.csv'), index=False)
    print(f'{n:,} consignments, {len(dest):,} delivery suburbs, {open_.sum():,} open, late rate {late.mean():.1%}')

if __name__ == '__main__':
    main()
