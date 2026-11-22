# Cours quotidiens des actions de la BRVM, 2015–2026

Pipeline qui transforme le **Bulletin Officiel de la Cote** (BOC) de la Bourse Régionale des Valeurs
Mobilières (BRVM, Abidjan), publié chaque jour en PDF, en tables propres et contrôlées : cours, volumes,
dividendes et ratios des 50 sociétés cotées depuis janvier 2015, plus les indices du marché.

Le dataset lui-même (environ 132 000 lignes, mis à jour chaque jour de bourse) est publié sur
[mandy](https://dataset.mandia.org/mohamedfrancissahi/brvm-cours-actions-2015-2026), sous licence
CC BY 4.0. Ce dépôt contient le code qui le produit.

## Ce que fait le pipeline

1. **Téléchargement** (`scripts/download.sh`, `scripts/fetch_one.sh`) : un PDF par jour ouvré depuis
   `brvm.org`, avec repli sur l'archive `bfin.brvm.org`. Les jours sans bulletin sont marqués
   `missing_AAAAMMJJ` et retentés pendant 30 jours.
2. **Extraction** (`scripts/pdfchars.swift`, `scripts/lines.py`) : position de chaque caractère dans le
   PDF via PDFKit, puis regroupement en lignes et en cellules.
3. **Lecture des tableaux** (`scripts/parse_boc.py`, `scripts/parse_indices.py`) : chaque colonne est
   identifiée par son en-tête, ce qui permet de suivre les trois mises en page successives du bulletin
   (2015–2017, 2018–2022, 2023 et après). Le résultat de chaque PDF est mis en cache : une mise à jour
   ne relit que les nouveaux bulletins.
4. **Assemblage** (`scripts/build.py`) : `data/raw_actions.csv`, `data/raw_indices.csv`,
   `data/bulletins.csv`, `data/parse_issues.txt`.
5. **Contrôles** (`scripts/validate.py`, `scripts/crosscheck_sika.py`) :
   - nombre de sociétés extraites comparé au nombre imprimé dans le bulletin (100 % de concordance) ;
   - montant ÷ volume compris entre les cours du jour ;
   - variation publiée comparée à la variation recalculée, cours précédent comparé à la référence de la
     veille ;
   - contrôle croisé externe avec sikafinance.com (99,5 % d'accord sur 20 623 rendements journaliers).
6. **Publication** (`scripts/make_dataset.py`) : noms, pays et secteurs harmonisés sur toute la période,
   tables finales dans `data/publish/`.

`scripts/update_daily.sh` enchaîne ces étapes ; il tourne chaque soir de bourse.

## Utilisation

Prérequis : macOS (l'extraction utilise PDFKit) et Python 3.11, sans dépendance externe.

```sh
swiftc -O scripts/pdfchars.swift -o scripts/pdfchars    # une fois
./scripts/download.sh 2015-01-01 2026-11-20             # ~3 Go de PDF
python3 scripts/build.py
python3 scripts/validate.py
python3 scripts/make_dataset.py                          # -> data/publish/
```

Mise à jour incrémentale : `./scripts/update_daily.sh`.

## Limites connues

- **Prix non ajustés** : pas de correction pour les divisions d'actions ni pour les dividendes. Repérer
  les sauts où `cours_precedent` diffère de la référence de la veille avant de calculer des rendements.
- **Quelques bulletins introuvables** (15 sur la période), et une colonne illisible le 16/11/2017.
- Les données sont reprises telles que publiées, coquilles comprises. Les écarts détectés sont listés
  dans `controles_qualite.csv`.

## Licences

Code : MIT (voir `LICENSE`). Données : CC BY 4.0, source BRVM (Bulletin Officiel de la Cote).
