import sys, json, os
sys.path.insert(0, 'scripts')
from lines import page_lines
base = sys.argv[1]; pat = sys.argv[2]
ref = json.load(open(f'cache/pages/{base}.json'))
new = page_lines(f'pdf/{base}.pdf')
for name, pages in (('PDFKit', ref), ('PyMuPDF', {int(k): v for k, v in new.items()})):
    print('==', name)
    for L in pages.get(1, pages.get('1', [])):
        t = ' | '.join(f"{c['t']}@{c['x0']:.0f}-{c['x1']:.0f}" for c in L['cells'])
        if pat in t: print(f"{L['y']:.1f}", t)
