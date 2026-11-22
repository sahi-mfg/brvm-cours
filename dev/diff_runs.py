"""Compare deux sorties de build.py : python dev/diff_runs.py DATA_REF DATA_NEW"""
import collections, csv, sys

ref, new = sys.argv[1], sys.argv[2]


def cnt(p):
    c = collections.Counter()
    for r in csv.reader(open(p, newline='')):
        c[r[0]] += 1
    return c


a, b = cnt(f'{ref}/raw_indices.csv'), cnt(f'{new}/raw_indices.csv')
d = {k: (a[k], b.get(k, 0)) for k in a if a[k] != b.get(k, 0)}
print('indices: dates différentes', len(d))
ks = sorted(d)
print(' ', ks[:3], ks[-3:])
print(' ', collections.Counter(d.values()).most_common(5))

ra = set(open(f'{ref}/raw_actions.csv', newline='').read().splitlines())
rb = set(open(f'{new}/raw_actions.csv', newline='').read().splitlines())
only_a = sorted(ra - rb)
print('actions: lignes différentes', len(only_a))
for l in only_a:
    print('  ', ','.join(l.split(',')[:2]))
