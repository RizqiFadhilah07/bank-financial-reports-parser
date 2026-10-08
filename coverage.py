import argparse
from datetime import date

from register_downloads import scan, BANK_CODE_TO_NAME

QUARTER_END_MONTHS = {3,6,9,12}

QUARTER_GAP_BANKS = {
    "BCA", "BNI", "BSI", "BSN", "BTN", "BTPN", "Mega", "MegaSyariah", "OCBC", "UOB"
}

def default_until(today=None):
    today = today or date.today()
    if today.month == 1:
        return today.year -1, 12
    return today.year, today.month -1


def last_month_for_year(year, until):
    until_year, until_month = until
    if until_year < year:
        return 12
    if until_year == year:
        return until_month
    return 0


def classify_missing(code, missing_months):
    normal, check = [], []
    for month in missing_months:
        if month in QUARTER_END_MONTHS and code in QUARTER_GAP_BANKS:
            normal.append(month)
        else:
            check.append(month)
    return normal, check


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=date.today().year)
    ap.add_argument("--until", help="bulan terakhir yang diperiksa, contoh : 2026-09")
    args = ap.parse_args()

    if args.until:
        y,m = args.until.split("-")
        until = (int(y), int(m))
    else:
        until = default_until()

    last_month = last_month_for_year(args.year, until)
    if last_month == 0:
        print(f"Tidak ada bulan yang diperiksa untuk tahun {args.year}.")
        return

    found, unreadable = scan()
    have = {(code, period.year, period.month) for code, _name, period in found}

    months = list(range(1, last_month + 1))
    print(f"Tahun {args.year}, bulan 1-{last_month}   (Y = ada file, . = tidak ada)\n")
    print("Bank".ljust(14) + " ".join(f"{m:02d}" for m in months))

    summary = []
    for code in sorted(BANK_CODE_TO_NAME):
        marks = ["Y " if (code, args.year, m) in have else ". " for m in months]
        print(code.ljust(14) + "".join(marks).rstrip())
        missing = [m for m in months if (code, args.year, m) not in have]
        summary.append((code, *classify_missing(code, missing)))

    print("\nCelah per bank:")
    for code, normal, check in summary:
        if not normal and not check:
            print(f"    {code:12} lengkap")
            continue
        parts = []
        if normal:
            parts.append(f"normal (triwulan): {normal}")
        if check:
            parts.append(f"PERIKSA: {check}")
        print(f"  {code:12} " + " | ".join(parts))

        if not QUARTER_GAP_BANKS:
            print("\nCatatan: QUARTER_GAP_BANKS masih kosong, jadi semua celah ditandai PERIKSA.")
            print("Isi daftar itu dengan bank yang memang tidak punya laporan bulanan di bulan 3/6/9/12.")
 
 
if __name__ == "__main__":
    main()

