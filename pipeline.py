import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARSERS = HERE / "parsers"
sys.path.append(str(HERE))
sys.path.append(str(PARSERS))
from db import get_connection
from main import process_bank

def get_pending_reports(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT fr.report_id, b.bank_name, fr.file_path, fr.period_date
        FROM financial_reports fr
        JOIN banks b
        ON b.bank_id = fr.bank_id
        WHERE fr.status = 'downloaded'
        ORDER BY fr.period_date, fr.report_id
        """
    )
    rows = cur.fetchall()
    cur.close()
    return rows

def resolve_pdf(file_path):
    p = Path(file_path)
    if p.is_absolute():
        return p
    return (PARSERS / p).resolve()


def main():
    conn = get_connection()
    try:
        jobs = get_pending_reports(conn)
        print(f"{len(jobs)} laporan berstatus 'downloaded'")
        
        berhasil, gagal = 0, []
        for report_id, bank_name, file_path, period_date in jobs:
            print("=" * 70)
            print(f"Memproses report_id={report_id} {bank_name} {period_date}")
            try:
                process_bank(conn, bank_name, resolve_pdf(file_path),
                            period_date, verbose=False)
                berhasil += 1
            except Exception as e:
                conn.rollback()
                gagal.append((report_id, bank_name, str(e)))
                print(f"GAGAL: {bank_name}: {e}")

        print("=" * 70)
        print(f"Selesai.    Berhasil: {berhasil}, Gagal: {len(gagal)}")
        for report_id, bank_name, err in gagal:
            print(f" - {report_id} {bank_name}: {err}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()