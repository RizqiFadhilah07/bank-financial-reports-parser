import argparse
import calendar
import re
from datetime import date
from pathlib import Path

DOWNLOADS = Path(__file__).resolve().parent / "downloads"

BANK_CODE_TO_NAME = {
    "BCA": "BCA",
    "Mandiri": "Mandiri",
    "BSI": "BSI",
    "CIMB": "CIMB Niaga",
    "OCBC": "OCBC",
    "Mega": "Bank Mega",
    "Aladin": "Aladin",
    "BTPN": "BTPN Syariah",
    "UOB": "UOB",
    "BNI": "BNI",
    "BTN": "BTN",
    "BSN": "Bank Syariah Nasional",
    "MegaSyariah": "Bank Mega Syariah",
}

MONTHS = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11,
    "desember": 12,
}

FILENAME_RE = re.compile(r"-(?P<month>[a-z]+)-(?P<year>20\d{2})\.pdf$", re.IGNORECASE)

def period_from_filename(filename):
    m = FILENAME_RE.search(filename)
    if not m:
        return None
    month = MONTHS.get(m.group("month").lower())
    if month is None:
        return None
    year = int(m.group("year"))
    return date(year, month, calendar.monthrange(year, month)[1])

def scan(download_dir=DOWNLOADS):
    found, unreadable = [], []
    for folder in sorted(p for p in Path(download_dir).iterdir() if p.is_dir()):
        for pdf in sorted(folder.glob("*.pdf")):
            period = period_from_filename(pdf.name)
            if period is None:
                unreadable.append(f"{folder.name}/{pdf.name}")
            else:
                found.append((folder.name, pdf.name, period))

    return found, unreadable

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="tulis ke database")
    ap.add_argument("--month", help="filter satu bulan, contoh: 2026-05")
    ap.add_argument("--bank", help="filter satu bank, contoh: BCA")
    args = ap.parse_args()
 
    from db import get_connection   # impor di sini agar fungsi di atas bisa diuji tanpa DB
 
    found, unreadable = scan()
    if args.month:
        found = [f for f in found if f[2].strftime("%Y-%m") == args.month]
 
    if args.bank:
        found = [f for f in found if f[0].lower() == args.bank.lower()]

    if args.bank and not found:
        print(f"Tidak ada file untuk bank '{args.bank}'. Pilihan bank yang tersedia : {sorted(BANK_CODE_TO_NAME)}")
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT bank_name, bank_id, period_type FROM banks")
    banks = {name: (bid, ptype) for name, bid, ptype in cur.fetchall()}
 
    stats = {}     
    tanpa_mapping, tanpa_bank = set(), set()
 
    for code, filename, period in found:
        name = BANK_CODE_TO_NAME.get(code)
        if name is None:
            tanpa_mapping.add(code)
            continue
        if name not in banks:
            tanpa_bank.add(name)
            continue
        bank_id, period_type = banks[name]
        # format sama dengan data lama: relatif terhadap folder parsers/
        file_path = f"../downloads/{code}/{filename}"
 
        cur.execute(
            "SELECT status FROM financial_reports WHERE bank_id = %s AND period_date = %s",
            (bank_id, period),
        )
        existing = cur.fetchone()
        s = stats.setdefault(code, {"baru": 0, "sudah": 0})
        if existing:
            s["sudah"] += 1
            continue
 
        s["baru"] += 1
        if args.apply:
            cur.execute(
                """
                INSERT INTO financial_reports
                    (bank_id, period_date, period_type, file_path, status, downloaded_at)
                VALUES (%s, %s, %s, %s, 'downloaded', now())
                ON CONFLICT (bank_id, period_date) DO NOTHING
                """,
                (bank_id, period, period_type, file_path),
            )
        print(f"  {'DAFTAR' if args.apply else 'AKAN DIDAFTAR':14} {code:12} {period}  {filename}")
 
    if args.apply:
        conn.commit()
    conn.close()
 
    print("\nRingkasan per bank:")
    for code in sorted(stats):
        print(f"  {code:12} baru={stats[code]['baru']:3}  sudah_terdaftar={stats[code]['sudah']:3}")
    total_baru = sum(s["baru"] for s in stats.values())
    print(f"\nTotal baru: {total_baru} ({'sudah ditulis' if args.apply else 'dry-run, belum ditulis'})")
 
    if unreadable:
        print(f"\nNama file tidak terbaca ({len(unreadable)}):")
        for u in unreadable:
            print(f"  - {u}")
    if tanpa_mapping:
        print(f"\nFolder tanpa pemetaan: {sorted(tanpa_mapping)}")
    if tanpa_bank:
        print(f"Bank tidak ada di tabel banks: {sorted(tanpa_bank)}")
 
 
if __name__ == "__main__":
    main()