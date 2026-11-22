"""Independent cross-check of closing prices against sikafinance.com (split-adjusted series)."""
import csv, json, subprocess, os, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUF = {"Côte d'Ivoire": 'ci', 'Sénégal': 'sn', 'Burkina Faso': 'bf', 'Bénin': 'bj', 'Mali': 'ml', 'Niger': 'ne', 'Togo': 'tg'}
soc = {s['ticker']: s for s in csv.DictReader(open(f'{ROOT}/data/publish/brvm_societes.csv'))}
rows = collections.defaultdict(dict)
for r in csv.DictReader(open(f'{ROOT}/data/publish/brvm_cours_actions.csv')):
    if r['cloture'] and r['volume']: rows[r['ticker']][r['date']] = (float(r['cloture']), float(r['volume']))
tickers = sys.argv[1:] or sorted(rows)
tot = collections.Counter(); bad = []
for t in tickers:
    cp = f'{ROOT}/cache/sika/{t}.json'
    if not os.path.exists(cp):
        data = []
        for y in range(2015, 2027):
            for half in (('01-01', '03-31'), ('04-01', '06-30'), ('07-01', '09-30'), ('10-01', '12-31')):
                body = json.dumps({'ticker': f"{t}.{SUF.get(soc[t]['pays'], 'ci')}", 'datedeb': f'{y}-{half[0]}', 'datefin': f'{y}-{half[1]}', 'xperiod': '0'})
                out = subprocess.run(['curl', '-sL', '-m', '60', '-A', 'Mozilla/5.0', '-H', 'Content-Type: application/json', '-X', 'POST',
                                      'https://www.sikafinance.com/api/general/GetHistos', '-d', body], capture_output=True, text=True).stdout
                try: data += json.loads(out).get('lst') or []
                except Exception: pass
        json.dump(data, open(cp, 'w'))
    data = json.load(open(cp))
    sk = {f"{d['Date'][6:]}-{d['Date'][3:5]}-{d['Date'][:2]}": d for d in data}
    common = sorted(set(sk) & set(rows[t]))
    if not common: print(t, 'no overlap', len(sk)); continue
    # adjustment factor is piecewise constant (splits); compare day-over-day returns instead of levels
    n = m = 0
    for a, b in zip(common, common[1:]):
        r_ours = rows[t][b][0] / rows[t][a][0]; r_sk = sk[b]['Close'] / sk[a]['Close'] if sk[a]['Close'] else None
        if r_sk is None: continue
        n += 1
        if abs(r_ours / r_sk - 1) > 0.005:
            m += 1; bad.append((t, a, b, rows[t][a][0], rows[t][b][0], sk[a]['Close'], sk[b]['Close']))
    tot['pairs'] += n; tot['mismatch'] += m
    print(f'{t}: {len(common)} dates communes, {n} rendements comparés, {m} écarts')
print(dict(tot))
json.dump(bad, open(f'{ROOT}/data/crosscheck_sika_ecarts.json', 'w'), ensure_ascii=False)
