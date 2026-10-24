"""DIFOT Lens pipeline: carrier connote CSVs -> metrics -> single-page visual.

Usage:
  python pipeline.py --csv "path/to/ConnoteList*.csv" --config config.json --out build/
Steps: load -> prep (clean, geocode, business-day lateness, DIFOT) -> aggregate ->
       trips (freight flow) -> weekly postcode piles -> inject into template.html
All numbers shown on the page come from this file (deterministic, no LLM).
"""
import argparse, glob, json, os
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, '..', 'ref')
RA_CODES = {1: 'Major Cities of Australia', 2: 'Inner Regional Australia', 3: 'Outer Regional Australia', 4: 'Remote Australia', 5: 'Very Remote Australia'}
STATES = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT']
ROAD_FACTOR = 1.25            # straight line -> road km
# Postcode 4875 covers all Torres Strait islands with one shared coordinate; pin known localities.
OVERRIDES = {('4875', 'THURSDAY ISLAND'): (-10.581, 142.219), ('4875', 'HORN ISLAND'): (-10.603, 142.290),
             ('4875', 'BADU ISLAND'): (-10.122, 142.140), ('4875', 'KUBIN'): (-10.237, 142.220),
             ('4875', 'BOIGU ISLAND'): (-9.230, 142.215), ('4875', '__default__'): (-10.581, 142.219)}

def r(x, n=4):
    return None if pd.isna(x) else round(float(x), n)

# ---------------------------------------------------------------- load
def load(pattern):
    files = sorted(glob.glob(pattern))
    if not files: raise SystemExit(f'No CSVs match {pattern}')
    d = pd.concat([pd.read_csv(f, dtype=str) for f in files])
    d = d.drop_duplicates().reset_index(drop=True)
    for c in ['ConnoteDate', 'ETADate', 'DelvDate']:
        d[c] = pd.to_datetime(d[c], dayfirst=True, errors='coerce')
    for c in ['Items', 'Pallets', 'Kgs', 'ChargedKgs', 'Cubic', 'TotalCharge', 'DelvItems']:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    return d

# ---------------------------------------------------------------- geocode
def geocoder():
    pc = pd.read_csv(os.path.join(REF, 'pc.csv'), dtype={'postcode': str}, low_memory=False)
    pc = pc[pc.lat.abs() > 1].copy()
    pc['postcode'] = pc.postcode.str.zfill(4)
    pc['la'] = pd.to_numeric(pc.Lat_precise, errors='coerce').fillna(pc.lat)
    pc['lo'] = pd.to_numeric(pc.Long_precise, errors='coerce').fillna(pc.long)
    loc = pc.groupby(['postcode', pc.locality.str.upper()])[['la', 'lo']].mean()
    pcm = pc.groupby('postcode')[['la', 'lo']].mean()
    for (p, l), (a, b) in OVERRIDES.items():
        if l == '__default__': pcm.loc[p] = [a, b]
        else: loc.loc[(p, l), :] = [a, b]
    pc['RA_2021_NAME'] = pc.RA_2021_NAME.fillna(pc.RA_2016.map(RA_CODES))
    ra = pc.dropna(subset=['RA_2021_NAME']).groupby('postcode').RA_2021_NAME.agg(lambda s: s.mode()[0])
    sa4 = pc.dropna(subset=['sa4name']).groupby('postcode').sa4name.agg(lambda s: s.mode()[0])
    def geo(postcodes, suburbs):
        key = pd.MultiIndex.from_arrays([postcodes, suburbs.str.upper().str.strip()])
        a = loc.reindex(key)
        fb = pcm.reindex(postcodes)
        return (a.la.values, a.lo.values) if False else (
            np.where(np.isnan(a.la.values), fb.la.values, a.la.values),
            np.where(np.isnan(a.lo.values), fb.lo.values, a.lo.values))
    return geo, ra, sa4

