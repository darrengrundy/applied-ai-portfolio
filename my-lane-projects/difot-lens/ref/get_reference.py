"""Download and prepare the two public reference files the pipeline needs.

  ref/pc.csv   - Australian postcodes with locality coordinates and ABS remoteness
                 (github.com/matthewproctor/australianpostcodes)
  ref/aus.json - state boundaries, simplified for the browser
                 (github.com/rowanhogan/australian-states)
"""
import json, math, os, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
PC = 'https://raw.githubusercontent.com/matthewproctor/australianpostcodes/master/australian_postcodes.csv'
ST = 'https://raw.githubusercontent.com/rowanhogan/australian-states/master/states.geojson'
ABBR = {'New South Wales': 'NSW', 'Victoria': 'VIC', 'Queensland': 'QLD', 'South Australia': 'SA', 'Western Australia': 'WA',
        'Tasmania': 'TAS', 'Northern Territory': 'NT', 'Australian Capital Territory': 'ACT'}
sys.setrecursionlimit(100000)

def rdp(pts, eps):  # Ramer-Douglas-Peucker line simplification
    if len(pts) < 3: return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]; dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy)
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        x, y = pts[i]
        d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / L if L > 1e-12 else math.hypot(x - x1, y - y1)
        if d > dmax: dmax, idx = d, i
    return rdp(pts[:idx + 1], eps)[:-1] + rdp(pts[idx:], eps) if dmax > eps else [pts[0], pts[-1]]

def main():
    urllib.request.urlretrieve(PC, os.path.join(HERE, 'pc.csv'))
    g = json.load(urllib.request.urlopen(ST))
    feats = []
    for f in g['features']:
        n = f['properties']['STATE_NAME']
        if n not in ABBR: continue
        geo = f['geometry']; polys = geo['coordinates'] if geo['type'] == 'MultiPolygon' else [geo['coordinates']]
        out = []
        for p in polys:
            o = p[0]
            if len(o) < 30 and ABBR[n] != 'ACT': continue
            h = len(o) // 2
            s = [[round(x, 3), round(y, 3)] for x, y in rdp(o[:h + 1], .015)[:-1] + rdp(o[h:], .015)]
            if len(s) >= 4: out.append([s])
        feats.append({'type': 'Feature', 'properties': {'s': ABBR[n]}, 'geometry': {'type': 'MultiPolygon', 'coordinates': out}})
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(HERE, 'aus.json'), 'w'), separators=(',', ':'))
    print('ref/pc.csv and ref/aus.json ready')

if __name__ == '__main__':
    main()
