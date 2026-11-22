"""Petits calculs de dates, identiques sur macOS, Linux et Windows (évite `date -j` / `date -d`).

    python scripts/dates.py weekdays 2026-11-01 2026-11-20   # AAAAMMJJ des jours ouvrés, un par ligne
    python scripts/dates.py shift 2026-11-20 1               # 2026-11-21
    python scripts/dates.py today                            # 2026-11-22
"""
import datetime as dt
import sys


def parse(s):
    return dt.date.fromisoformat(s)


def main(argv):
    cmd = argv[0]
    if cmd == 'weekdays':
        d, end = parse(argv[1]), parse(argv[2])
        while d <= end:
            if d.weekday() < 5:
                print(d.strftime('%Y%m%d'))
            d += dt.timedelta(days=1)
    elif cmd == 'shift':
        print(parse(argv[1]) + dt.timedelta(days=int(argv[2])))
    elif cmd == 'today':
        print(dt.date.today())
    else:
        sys.exit(f'commande inconnue : {cmd}')


if __name__ == '__main__':
    main(sys.argv[1:])
