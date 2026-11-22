"""Build the publishable dataset from data/raw_*.csv -> data/publish/."""
import csv, os, collections, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'data'); P = os.path.join(D, 'publish'); os.makedirs(P, exist_ok=True)

raw = list(csv.DictReader(open(os.path.join(D, 'raw_actions.csv'))))
bulletins = {b['date']: b for b in csv.DictReader(open(os.path.join(D, 'bulletins.csv')))}

SUFFIX = {'CI': "Côte d'Ivoire", 'SN': 'Sénégal', 'BF': 'Burkina Faso', 'BN': 'Bénin', 'ML': 'Mali',
          'NG': 'Niger', 'TG': 'Togo', 'SENEGAL': 'Sénégal', 'BENIN': 'Bénin', "D'IVOIRE": "Côte d'Ivoire"}
PAYS_MANUEL = {  # tickers whose printed name has no country suffix
    'CBIBF': 'Burkina Faso', 'ORGT': 'Togo', 'ETIT': 'Togo', 'SNTS': 'Sénégal', 'SDSC': "Côte d'Ivoire",
    'BBGC': "Côte d'Ivoire", 'SVOC': "Côte d'Ivoire", 'SEMC': "Côte d'Ivoire", 'ORAC': "Côte d'Ivoire",
    'LNBB': 'Bénin', 'BICB': 'Bénin', 'SIBC': "Côte d'Ivoire", 'NSBC': "Côte d'Ivoire", 'ECOC': "Côte d'Ivoire",
    'SGBC': "Côte d'Ivoire", 'SCRC': "Côte d'Ivoire", 'TTRC': "Côte d'Ivoire", 'BOAS': 'Sénégal', 'TTLS': 'Sénégal', 'ONTBF': 'Burkina Faso', 'BOABF': 'Burkina Faso',
}
SECTEURS = {'CB': 'Consommation de base', 'CD': 'Consommation discrétionnaire', 'ENE': 'Énergie',
            'FIN': 'Services financiers', 'IND': 'Industriels', 'SPU': 'Services publics', 'TEL': 'Télécommunications',
            'AGR': 'Agriculture', 'DIS': 'Distribution', 'TRA': 'Transport', 'AUT': 'Autres secteurs'}


def pays_of(t, name):
    if t in PAYS_MANUEL: return PAYS_MANUEL[t]
    last = name.replace(')', ' ').split()[-1].upper() if name.strip() else ''
    return SUFFIX.get(last)


by_t = collections.defaultdict(list)
for r in raw: by_t[r['ticker']].append(r)
soc = {}
for t, rs in by_t.items():
    rs.sort(key=lambda r: r['date'])
    names = [r['nom'] for r in rs if r['nom']]
    name = collections.Counter(names[-60:]).most_common(1)[0][0] if names else ''
    sect = next((r['secteur_code'] for r in reversed(rs) if r['secteur_code']), '')
    soc[t] = {'ticker': t, 'societe': name, 'pays': pays_of(t, name) or '',
              'secteur_code': sect, 'secteur': SECTEURS.get(sect, ''),
              'premiere_date': rs[0]['date'], 'derniere_date': rs[-1]['date'], 'nb_seances': len(rs),
              'nb_seances_avec_echanges': sum(1 for r in rs if r['volume'] not in ('', '0', '0.0'))}

cols = ['date', 'ticker', 'societe', 'pays', 'secteur_code', 'cours_precedent', 'ouverture', 'cloture',
        'cours_moyen', 'cours_reference', 'variation_jour_pct', 'volume', 'valeur_fcfa', 'variation_annuelle_pct',
        'plus_bas_annuel', 'plus_haut_annuel', 'dividende_net', 'dividende_date', 'rendement_net_pct', 'per',
        'compartiment', 'mention', 'nom_bulletin', 'secteur_bulletin', 'section_bulletin', 'source']


def clean_num(v):
    if v in ('', None): return ''
    x = float(v)
    return str(int(x)) if x == int(x) and abs(x) < 1e15 else repr(round(x, 4))


out = []
for r in sorted(raw, key=lambda r: (r['date'], r['ticker'])):
    s = soc[r['ticker']]
    o = {'date': r['date'], 'ticker': r['ticker'], 'societe': s['societe'], 'pays': s['pays'],
         'secteur_code': s['secteur_code'], 'nom_bulletin': r['nom'], 'secteur_bulletin': r['secteur_code'],
         'section_bulletin': r['section'], 'mention': r['mention'], 'compartiment': r.get('compartiment', ''),
         'dividende_date': r['dividende_date'], 'source': bulletins[r['date']]['file'] + '.pdf'}
    for k in ['cours_precedent', 'ouverture', 'cloture', 'cours_moyen', 'cours_reference', 'variation_jour_pct',
              'volume', 'variation_annuelle_pct', 'plus_bas_annuel', 'plus_haut_annuel', 'dividende_net',
              'rendement_net_pct', 'per']:
        o[k] = clean_num(r.get(k, ''))
    o['valeur_fcfa'] = clean_num(r['valeur'])
    out.append(o)
with open(os.path.join(P, 'brvm_cours_actions.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, cols, lineterminator='\n'); w.writeheader(); w.writerows(out)

scol = ['ticker', 'societe', 'pays', 'secteur_code', 'secteur', 'premiere_date', 'derniere_date', 'nb_seances',
        'nb_seances_avec_echanges']
with open(os.path.join(P, 'brvm_societes.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, scol, lineterminator='\n'); w.writeheader(); w.writerows(sorted(soc.values(), key=lambda s: s['ticker']))

idx = list(csv.DictReader(open(os.path.join(D, 'raw_indices.csv'))))
icols = ['date', 'indice', 'valeur', 'variation_jour_pct', 'variation_annuelle_pct', 'nb_societes', 'volume',
         'valeur_echangee', 'per_moyen']
with open(os.path.join(P, 'brvm_indices.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, icols, lineterminator='\n'); w.writeheader()
    for r in idx:
        w.writerow({k: (clean_num(r[k]) if k not in ('date', 'indice') else r[k]) for k in icols})

print(len(out), 'lignes actions,', len(soc), 'sociétés,', len(idx), 'lignes indices')
print('sans pays:', [t for t, s in soc.items() if not s['pays']])
