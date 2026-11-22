"""Consistency checks on data/raw_actions.csv. Prints a report; writes data/validation_flags.csv."""
import csv, os, collections, statistics, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = list(csv.DictReader(open(os.path.join(ROOT, 'data', 'raw_actions.csv'))))
f = lambda v: float(v) if v not in ('', None) else None
flags = []
def flag(r, kind, detail):
    flags.append({'date': r['date'], 'ticker': r['ticker'], 'check': kind, 'detail': detail})

per_date = collections.Counter(r['date'] for r in rows)
by_t = collections.defaultdict(list)
for r in rows: by_t[r['ticker']].append(r)

n_var = n_vwap = n_cont = 0
for r in rows:
    p, o, c, v, vol, val, ref = (f(r[k]) for k in ('cours_precedent', 'ouverture', 'cloture', 'variation_jour_pct', 'volume', 'valeur', 'cours_reference'))
    if ref is None or ref <= 0: flag(r, 'ref_missing', '')
    if p and ref and v is not None:
        n_var += 1
        exp = (ref / p - 1) * 100
        if abs(exp - v) > 0.06 + 0.01 * abs(v): flag(r, 'variation', f'prev={p} ref={ref} var={v} exp={exp:.2f}')
    if vol and val:
        n_vwap += 1
        lo = min(x for x in (o, c, p, ref) if x); hi = max(x for x in (o, c, p, ref) if x)
        vw = val / vol
        if not (0.6 * lo <= vw <= 1.4 * hi): flag(r, 'vwap', f'vwap={vw:.1f} lo={lo} hi={hi} vol={vol} val={val}')
    if (vol is None) != (val is None): flag(r, 'vol_val_mismatch', f'vol={vol} val={val}')
for t, rs in by_t.items():
    rs.sort(key=lambda r: r['date'])
    for a, b in zip(rs, rs[1:]):
        n_cont += 1
        if f(a['cours_reference']) and f(b['cours_precedent']) and f(a['cours_reference']) != f(b['cours_precedent']):
            flag(b, 'continuity', f"ref[{a['date']}]={a['cours_reference']} prev={b['cours_precedent']}")
cnt = collections.Counter(x['check'] for x in flags)
print('rows', len(rows), 'dates', len(per_date), 'tickers', len(by_t))
print('rows/date min/median/max', min(per_date.values()), statistics.median(per_date.values()), max(per_date.values()))
low = sorted(d for d, n in per_date.items() if n < 40)
print('dates with <40 rows:', len(low), low[:10])
print(f'checked: variation={n_var} vwap={n_vwap} continuity={n_cont}')
print('flags:', dict(cnt))
with open(os.path.join(ROOT, 'data', 'validation_flags.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, ['date', 'ticker', 'check', 'detail']); w.writeheader(); w.writerows(flags)
for k in cnt:
    ex = [x for x in flags if x['check'] == k][:int(sys.argv[1]) if len(sys.argv) > 1 else 4]
    for x in ex: print(' ', k, x['date'], x['ticker'], x['detail'])
