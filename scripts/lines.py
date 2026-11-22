"""Turn PDFKit char dump into lines of cells (cell = run of chars separated by gaps > GAP pt)."""
import subprocess, collections
GAP = 3.5
BIN = __file__.rsplit('/',1)[0] + '/pdfchars'

def page_lines(pdf):
    out = subprocess.run([BIN, pdf], capture_output=True, text=True).stdout
    pages = collections.defaultdict(list)
    for l in out.split('\n'):
        p = l.split('\t')
        if len(p) < 6: continue
        pages[int(p[0])].append((float(p[1]), float(p[2]), float(p[3]), float(p[4]), p[5]))
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