# ---------------------------------------------------------------- prep
def prep(d, geo):
    d['units'] = d.Items + d.Pallets
    for p in ['Sender', 'Receiver']:
        pcs = d[p + 'PostCode'].astype(str).str.zfill(4)
        d[p + 'PostCode'] = pcs
        d[p[0] + 'lat'], d[p[0] + 'lon'] = geo(pcs.values, d[p + 'Suburb'].fillna(''))
    la1, lo1, la2, lo2 = [np.radians(d[c]) for c in ['Slat', 'Slon', 'Rlat', 'Rlon']]
    a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    d['km'] = 2 * 6371 * np.arcsin(np.sqrt(a)) * ROAD_FACTOR
    deliv = d.DelvDate.notna()
    ok = deliv & (d.DelvDate >= d.ConnoteDate)
    D = lambda s: s.values.astype('datetime64[D]')
    d['late_bd'] = np.nan
    d.loc[ok, 'late_bd'] = np.busday_count(D(d.loc[ok, 'ETADate']), D(d.loc[ok, 'DelvDate']))
    d['ontime'] = np.where(ok, d.late_bd <= 0, np.nan)
    d['infull'] = np.where(ok, d.DelvItems >= d.units, np.nan)
    d['difot'] = np.where(ok, (d.late_bd <= 0) & (d.DelvItems >= d.units), np.nan)
    d['status'] = np.select([~deliv, ~ok, d.difot == 1], ['open', 'bad_date', 'pass'], 'fail')
    return d

