"""Parse the equity tables of a BRVM 'Bulletin Officiel de la Cote' PDF into rows.

Layout-agnostic: column anchors are read from the table header of each page
(right edge of header labels), data cells are assigned to the nearest anchor.
Works on the 2018-2022 layout (sector section headers, no sector column) and
the 2023+ layout (sector code column, compartment section headers).
"""
import re, sys, json, os
sys.path.insert(0, os.path.dirname(__file__))
from lines import page_lines

HEADER_FIELDS = {
    'Précédent': 'cours_precedent', 'Ouv.': 'ouverture', 'Clôt.': 'cloture',
    'jour': 'variation_jour_pct', 'Volume': 'volume', 'Valeur': 'valeur',
    'Référence': 'cours_reference', 'Cours Référence': 'cours_reference', 'précédente': 'variation_annuelle_pct',
    'Montant net': 'dividende_net', 'Montantnet': 'dividende_net', 'Date': 'dividende_date',
    'Rdt. Net': 'rendement_net_pct', 'PER': 'per',
    # 2015-2017 layout
    'Moy.': 'cours_moyen', 'Bas': 'plus_bas_annuel', 'Haut': 'plus_haut_annuel', 'Comp.': 'compartiment',
}
# secondary labels: used only when the primary label for that field is absent
HEADER_FALLBACK = {'Variation': 'variation_jour_pct', "l'année": 'variation_annuelle_pct'}
HEADER_NORM = {k.replace(' ', ''): v for k, v in HEADER_FIELDS.items()}
TICKER = re.compile(r'^[A-Z][A-Z0-9]{2,5}$')
SECTOR = re.compile(r'^(AGR|DIS|FIN|IND|SPU|TRP|TRA|AUT|CB|CD|ENE|TEL|SPV)$')
MONTHS = {'janv': 1, 'févr': 2, 'fevr': 2, 'mars': 3, 'avr': 4, 'mai': 5, 'juin': 6, 'juil': 7,
          'août': 8, 'aout': 8, 'sept': 9, 'oct': 10, 'nov': 11, 'déc': 12, 'dec': 12}
DATE_RE = re.compile(r'(\d{1,2})-([a-zéû]+)\.?-(\d{2})')
TOKEN_RE = re.compile(r'\d(?:er|ème|eme|e)\b|\d{1,2}-[a-zéû]+\.?-\d{2}|-?[\d ]*\d(?:[,.]\d+)?\s?%|-?,\d+|-?\d{1,3}(?: \d{3})*(?:[,.]\d+)?|-?\d+(?:[,.]\d+)?|SP|NC|[A-Za-z\-]+')
NONNUM = {'SP', 'NC'}
MARK_RE = re.compile(r'\([A-Za-z][A-Za-z\-\.]{0,5}\)')
NAME_NUM = re.compile(r'^(.*[A-Za-z\)\.])(\d{1,3}(?: \d{3})+|\d{1,3})$')
MENTION_IN_CELL = re.compile(r'(Ex-c|Ex-d|Ex-dr|Val-T)\b')


def num(t):
    t = t.replace('%', '').replace(' ', '').replace('\u00a0', '').strip()
    if t in ('', '-'): return None
    t = t.replace(',', '.')
    if t.startswith('.'): t = '0' + t
    if t.startswith('-.'): t = '-0' + t[1:]
    try: return float(t)
    except ValueError: return None


def parse_date(t):
    m = DATE_RE.fullmatch(t.strip())
    if not m: return None
    d, mon, y = m.groups()
    mo = MONTHS.get(mon.rstrip('.'))
    if not mo: return None
    y = int(y); y += 2000 if y < 70 else 1900
    return f'{y:04d}-{mo:02d}-{int(d):02d}'


def tokens(cell):
    """Split a (possibly merged) cell into tokens."""
    t = cell['t'].strip()
    if TOKEN_RE.fullmatch(t): return [t]
    toks = [m.group(0).strip() for m in TOKEN_RE.finditer(t) if m.group(0).strip()]
    return toks or [t]


def find_anchors(lines_, i):
    """Header block around line i (which contains 'Symbole'). Returns (anchors, kind)."""
    y0 = lines_[i]['y']
    labels = {}
    fallback = {}
    texts = set()
    for L in lines_:
        if abs(L['y'] - y0) <= 22:
            for c in L['cells']:
                texts.add(c['t'])
                key = c['t'].replace(' ', '')
                if key in HEADER_NORM:
                    labels[HEADER_NORM[key]] = c['x1']
                elif key in HEADER_FALLBACK:
                    fallback.setdefault(HEADER_FALLBACK[key], c['x1'])
    for k, v in fallback.items():
        labels.setdefault(k, v)
    if 'nominale' in texts or 'Parité' in texts or "l'origine" in texts:
        kind = 'other'
    elif {'ouverture', 'cloture', 'volume', 'dividende_net'} <= labels.keys():
        kind = 'actions'
    else:
        kind = 'other'
    return labels, kind, y0


