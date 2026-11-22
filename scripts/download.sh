#!/bin/bash
# usage: download.sh START END  (YYYY-MM-DD) ; fetch BRVM Bulletin Officiel de la Cote PDFs (weekdays)
# Naming: boc_YYYYMMDD_2.pdf (recent) or boc_YYYYMMDD.pdf (older). Non-trading days => pdf/missing_YYYYMMDD marker.
# Works on macOS, Linux and WSL (needs bash, curl, xargs and uv).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p pdf
uv run --quiet python scripts/dates.py weekdays "$1" "$2" | xargs -P 6 -n 1 ./scripts/fetch_one.sh