# ---------------------------------------------------------------- aggregate
def aggregate(d, ra, sa4):
    d = d.copy()
    d['sa4'] = d.ReceiverPostCode.map(sa4).fillna(d.ReceiverState)
    d['remote'] = d.ReceiverPostCode.map(ra)
    last_full_monday = (d.ConnoteDate.max() - pd.Timedelta(days=d.ConnoteDate.max().weekday()))
    d = d[d.ConnoteDate < last_full_monday]            # drop final partial week
    d['wk'] = d.ConnoteDate.dt.to_period('W-SUN').dt.start_time
    d['mo'] = d.ConnoteDate.dt.month
    weeks = sorted(d.wk.unique())
    out = {'weeks': [pd.Timestamp(w).strftime('%Y-%m-%d') for w in weeks]}
    c = d[d.status.isin(['pass', 'fail'])]
    g = d.groupby('wk').agg(n=('Connote', 'size'), cost=('TotalCharge', 'sum'), kg=('Kgs', 'sum'), km=('km', 'sum'))
    g = g.join(c.groupby('wk').agg(difot=('difot', 'mean'), ot=('ontime', 'mean'), inf=('infull', 'mean')))
    out['nat'] = [dict(n=int(x.n), difot=r(x.difot), ot=r(x.ot), inf=r(x.inf), cps=r(x.cost / x.n, 2),
                       cpkg=r(x.cost / x.kg, 3), cpkm=r(x.cost / x.km, 4), avgkm=r(x.km / x.n, 1)) for _, x in g.iterrows()]
    sw = {}
    for s in STATES:
        a = d[d.ReceiverState == s].groupby('wk').agg(n=('Connote', 'size'), cost=('TotalCharge', 'sum'), kg=('Kgs', 'sum'), km=('km', 'sum'))
        a = a.join(c[c.ReceiverState == s].groupby('wk').difot.mean()).reindex(weeks)
        sw[s] = [[int(0 if pd.isna(x.n) else x.n), r(x.difot, 3), r(x.cost / x.n, 2) if x.n else None,
                  r(x.cost / x.kg, 3) if x.n else None, r(x.km / x.n, 0) if x.n else None] for _, x in a.iterrows()]
    out['stateWeek'] = sw
    st = d.groupby('ReceiverState').agg(n=('Connote', 'size'), cost=('TotalCharge', 'sum'), kg=('Kgs', 'sum'), km=('km', 'sum')).join(c.groupby('ReceiverState').difot.mean())
    out['stateTot'] = {s: dict(n=int(x.n), difot=r(x.difot, 3), cps=r(x.cost / x.n, 2), cpkg=r(x.cost / x.kg, 3), avgkm=r(x.km / x.n, 0)) for s, x in st.iterrows()}
    top = d.SenderSuburb.str.title().value_counts().head(7).index
    d['orig'] = np.where(d.SenderSuburb.str.title().isin(top), d.SenderSuburb.str.title(), 'Other')
    c = d[d.status.isin(['pass', 'fail'])].copy()
    og = d.groupby('orig').agg(n=('Connote', 'size'), lat=('Slat', 'median'), lon=('Slon', 'median'), st=('SenderState', lambda s: s.mode()[0])).join(c.groupby('orig').difot.mean())
    out['origins'] = [dict(name=k, n=int(x.n), lat=r(x.lat), lon=r(x.lon), st=x.st, difot=r(x.difot, 3)) for k, x in og.iterrows() if k != 'Other' and x.n >= 100]
    # postcode x month (kept for compatibility) + postcode list used by weekly piles
    d['rpc'] = d.ReceiverPostCode
    c['rpc'] = c.ReceiverPostCode
    pg = c.groupby(['rpc', 'mo']).agg(n=('difot', 'size'), f=('difot', lambda s: int((s == 0).sum())))
    loc = d.groupby('rpc').agg(lat=('Rlat', 'median'), lon=('Rlon', 'median'), sub=('ReceiverSuburb', lambda s: s.str.title().mode()[0]), st=('ReceiverState', 'first'))
    months = sorted(d.mo.unique()); mi = {m: i for i, m in enumerate(months)}
    out['months'] = [int(m) for m in months]
    pcs = []
    pg_idx = set(pg.index.get_level_values(0))
    for p, x in loc.iterrows():
        if p not in pg_idx: continue
        sub = pg.loc[p]
        m = [[int(sub.loc[mo].n), int(sub.loc[mo].f)] if mo in sub.index else [0, 0] for mo in months]
        pcs.append([p, x['sub'], x.st, r(x.lat, 3), r(x.lon, 3), m])
    out['postcodes'] = pcs
    c['svc'] = np.busday_count(c.ConnoteDate.values.astype('datetime64[D]'), c.ETADate.values.astype('datetime64[D]')).clip(1, 5)
    out['svc'] = [[int(k), int(v['size']), r(v['mean'], 3)] for k, v in c.groupby('svc').difot.agg(['size', 'mean']).iterrows()]
    out['origDifot'] = [[k, int(v['size']), r(v['mean'], 3)] for k, v in c.groupby('orig').difot.agg(['size', 'mean']).sort_values('size', ascending=False).iterrows()]
    f = c[c.difot == 0]
    out['lateDist'] = [[int(k), int(v)] for k, v in f.late_bd.clip(upper=5).value_counts().sort_index().items()]
    out['remote'] = [[k, int(v['size']), r(v['mean'], 3)] for k, v in c.groupby('remote').difot.agg(['size', 'mean']).iterrows()]
    out['etaDow'] = [[int(k), int(v['size']), r(v['mean'], 3)] for k, v in c.groupby(c.ETADate.dt.dayofweek).difot.agg(['size', 'mean']).iterrows()]
    allc = c
    out['kpi'] = dict(n=int(len(d)), measured=int(len(allc)), open=int((d.status == 'open').sum()), difot=r(allc.difot.mean()),
                      ot=r(allc.ontime.mean()), inf=r(allc.infull.mean()), spend=round(float(d.TotalCharge.sum())),
                      cps=r(d.TotalCharge.sum() / len(d), 2), cpkg=r(d.TotalCharge.sum() / d.Kgs.sum(), 3),
                      cpkm=r(d.TotalCharge.sum() / d.km.sum(), 4), avgkm=r(d.km.mean(), 0), fails=int((allc.difot == 0).sum()),
                      oneday=r((f.late_bd == 1).mean(), 3), start=d.ConnoteDate.min().strftime('%d %b %Y'), end=d.ConnoteDate.max().strftime('%d %b %Y'))
    w = c.groupby('wk').agg(n=('difot', 'size'), df=('difot', 'mean'))
    out['volScatter'] = [[int(x.n), r(x.df, 3)] for _, x in w.iterrows()]
    out['volCorr'] = r(w.corr().iloc[0, 1], 2)
    # weekly piles per postcode
    wi = {w: i for i, w in enumerate(weeks)}
    pidx = {p[0]: i for i, p in enumerate(pcs)}
    N = np.zeros((len(pcs), len(weeks)), int); F = np.zeros_like(N)
    for pc_, w_, df in zip(c.rpc, c.wk, c.difot):
        i = pidx.get(pc_)
        if i is not None: N[i, wi[w_]] += 1; F[i, wi[w_]] += df == 0
    pw = {'n': N.tolist(), 'f': F.tolist()}
    return out, pw

