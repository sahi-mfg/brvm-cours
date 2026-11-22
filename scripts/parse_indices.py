"""Parse BRVM indices from page 1 of a Bulletin Officiel de la Cote."""
import re, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from parse_boc import num

NUMERIC = re.compile(r'^-?[\d ]+(?:[,.]\d+)?\s?%?$|^-$')


def norm_name(s):
    s = s.replace('–', '-').replace('(**)', '').strip()
    s = re.sub(r'\s*-\s*', ' - ', s) if s.startswith('BRVM -') or s.startswith('BRVM–') else s
    s = re.sub(r'^BRVM-', 'BRVM ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s.upper()


def summary_page(pages):
    """Page holding the market summary (usually 1; some 2024 files start with the OPCVM page)."""
    for pg in sorted(pages):
        txt = ' '.join(c['t'] for L in pages[pg] for c in L['cells'])
        if re.search(r'BRVM\s*(COMPOSITE|Composite)', txt) and re.search(r'N°\s*\d+', txt):
            return pg
    return 1


def parse_indices(pages, date):
    out = {}
    ls = pages.get(summary_page(pages), [])
    for L in ls:
        cells = []
        for c in L['cells']:
            if c['t'] in ('(**)', '('): continue
            m = re.match(r'^(BRVM.*?[A-Z])\s*(?:\(\*\*\)|\()?\s*(\d+)$', c['t'])
            if m and not re.match(r'^BRVM ?(10|30)$', c['t']):   # label glued to the 'nb sociétés' column
                cells += [dict(c, t=m.group(1)), dict(c, t=m.group(2))]
            else:
                cells.append(dict(c, t=re.sub(r'\s*\(\*?\*?\)?$', '', c['t']) if c['t'].startswith('BRVM') else c['t']))
        texts = [c['t'] for c in cells]
        # table row: label, nb, valeur, var j, var an, volume, valeur, PER
        if texts and re.match(r'^BRVM\s*[-–]', texts[0]) and len(texts) >= 5 and all(NUMERIC.match(t) for t in texts[1:5]):
            name = norm_name(texts[0])
            vals = [num(t) if t != '-' else None for t in texts[1:8]] + [None] * 7
            if vals[1] is None: continue
            out[name] = {'date': date, 'indice': name, 'valeur': vals[1], 'variation_jour_pct': vals[2],
                         'variation_annuelle_pct': vals[3], 'nb_societes': vals[0], 'volume': vals[4],
                         'valeur_echangee': vals[5], 'per_moyen': vals[6]}
            continue
        # headline: 'BRVM COMPOSITE' '528,25' pairs
        for a, b in zip(cells, cells[1:]):
            m = re.match(r'^(BRVM (COMPOSITE|Composite|10|30|PRESTIGE|Prestige))$', a['t'])
            if m and NUMERIC.match(b['t']) and '%' not in b['t']:
                name = norm_name(a['t'])
                out.setdefault(name, {'date': date, 'indice': name, 'valeur': num(b['t'])})
    return list(out.values())