def merge_wrapped_digits(ls):
    """A long number overflowing its cell wraps its last digits onto a line just below,
    right-aligned with it (e.g. '27 202 488 31' / '0'). Glue them back.
    Also merges lines whose baselines differ by <= 3pt (row with a 2-line name: ticker
    and numbers sit ~2.3pt apart)."""
    merged = []
    for L in sorted(ls, key=lambda L: -L['y']):
        if merged and merged[-1]['y'] - L['y'] <= 3.0:
            merged[-1]['cells'] = sorted(merged[-1]['cells'] + L['cells'], key=lambda c: c['x1'])
            continue
        merged.append({'y': L['y'], 'cells': list(L['cells'])})
    ls = merged
    out = []
    for L in ls:
        cs = L['cells']
        if out and 0 < out[-1]['y'] - L['y'] <= 8 and not any(c['t'].startswith('TOTAL') for c in cs):
            # digit fragments right-aligned under a numeric cell of the line above (x > name column)
            prev = out[-1]
            keep = []
            for c in cs:
                tgt = [p for p in prev['cells'] if abs(p['x1'] - c['x1']) <= 3 and re.fullmatch(r'[\d ]+', p['t'])]
                if c['x1'] > 150 and re.fullmatch(r'\d{1,3}', c['t']) and tgt:
                    last = tgt[0]['t'].split(' ')[-1]
                    tgt[0]['t'] = tgt[0]['t'] + (' ' if len(last) == 3 and ' ' in tgt[0]['t'] else '') + c['t']
                else:
                    keep.append(c)
            if not keep:
                continue
            L = {'y': L['y'], 'cells': keep}
        out.append(L)
    return out


