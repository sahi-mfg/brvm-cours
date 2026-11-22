#!/bin/bash
# Mise à jour quotidienne du dataset BRVM.
#   1. télécharge les bulletins manquants, du lendemain du dernier bulletin jusqu'à aujourd'hui
#   2. reconstruit les tables (le cache rend l'opération incrémentale)
#   3. relance les contrôles et la mise en forme publiable (data/publish/ et data/publish-hf/data/)
#   4. publie sur Hugging Face si un jeton est configuré (hf auth login) et HF_REPO défini
#
# Sortie : silencieuse si rien de nouveau. Une ligne de résumé s'il y a de nouvelles séances.
# Code de sortie non nul en cas d'échec : Hermes envoie alors une alerte.
set -euo pipefail
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="uv run --quiet python"
LOG="$ROOT/update.log"
HF_REPO="${HF_REPO:-ihasthetruth/brvm-cours-actions-2015-2026}"   # dataset Hugging Face publié à chaque nouvelle séance

last=$(tail -n 1 data/bulletins.csv | cut -d, -f1)
start=$($PY scripts/dates.py shift "$last" 1)
today=$($PY scripts/dates.py today)
[[ "$start" > "$today" ]] && exit 0

{
  echo "=== $(date '+%F %T') : de $start à $today"
  # Un bulletin peut manquer à cause d'une panne passagère du site (cas du 30/10/2026) ou parce
  # qu'il n'est pas encore en ligne : on retire les marqueurs « missing » des 30 derniers jours
  # et on retente toute cette période. Les jours fériés restent simplement marqués « missing ».
  since=$($PY scripts/dates.py shift "$today" -29)
  for ymd in $($PY scripts/dates.py weekdays "$since" "$today"); do rm -f "pdf/missing_$ymd"; done
  ./scripts/download.sh "$since" "$today"
} >> "$LOG" 2>&1

before=$(wc -l < data/bulletins.csv)
$PY scripts/build.py >> "$LOG" 2>&1
# Bulletins publiés en anglais sous le nom français : on les remplace par la version française.
if awk -F, 'NR>1 && $5==0 && $2 !~ /_bfin/' data/bulletins.csv | grep -q .; then
  ./scripts/refetch_english.sh >> "$LOG" 2>&1
  $PY scripts/build.py >> "$LOG" 2>&1
fi
after=$(wc -l < data/bulletins.csv)
new=$((after - before))
[[ $new -le 0 ]] && exit 0

$PY scripts/validate.py >> "$LOG" 2>&1
$PY scripts/make_dataset.py >> "$LOG" 2>&1
cp data/validation_flags.csv data/publish/controles_qualite.csv
cp data/publish/*.csv data/publish-hf/data/

last_new=$(tail -n 1 data/bulletins.csv | cut -d, -f1)
n_actions=$(tail -n 1 data/bulletins.csv | cut -d, -f5 | tr -d '\r')
new_dates=$(tail -n "$new" data/bulletins.csv | cut -d, -f1 | paste -sd'|' -)
issues=$(grep -cE "^($new_dates)" data/parse_issues.txt || true)

published="non publié (pas de dépôt HF configuré)"
if [[ -n "$HF_REPO" ]]; then
  uvx --from huggingface_hub hf upload "$HF_REPO" data/publish-hf . --repo-type dataset \
      --commit-message "Séances jusqu'au $last_new" >> "$LOG" 2>&1 \
    && published="publié sur Hugging Face" || { echo "ÉCHEC publication HF ($HF_REPO), voir $LOG"; exit 1; }
fi

echo "BRVM : +$new séance(s), dernière le $last_new ($n_actions sociétés), $issues anomalie(s) de lecture sur ces séances ; $published. Mandy : à republier à la main (data/publish/)."
