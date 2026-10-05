import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parents[0]))
from db import get_connection

from main import process_bank


def resolve_pdf(file_path):
    p = Path(file_path)
    if p.is_absolute():
        return p
    return (HERE / p).resolve()


def main():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.bank_name, fr.file_path, fr.period_date
        FROM financial_reports fr
        JOIN banks b ON b.bank_id = fr.bank_id
        WHERE fr.status = 'parsed'
        ORDER BY fr.report_id
        """
    )
    jobs = cur.fetchall()
    cur.close()
    print(f"{len(jobs)} report akan dijalankan ulang\n")

    gagal = []
    for bank_name, file_path, period_date in jobs:
        print("=" * 70)
        try:
            process_bank(conn, bank_name, resolve_pdf(file_path), period_date, verbose=False)
        except Exception as e:
            conn.rollback()
            gagal.append((bank_name, str(e)))
            print(f"GAGAL: {bank_name}: {e}")

    conn.close()
    print("\n" + "=" * 70)
    print(f"Selesai. Berhasil: {len(jobs) - len(gagal)}, gagal: {len(gagal)}")
    for bank_name, err in gagal:
        print(f"  - {bank_name}: {err}")


if __name__ == "__main__":
    main()