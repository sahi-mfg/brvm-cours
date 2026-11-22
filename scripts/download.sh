#!/bin/bash
# usage: download.sh START END  (YYYY-MM-DD) ; fetch BRVM Bulletin Officiel de la Cote PDFs (weekdays)
# Naming: boc_YYYYMMDD_2.pdf (recent) or boc_YYYYMMDD.pdf (older). Non-trading days => pdf/missing_YYYYMMDD marker.
cd "$(dirname "$0")/.."
d="$1"; end="$2"
while [[ "$d" < "$end" || "$d" == "$end" ]]; do
  dow=$(date -j -f %Y-%m-%d "$d" +%u)
  [[ $dow -le 5 ]] && echo "${d//-/}"
  d=$(date -j -v+1d -f %Y-%m-%d "$d" +%Y-%m-%d)
done | xargs -P 6 -n 1 ./scripts/fetch_one.sh
