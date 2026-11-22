#!/bin/bash
# usage: fetch_one.sh YYYYMMDD  (run from repo root)
# Sources: www.brvm.org/sites/default/files/boc_YYYYMMDD[_2].pdf, then bfin.brvm.org/boc/BOC_JOUR/BOC_YYYYMMDD.pdf (archive from 2015)
ymd="$1"
ls pdf/boc_${ymd}*.pdf >/dev/null 2>&1 && exit 0
[[ -f pdf/missing_${ymd} ]] && exit 0
try() {  # url dest
  local code
  code=$(curl -sL -A "Mozilla/5.0" -m 90 --retry 2 -o "$2.part" -w "%{http_code}" "$1")
  if [[ $code == 200 ]] && head -c 4 "$2.part" | grep -q "%PDF"; then mv "$2.part" "$2"; return 0; fi
  rm -f "$2.part"; return 1
}
for s in _2 ""; do
  try "https://www.brvm.org/sites/default/files/boc_${ymd}${s}.pdf" "pdf/boc_${ymd}${s}.pdf" && { echo "ok $ymd$s"; exit 0; }
done
try "https://bfin.brvm.org/boc/BOC_JOUR/BOC_${ymd}.pdf" "pdf/boc_${ymd}_bfin.pdf" && { echo "ok $ymd bfin"; exit 0; }
touch pdf/missing_${ymd}; echo "missing $ymd"