def parse_pdf(path, pages=None):
    date = re.search(r'boc_(\d{8})', path).group(1)
    date = f'{date[:4]}-{date[4:6]}-{date[6:]}'
    pages = pages if pages is not None else page_lines(path)
    rows, issues = [], []
    carry = None  # last header of previous page (tables continue across pages)
    section = None
    for pg in sorted(pages):
        ls = merge_wrapped_digits(pages[pg])
        # header blocks on this page
        heads = [find_anchors(ls, i) for i, L in enumerate(ls) if any(c['t'] == 'Symbole' for c in L['cells'])]
        if carry is not None:
            heads.append((carry[0], carry[1], 10_000))
        if not heads: continue
        real = [h for h in heads if h[2] < 10_000]
        carry = min(real, key=lambda h: h[2]) if real else carry
        page_rows = []
        conts = []
        for L in ls:
            y = L['y']
            above = [h for h in heads if h[2] >= y + 10]
            if not above: continue
            anchors, kind, hy = min(above, key=lambda h: h[2] - y)
            if kind != 'actions': continue
            cells = L['cells']
            txt = ' '.join(c['t'] for c in cells)
            if re.match(r'^(SECTEUR|AUTRES SECTEURS|COMPARTIMENT|BRVM ?-)', txt):
                section = re.sub(r'\s+-?\d[\d .,]*\s*points.*$', '', txt).strip()
                section = re.sub(r'\s+\d[\d ]*[.,]\d+$', '', section)
                continue
            if txt.startswith('TOTAL'): continue
            # locate ticker
            if len(cells) > 1 and SECTOR.match(cells[0]['t']) and cells[0]['x1'] < 36:
                m = re.match(r'^([A-Z][A-Z0-9]{2,5}) (.+)$', cells[1]['t'])
                if m:  # sector code + 'TICKER NAME' glued in one cell
                    cells = [cells[0], dict(cells[1], t=m.group(1), x1=cells[1]['x0'] + 25), dict(cells[1], t=m.group(2))] + cells[2:]
            k = None
            if cells and cells[0]['x1'] < 90 and re.fullmatch(r'[^A-Z\s]{1,2}[A-Z][A-Z0-9]{2,5}', cells[0]['t']):
                # stray glyph glued before the ticker (e.g. '4ABJC')
                cells = [dict(cells[0], t=re.sub(r'^[^A-Z]+', '', cells[0]['t']))] + cells[1:]
            if len(cells) > 1 and cells[0]['x1'] < 45 and TICKER.match(cells[1]['t']) and cells[1]['x1'] < 90 and (
                    SECTOR.match(cells[0]['t']) or len(cells[0]['t']) <= 3):
                k = 1   # sector code column (possibly with stray glyphs, e.g. '%CD') + ticker (2023+ layouts)
                if not SECTOR.match(cells[0]['t']):
                    cells = [dict(cells[0], t=re.sub(r'[^A-Z]', '', cells[0]['t']))] + cells[1:]
            elif cells and TICKER.match(cells[0]['t']) and cells[0]['x1'] < 90:
                k = 0
            if k is None or k + 1 >= len(cells) or not any(re.search(r'\d', c['t']) for c in cells[k + 1:]):
                conts.append(L); continue
            sector = cells[0]['t'] if k == 1 and SECTOR.match(cells[0]['t']) else None
            first_anchor = min(anchors.values())
            fixed = []
            for c in cells:
                m = NAME_NUM.match(c['t'])
                if m and c['x1'] >= first_anchor - 3 and c['x0'] < first_anchor - 40:
                    fixed += [dict(c, t=m.group(1), x1=first_anchor - 30), dict(c, t=m.group(2))]
                else:
                    fixed.append(c)
            cells = fixed
            name_cells = [c for c in cells[k + 1:] if c['x1'] < first_anchor - 3 and re.search(r'[A-Za-z(]', c['t'])]
            data_cells = [c for c in cells[k + 1:] if c not in name_cells]
            marks = [c['t'][1:-1] for c in name_cells if MARK_RE.fullmatch(c['t'])]
            name_cells = [c for c in name_cells if not MARK_RE.fullmatch(c['t'])]
            rec = {'date': date, 'ticker': cells[k]['t'], 'nom': ' '.join(c['t'] for c in name_cells).replace('(**)', '').strip(),
                   'secteur_code': sector, 'section': section, '_y': y, '_page': pg, '_anchors': anchors,
                   '_marks': marks}
            order = sorted(anchors.items(), key=lambda kv: kv[1])
            names = [n for n, _ in order]
            for c in data_cells:
                mm = MENTION_IN_CELL.findall(c['t'])
                if mm:
                    rec['_marks'].extend(mm)
                    c = dict(c, t=MENTION_IN_CELL.sub('', c['t']).strip())
                    if not c['t']: continue
                toks = tokens(c)
                # nearest anchor for the right edge, earlier tokens go to preceding anchors
                j = min(range(len(order)), key=lambda a: abs(order[a][1] - c['x1']))
                if abs(order[j][1] - c['x1']) > 20:
                    issues.append(f'{date} {rec["ticker"]} unplaced cell {c["t"]!r}@{c["x1"]:.0f}')
                    continue
                for t_i, t in enumerate(reversed(toks)):
                    a = j - t_i
                    if a < 0: issues.append(f'{date} {rec["ticker"]} overflow {c["t"]!r}'); break
                    rec[names[a]] = t
            page_rows.append(rec)
        # attach continuation lines (wrapped names / sector code) to nearest row
        for L in conts:
            if not page_rows: break
            r = min(page_rows, key=lambda r: abs(r['_y'] - L['y']))
            if abs(r['_y'] - L['y']) > 10: continue
            for c in L['cells']:
                if c['x1'] < 36 and SECTOR.match(c['t']) and not r['secteur_code']:
                    r['secteur_code'] = c['t']
                elif c['x1'] < 150 and MARK_RE.fullmatch(c['t']):
                    r['_marks'].append(c['t'][1:-1])
                elif c['x1'] < 150 and not re.fullmatch(r'[\d ,%-]+', c['t']):
                    r['nom'] = (r['nom'] + ' ' + c['t']).strip() if L['y'] < r['_y'] else (c['t'] + ' ' + r['nom']).strip()
        rows.extend(page_rows)
    out = []
    for r in rows:
        o = {'date': r['date'], 'ticker': r['ticker'], 'nom': r['nom'], 'secteur_code': r['secteur_code'],
             'section': r['section']}
        statut = []
        for f in HEADER_FIELDS.values():
            v = r.get(f)
            if f == 'dividende_date':
                o[f] = parse_date(v) if v else None
            elif f == 'compartiment':
                o[f] = v
            elif v in NONNUM:
                o[f] = None; statut.append(f'{f}={v}')
            else:
                o[f] = num(v) if v is not None else None
        o['mention'] = ';'.join(sorted({s.split('=')[1] for s in statut} | set(r['_marks']))) or None
        out.append(o)
    return out, issues


if __name__ == '__main__':
    rows, issues = parse_pdf(sys.argv[1])
    for r in rows: print(json.dumps(r, ensure_ascii=False))
    for i in issues: print('ISSUE', i, file=sys.stderr)
    print(len(rows), 'rows', file=sys.stderr)
