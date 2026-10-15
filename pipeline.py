import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARSERS = HERE / "parsers"
sys.path.append(str(HERE))
sys.path.append(str(PARSERS))
from db import get_connection
from main import process_bank

LOG_DIR = HERE / "logs"
logger = logging.getLogger("pipeline")

def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8")
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def record_error(conn,report_id, message):
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE financial_reports SET error_message = %s WHERE report_id = %s",
            (message, report_id)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Gagal mencatat error_message untuk report_id %s", report_id)
    finally:
        cur.close()


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
    setup_logging()
    conn = get_connection()
    try:
        jobs = get_pending_reports(conn)
        logger.info("%d laporan berstatus, 'downloaded'", len(jobs))
        
        berhasil, gagal = 0, []
        for report_id, bank_name, file_path, period_date in jobs:
            logger.info("Memproses report_id=%s %s %s", report_id, bank_name, period_date)
            try:
                result = process_bank(conn, bank_name, resolve_pdf(file_path), period_date, verbose=False)
                if result["gagal"]:
                    logger.warning("OK dengan %d metric yang gagal terbaca: %s %s",
                                   len(result["gagal"]), bank_name, period_date)
                    reasons = result.get("reasons", {})
                    for alias in result["gagal"]:
                        logger.warning("  - %s [%s]", alias, reasons.get(alias, "alasan tidak diketahui"))
                else:
                    logger.info("OK: %s %s (%d metric)", bank_name, period_date, result['jumlah_metric'])
                berhasil += 1
            except Exception as e:
                conn.rollback()
                record_error(conn, report_id, f"{type(e).__name__}: {e}")
                gagal.append((report_id, bank_name, str(e)))
                logger.exception("GAGAL: %s %s: %s", bank_name, period_date, e)

        logger.info("Selesai. Berhasil: %d, Gagal: %d", berhasil, len(gagal))
        for report_id, bank_name, err in gagal:
            logger.error(" - %s %s :%s", report_id, bank_name, err)
    finally:
        conn.close()
    return 1 if gagal else 0

if __name__ == "__main__":
    sys.exit(main())