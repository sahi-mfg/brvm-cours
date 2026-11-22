import sys
import pymupdf

pdf, words = sys.argv[1], sys.argv[2].split('|')
d = pymupdf.open(pdf)
p = d[0]
H = p.rect.height
for b in p.get_text("rawdict")["blocks"]:
    for l in b.get("lines", []):
        for s in l["spans"]:
            t = ''.join(c['c'] for c in s['chars'])
            if t.strip() in words:
                x0, y0, x1, y1 = s['bbox']
                print(repr(t), 'size', s['size'], 'top', round(H - y0, 1), 'bottom', round(H - y1, 1),
                      'baseline', round(H - s['origin'][1], 1), 'asc', s.get('ascender'), 'desc', s.get('descender'),
                      'font', s['font'])
