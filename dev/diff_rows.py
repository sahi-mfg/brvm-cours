"""Affiche côte à côte les lignes qui diffèrent : python dev/diff_rows.py DATA_REF DATA_NEW"""
import csv, sys

ref, new = sys.argv[1], sys.argv[2]


def load(p):
    rows = list(csv.reader(open(p, newline='')))
    return rows[0], {(r[0], r[1]): r for r in rows[1:]}


h, a = load(f'{ref}/raw_actions.csv')
_, b = load(f'{new}/raw_actions.csv')
for k in sorted(set(a) | set(b)):
    ra, rb = a.get(k), b.get(k)
    if ra == rb:
        continue
    if ra is None or rb is None:
        print(k, 'seulement dans', 'ref' if rb is None else 'new')
        continue
    d = [f'{h[i]}: {ra[i]!r} -> {rb[i]!r}' for i in range(len(h)) if ra[i] != rb[i]]
    print(k, '; '.join(d))

for name in ('raw_indices.csv',):
    ra = {(r[0], r[1]) for r in csv.reader(open(f'{ref}/{name}', newline=''))}
    rb = {(r[0], r[1]) for r in csv.reader(open(f'{new}/{name}', newline=''))}
    print(name, 'en plus :', sorted(rb - ra), 'en moins :', sorted(ra - rb))
