"""Build the dataset from all PDFs in pdf/ -> data/*.csv (+ per-PDF cache in cache/)."""
import os, sys, json, glob, csv, re
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
from lines import page_lines
from parse_boc import parse_pdf, HEADER_FIELDS
from parse_indices import parse_indices, summary_page

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'cache')
PARSER_VERSION = '12'


def work(path):
    base = os.path.basename(path)[:-4]
    cp = os.path.join(CACHE, base + '.json')
    if os.path.exists(cp) and os.path.getmtime(cp) > os.path.getmtime(path):
        c = json.load(open(cp))
        if c.get('v') == PARSER_VERSION:
            return c
    try:
        pp = os.path.join(CACHE, 'pages', base + '.json')
        if os.path.exists(pp):
            pages = {int(k): v for k, v in json.load(open(pp)).items()}
        else:
            pages = page_lines(path)
            json.dump(pages, open(pp, 'w'))
        pages = json.loads(json.dumps(pages))  # parse mutates cells
        pages = {int(k): v for k, v in pages.items()}
        rows, issues = parse_pdf(path, pages)
        date = rows[0]['date'] if rows else None
        m = re.search(r'boc_(\d{8})', path).group(1)
        idx = parse_indices(pages, f'{m[:4]}-{m[4:6]}-{m[6:]}')
        p1 = ' '.join(c['t'] for L in pages.get(summary_page(pages), []) for c in L['cells'])
        num_m = re.search(r'N°\s*(\d+)', p1)
        date_m = re.search(r'(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+(\d{1,2}(?:er)?\s+\S+\s+\d{4})', p1)
        MOIS = {'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
                'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12}
        pm = re.search(r'(\d{1,2})(?:er)?\s+(\S+)\s+(\d{4})', date_m.group(0)) if date_m else None
        printed = f"{pm.group(3)}-{MOIS.get(pm.group(2).lower(), 0):02d}-{int(pm.group(1)):02d}" if pm else None
        if printed and printed != f'{m[:4]}-{m[4:6]}-{m[6:]}':
            issues.append(f'{base} printed date {printed} != file date -> rows dropped (duplicate bulletin)')
            rows, idx = [], []
        meta = {'file': base, 'date': f'{m[:4]}-{m[4:6]}-{m[6:]}', 'numero': int(num_m.group(1)) if num_m else None,
                'date_imprimee': date_m.group(0) if date_m else None, 'n_actions': len(rows)}
        c = {'v': PARSER_VERSION, 'file': base, 'rows': rows, 'indices': idx, 'issues': issues, 'meta': meta}
    except Exception as e:
        c = {'v': PARSER_VERSION, 'file': base, 'rows': [], 'indices': [], 'issues': [f'{base} EXCEPTION {e!r}']}
    json.dump(c, open(cp, 'w'), ensure_ascii=False)
    return c


if __name__ == '__main__':
    os.makedirs(CACHE, exist_ok=True)
    files = sorted(glob.glob(os.path.join(ROOT, 'pdf', 'boc_*.pdf')))
    if len(sys.argv) > 1:
        files = [f for f in files if any(a in f for a in sys.argv[1:])]
    with Pool(8) as p:
        res = p.map(work, files, chunksize=4)
    rows = [r for c in res for r in c['rows']]
    idx = [r for c in res for r in c['indices']]
    issues = [i for c in res for i in c['issues']]
    # one bulletin per date (some dates may have several file variants)
    seen = set(); dedup = []
    for r in rows:
        k = (r['date'], r['ticker'])
        if k in seen: continue
        seen.add(k); dedup.append(r)
    cols = ['date', 'ticker', 'nom', 'secteur_code', 'section'] + list(dict.fromkeys(HEADER_FIELDS.values())) + ['mention']
    os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
    with open(os.path.join(ROOT, 'data', 'raw_actions.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(sorted(dedup, key=lambda r: (r['date'], r['ticker'])))
    icols = ['date', 'indice', 'valeur', 'variation_jour_pct', 'variation_annuelle_pct', 'nb_societes', 'volume', 'valeur_echangee', 'per_moyen']
    with open(os.path.join(ROOT, 'data', 'raw_indices.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, icols, extrasaction='ignore'); w.writeheader()
        w.writerows(sorted(idx, key=lambda r: (r['date'], r['indice'])))
    open(os.path.join(ROOT, 'data', 'parse_issues.txt'), 'w').write('\n'.join(issues))
    with open(os.path.join(ROOT, 'data', 'bulletins.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, ['date', 'file', 'numero', 'date_imprimee', 'n_actions']); w.writeheader()
        w.writerows(sorted((c['meta'] for c in res if c.get('meta')), key=lambda r: r['date']))
    print(f'{len(files)} pdf, {len(dedup)} rows actions, {len(idx)} rows indices, {len(issues)} issues')
