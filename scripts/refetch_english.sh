#!/bin/bash
# Replace bulletins published in English under the French filename (parser finds 0 rows)
# with the French version from the bfin archive. usage: refetch_english.sh  (after build.py)
cd "$(dirname "$0")/.."
awk -F, 'NR>1 && $5==0 {print $2}' data/bulletins.csv | tr -d '\r' | while read base; do
  ymd=$(echo "$base" | grep -oE '[0-9]{8}')
  [[ "$base" == *_bfin ]] && { echo "already bfin: $base"; continue; }
  code=$(curl -sL -A "Mozilla/5.0" -m 90 -o "pdf/tmp_$ymd.pdf" -w "%{http_code}" "https://bfin.brvm.org/boc/BOC_JOUR/BOC_${ymd}.pdf")
  if [[ $code == 200 ]] && head -c 4 "pdf/tmp_$ymd.pdf" | grep -q "%PDF"; then
    mkdir -p pdf/english; mv "pdf/$base.pdf" pdf/english/; mv "pdf/tmp_$ymd.pdf" "pdf/boc_${ymd}_bfin.pdf"; echo "replaced $base"
  else
    rm -f "pdf/tmp_$ymd.pdf"; echo "no bfin for $base"
  fi
done