# ---------------------------------------------------------------- trips (freight flow)
def trips(d, day0):
    d = d[d.status != 'bad_date'].copy()
    d['s'] = (d.ConnoteDate - day0).dt.days
    end = d.DelvDate.where(d.DelvDate.notna(), d.ETADate)
    d['e'] = (end - day0).dt.days
    d = d[(d.s >= 0) & (d.e >= d.s) & (d.e - d.s <= 21) & d.Slat.notna() & d.Rlat.notna()]
    d['f'] = np.select([d.status == 'open', d.difot == 1], [2, 0], 1)
    d['sk'] = d.Slat.round(2).astype(str) + ',' + d.Slon.round(2).astype(str)
    d['rk'] = d.Rlat.round(2).astype(str) + ',' + d.Rlon.round(2).astype(str)
    keys = pd.Index(pd.unique(pd.concat([d.sk, d.rk])))
    d['o'] = keys.get_indexer(d.sk); d['dd'] = keys.get_indexer(d.rk)
    d = d.sort_values('s')
    P = [[float(k.split(',')[1]), float(k.split(',')[0])] for k in keys]
    days = int(d.e.max()) + 1
    deliv = np.zeros(days, int); late = np.zeros(days, int); transit = np.zeros(days, int)
    dl = d[d.f != 2]
    np.add.at(deliv, dl.e.values, 1); np.add.at(late, dl.e.values, (dl.f.values == 1).astype(int))
    diff = np.zeros(days + 1, int); np.add.at(diff, d.s.values, 1); np.add.at(diff, d.e.values, -1); transit = np.cumsum(diff)[:days]
    return dict(P=P, o=d.o.tolist(), d=d.dd.tolist(), s=d.s.tolist(), t=(d.e - d.s).tolist(), f=d.f.tolist(),
                days=days, deliv=deliv.tolist(), late=late.tolist(), transit=transit.tolist())

# ---------------------------------------------------------------- build
def build(data, pw, tr, cfg, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    t = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    j = lambda o: json.dumps(o, separators=(',', ':'))
    for k, v in [('__CFG__', j(cfg)), ('__DATA__', j(data)), ('__AUS__', open(os.path.join(REF, 'aus.json')).read()),
                 ('__TRIPS__', j(tr)), ('__PW__', j(pw))]:
        t = t.replace(k, v)
    t = t.replace('__TITLE__', cfg.get('pageTitle', cfg.get('title', 'DIFOT Lens')))
    path = os.path.join(out_dir, cfg.get('file', 'difot-lens.html'))
    open(path, 'w', encoding='utf-8').write(t)
    return path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True); ap.add_argument('--config', required=True); ap.add_argument('--out', default='build')
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding='utf-8'))
    geo, ra, sa4 = geocoder()
    d = prep(load(a.csv), geo)
    print('rows', len(d), d.status.value_counts().to_dict())
    data, pw = aggregate(d, ra, sa4)
    tr = trips(d, pd.Timestamp(data['weeks'][0]))
    print('DIFOT', data['kpi']['difot'], 'spend', data['kpi']['spend'], 'trips', len(tr['s']))
    print('wrote', build(data, pw, tr, cfg, a.out))

if __name__ == '__main__':
    main()
