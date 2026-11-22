"""Comparaison PDFKit (cache/pages) vs PyMuPDF sur un échantillon de bulletins."""
import glob, json, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def chars_mupdf(pdf):
    doc = pymupdf.open(pdf)
    out = []
    for pno, page in enumerate(doc, start=1):
        H = page.rect.height
        raw = page.get_text("rawdict")
        for b in raw["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    for c in s["chars"]:
                        ch = c["c"]
                        if not ch.strip():
                            continue
                        x0, y0, x1, y1 = c["bbox"]
                        out.append((pno, round(x0, 1), round(H - y1, 1), round(x1, 1), round(H - y0, 1), ch))
    return out


if __name__ == '__main__':
    files = sorted(glob.glob(os.path.join(ROOT, 'pdf', 'boc_*.pdf')))
    random.seed(0)
    sample = [files[0], files[-1]] + random.sample(files, 8)
    for f in sample:
        base = os.path.basename(f)[:-4]
        pp = os.path.join(ROOT, 'cache', 'pages', base + '.json')
        if not os.path.exists(pp):
            print(base, 'pas de cache'); continue
        ref = json.load(open(pp))
        mu = chars_mupdf(f)
        # recompose texte page 1 de la ref
        nref = sum(len(c['t'].replace(' ', '')) for L in ref.get('1', []) for c in L['cells'])
        nmu = sum(1 for c in mu if c[0] == 1)
        ref_ys = sorted({round(L['y']) for L in ref.get('1', [])})[:5]
        mu1 = [c for c in mu if c[0] == 1]
        mu_ys = sorted({round(c[4]) for c in mu1})[:5]
        first_ref = ref['1'][0]['cells'][0] if ref.get('1') else None
        print(base, 'chars p1 ref', nref, 'mupdf', nmu, '| y ref', ref_ys, 'mupdf', mu_ys, '| 1re cellule', first_ref)
