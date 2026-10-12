import argparse
import logging
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
from db import get_connection

LOG_DIR = HERE / "logs"
logger = logging.getLogger("validate")

eligible_metric = {
    ("UOB", "minority_interest"): date(2026, 7, 31),
    ("UOB", "profit_loss_transfer_to_head_office"): date(2026, 7, 31),
    ("UOB", "total_equity_attributable_to_owners"): date(2026, 7, 31),
}

LAPORAN_TIDAK_TERBACA = {
    ("Bank Mega Syariah", date(2026, 1, 31)): "PDF hasil scan, 0 karakter teks (report_id 781)",
}

SIGNED = "value * (CASE sign_type WHEN '-' THEN -1 ELSE 1 END)"

SQL_NERACA = """
WITH n AS (
    SELECT report_id, bank_id, period_date,
        MAX(CASE WHEN metric_alias = 'total_assets' THEN value END) as aset,
        MAX(CASE WHEN metric_alias = 'total_liabilities_and_equity' THEN value END) as pasiva
    FROM financial_data
    WHERE (%(p)s IS NULL OR period_date = %(p)s)
    GROUP BY report_id, bank_id, period_date
)
SELECT b.bank_name, n.period_date,
    'aset=' || COALESCE(n.aset::text, 'NULL') || ' pasiva=' || COALESCE(n.pasiva::text, 'NULL')
FROM n JOIN banks b ON b.bank_id = n.bank_id
WHERE n.aset IS NULL OR n.pasiva IS NULL OR n.aset <> n.pasiva
ORDER BY n.period_date, b.bank_name
"""


SQL_LABA = f"""
WITH s AS (
  SELECT report_id, bank_id, period_date,
    MAX(CASE WHEN metric_alias = 'profit_before_tax' THEN {SIGNED} END) AS pbt,
    MAX(CASE WHEN metric_alias = 'income_tax' THEN {SIGNED} END) AS pajak,
    MAX(CASE WHEN metric_alias = 'current_tax_expense' THEN {SIGNED} END) AS kini,
    MAX(CASE WHEN metric_alias = 'deferred_tax_income_expense' THEN {SIGNED} END) AS tangguhan,
    MAX(CASE WHEN metric_alias = 'net_profit' THEN {SIGNED} END) AS laba
  FROM financial_data
  WHERE (%(p)s IS NULL OR period_date = %(p)s)
  GROUP BY report_id, bank_id, period_date
), t AS (
  SELECT *, CASE WHEN COALESCE(pajak, 0) <> 0 THEN pajak
                 ELSE COALESCE(kini, 0) + COALESCE(tangguhan, 0) END AS pajak_total
  FROM s
)
SELECT b.bank_name, t.period_date,
       'pbt=' || COALESCE(t.pbt::text, 'NULL') || ' pajak=' || t.pajak_total::text
       || ' laba=' || COALESCE(t.laba::text, 'NULL')
FROM t JOIN banks b ON b.bank_id = t.bank_id
WHERE t.pbt IS NULL OR t.laba IS NULL OR t.pbt + t.pajak_total <> t.laba
ORDER BY t.period_date, b.bank_name
"""

SQL_LABEL_LEAKING = """
    SELECT b.bank_name, fd.period_date, fd.metric_alias || ' | ' || fd.raw_text
    FROM financial_data fd JOIN banks b ON b.bank_id = fd.bank_id
    WHERE fd.metric_alias IN ('other_commitment_receivables','other_commitment_obligations',
        'other_accrued_income','other_contingent_receivables','other_contingent_obligations',
        'other_non_reclassifiable_oci','other_reclassifiable_oci',
        'other_additional_paid_in_capital','other_fund_distribution_income')
    AND fd.raw_text ~ '[A-Z]{5,}'
    AND (%(p)s IS NULL OR fd.period_date = %(p)s)
    ORDER BY fd.period_date, b.bank_name
"""

SQL_ELIGIBLE_METRIC = """
    SELECT b.bank_name, fr.period_date, m.metric_alias
    FROM financial_reports fr
    JOIN banks b ON b.bank_id = fr.bank_id
    JOIN bank_metric_mapping m ON m.bank_id = fr.bank_id AND m.is_applicable = TRUE
    WHERE fr.status = 'parsed'
    AND (%(p)s IS NULL OR fr.period_date = %(p)s)
    AND NOT EXISTS (SELECT 1 FROM financial_data fd
                    WHERE fd.report_id = fr.report_id AND fd.metric_alias = m.metric_alias)
    ORDER BY b.bank_name, fr.period_date, m.metric_alias
"""

SQL_EMPTY_REPORT = """
    SELECT b.bank_name, fr.period_date, fr.status
    FROM financial_reports fr JOIN banks b ON b.bank_id = fr.bank_id
    WHERE NOT EXISTS (SELECT 1 FROM financial_data fd WHERE fd.report_id = fr.report_id)
    AND (%(p)s IS NULL OR fr.period_date = %(p)s)
    ORDER BY fr.period_date, b.bank_name
"""

def empty_report(rows):
    return [(b, p, s) for b, p, s in rows if (b, p) not in LAPORAN_TIDAK_TERBACA]

def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(LOG_DIR / "validate.log", mode="a", encoding="utf-8")
    fh.setFormatter(fmt)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.setLevel(logging.INFO)
    logger.addHandler(fh)
    logger.addHandler(ch)

def fetch(cur, sql, month):
    cur.execute(sql, {"p": month})
    return cur.fetchall()

def not_eligible_metric(rows):
    result = []
    for bank, period, alias in rows:
        start = eligible_metric.get((bank, alias))
        if start is None or period < start:
            result.append((bank, period, alias))
    return result

def main():
    ap = argparse.ArgumentParser(description="Validasi data dari financial_data")
    ap.add_argument("--month", help="filter satu periode, contoh : 2026-08-31")
    args = ap.parse_args()

    setup_logging()
    conn = get_connection()
    try:
        cur = conn.cursor()
        rules = [
            ("neraca", fetch(cur, SQL_NERACA, args.month)),
            ("laba", fetch(cur, SQL_LABA, args.month)),
            ("leaking_label", fetch(cur, SQL_LABEL_LEAKING, args.month)),
            ("metric_hilang", not_eligible_metric(fetch(cur, SQL_ELIGIBLE_METRIC, args.month))),
            ("laporan_kosong", empty_report(fetch(cur, SQL_EMPTY_REPORT, args.month))),
        ]
        cur.close()
    finally:
        conn.close()

    total = 0
    for nama, rows in rules:
        if not rows:
            logger.info("Approved %s", nama)
            continue
        logger.warning("Failed %s: %d temuan", nama, len(rows))
        for baris in rows:
            logger.warning("  %s", " | ".join(str(x) for x in baris))
        total += len(rows)

    logger.info("Selesai. Total temuan: %d", total)
    sys.exit(1 if total else 0)

if __name__ == "__main__":
    main()