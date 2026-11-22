"""Turn the PDF's characters into lines of cells (cell = run of chars separated by gaps > GAP pt).

Characters come from PyMuPDF (cross-platform). Coordinates are converted to a bottom-left origin
(y grows upwards), as in the original PDFKit extractor, so that the parser's geometry is unchanged.
"""
import collections
import pymupdf
GAP = 3.5
EXTRACTOR = "pymupdf"


def page_chars(pdf):
    """{page: [(x0, y0, x1, y1, char)]}, y measured from the bottom of the page."""
    pages = collections.defaultdict(list)
    with pymupdf.open(pdf) as doc:
        for pno, page in enumerate(doc, start=1):
            H = page.rect.height
            for b in page.get_text("rawdict")["blocks"]:
                for l in b.get("lines", []):
                    for s in l["spans"]:
                        # Vertical extent from the baseline and font size, not from the font's own
                        # ascender: two fonts on the same line then get the same top, as with PDFKit.
                        size = s["size"]
                        for c in s["chars"]:
                            ch = c["c"]
                            if not ch.strip() or not ch.isprintable():   # e.g. \x03 fillers
                                continue
                            x0, _, x1, _ = c["bbox"]
                            base = H - c["origin"][1]
                            pages[pno].append((round(x0, 1), round(base - 0.25 * size, 1),
                                               round(x1, 1), round(base + 0.75 * size, 1), ch))
    return pages


def page_lines(pdf):
    pages = page_chars(pdf)
    res = {}
    for pg, chars in pages.items():
        vis = [c for c in chars if c[4].strip()]
        # cluster by baseline-ish (top y = maxY); tolerance 2pt
        vis.sort(key=lambda c: -c[3])
        lines = []
        for c in vis:
            if lines and abs(lines[-1][0] - c[3]) <= 2.0:
                lines[-1][1].append(c)
            else:
                lines.append([c[3], [c]])
        out_lines = []
        for y, cs in lines:
            cs.sort(key=lambda c: c[0])
            cells = []
            for c in cs:
                if cells and c[0] - cells[-1]['x1'] <= GAP:
                    sep = ' ' if c[0] - cells[-1]['x1'] > 1.0 else ''
                    cells[-1]['t'] += sep + c[4]; cells[-1]['x1'] = c[2]
                else:
                    cells.append({'x0': c[0], 'x1': c[2], 't': c[4]})
            out_lines.append({'y': y, 'cells': cells})
        res[pg] = out_lines
    return res

if __name__ == '__main__':
    import sys
    pl = page_lines(sys.argv[1])
    for pg in sorted(pl):
        if len(sys.argv) > 2 and pg != int(sys.argv[2]): continue
        print('=== PAGE', pg)
        for L in pl[pg]:
            print(f"{L['y']:6.1f} " + ' | '.join(f"{c['t']}@{c['x1']:.0f}" for c in L['cells']))
