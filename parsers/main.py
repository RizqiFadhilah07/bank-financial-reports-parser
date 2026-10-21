import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from db import get_connection

from pdf_reader import read_pages, clean_text
from extractor import extract_metrics
from number_utils import get_sign_type
from config import TERM_VARIANTS
from config import TERM_VARIANTS, SIGN_FLIP_PATTERNS
from diagnose import diagnose_failures, add_history_notes

MIN_TEXT_CHARS = 200

def load_lookup(cur, bank_id):
    cur.execute(
        """
        SELECT COALESCE(bmm.local_term, mm.metric_name) AS search_term,
               bmm.metric_alias,
               mm.metric_order
        FROM bank_metric_mapping bmm
        JOIN master_metrics mm ON mm.metric_alias = bmm.metric_alias
        WHERE bmm.bank_id = ? AND bmm.is_applicable = 1
        ORDER BY mm.metric_order ASC
        """,
        (bank_id,)
    )
    lookup = cur.fetchall()
    lookup.sort(key=lambda row: len(row[0]), reverse=True)
    return [(t.replace("’", "'").replace("‘", "'"), a, o) for t, a, o in lookup]


def save_results(cur, bank_id, period_date, period_type, pdf_path, results):
    cur.execute(
        "SELECT report_id FROM financial_reports WHERE bank_id = ? AND period_date = ?",
        (bank_id, period_date)
    )
    row = cur.fetchone()

    if row is None:
        cur.execute(
            """
            INSERT INTO financial_reports (bank_id, period_date, period_type, file_path, status, downloaded_at)
            VALUES (?, ?, ?, ?, 'downloaded', SYSDATETIMEOFFSET())
            """,
            (bank_id, period_date, period_type, pdf_path)
        )
        cur.execute(
            "SELECT report_id FROM financial_reports WHERE bank_id = ? AND period_date = ?",
            (bank_id, period_date)
        )
        row = cur.fetchone()

    else:
        cur.execute(
            """
            UPDATE financial_reports
            SET file_path = ?, status = 'downloaded', downloaded_at = SYSDATETIMEOFFSET()
            WHERE report_id = ?
            """,
            (pdf_path, row[0])
        )
    report_id = row[0]
    print(f"\nreport_id: {report_id}")

    cur.execute(
        "SELECT metric_alias FROM financial_data WHERE report_id = ?", (report_id,)
    )
    existing = {r[0] for r in cur.fetchall()}

    for metric_order, metric_alias, value, raw_text, sign in results:
        if metric_alias in existing:
            cur.execute(
                """
                UPDATE financial_data
                SET value = ?, sign_type = ?, raw_text = ?
                WHERE report_id = ? AND metric_alias = ?
                """,
                (value, sign, raw_text, report_id, metric_alias)
            )
        else:
            cur.execute(
                """
                INSERT INTO financial_data (report_id, bank_id, period_date, metric_alias, value, sign_type, raw_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (report_id, bank_id, period_date, metric_alias, value, sign, raw_text)
            )

    cur.execute(
        "UPDATE financial_reports SET status = 'parsed', parsed_at = SYSDATETIMEOFFSET() WHERE report_id = ?",
        (report_id,)
    )

def add_term_variants(lookup, bank_name):
    variants = TERM_VARIANTS.get(bank_name, {})
    if not variants:
        return lookup
    order_of = {alias: order for _, alias, order in lookup}
    extra = [(term, alias, order_of[alias])
             for alias, terms in variants.items() if alias in order_of
             for term in terms]
    return sorted(lookup + extra, key=lambda row: len(row[0]), reverse=True)

def apply_sign_convention(bank_name, alias, raw_text, sign):
    pattern = SIGN_FLIP_PATTERNS.get(bank_name, {}).get(alias)
    if pattern and pattern.search(raw_text):
        return "+" if sign == "-" else "-"
    return sign


def process_bank(conn, bank_name, pdf_path, period_date, verbose=True):
    cur = conn.cursor()

    cur.execute("SELECT bank_id, period_type FROM banks WHERE bank_name = ?", (bank_name,))
    result = cur.fetchone()
    if result is None:
        raise ValueError(f"Bank '{bank_name}' tidak ditemukan di tabel banks.")
    bank_id, period_type = result
    print(f"Bank ditemukan: {bank_name} | bank_id={bank_id} | period_type={period_type}")

    lookup = load_lookup(cur, bank_id)
    lookup = add_term_variants(lookup, bank_name)
    alias_label = {a: t for t, a, o in lookup}
    print(f"Metric Dictionary: {len(lookup)} metrik untuk bank ini")

    text = clean_text(read_pages(pdf_path, bank_name))
    if len(text.strip()) < MIN_TEXT_CHARS:
        raise ValueError(
            f"PDF tidak punya teks yang bisa terbaca "
            f"({len(text.strip())} karakter), kemungkinan hasil scan: {pdf_path}"
        )
    raw_results = extract_metrics(text, lookup, bank_name)

    results = [
        (order, alias, 0 if value is None else value, raw_text,
         apply_sign_convention(bank_name, alias, raw_text,
                               get_sign_type(alias, alias_label[alias], raw_text)))
        for order, alias, value, raw_text in raw_results
    ]
    results.sort(key=lambda r: r[0])

    if verbose:
        for metric_order, metric_alias, value, raw_text, sign in results:
            print(f"    {metric_alias:40}{value:>18,.0f}  {sign}   {raw_text}")

    missing = {row[1] for row in lookup} - {r[1] for r in results}
    save_results(cur, bank_id, str(period_date), period_type, str(pdf_path), results)
    conn.commit()
    print("Semua data tersimpan ke financial_data.")

    reasons = {}
    if missing:
        try:
            reasons = diagnose_failures(text, lookup, sorted(missing))
            reasons = add_history_notes(cur, bank_id, period_date, reasons)
        except Exception as e:
            conn.rollback()
            reasons = {}
            print(f"Peringatan: diagnosa alasan gagal ({type(e).__name__}: {e})")
        print(f"\n{len(missing)} metric gagal terbaca")
    for alias in sorted(missing):
            print(f"    -{alias}  [{reasons.get(alias, 'alasan tidak diketahui')}]")
    cur.close()
    return {"jumlah_metric": len(results), "gagal": sorted(missing), "reasons": reasons}


def main():
    ap = argparse.ArgumentParser(description="Parse laporan bulanan satu bank")
    ap.add_argument("--bank", required=True, help='contoh: "Bank Syariah Nasional"')
    ap.add_argument("--pdf", required=True, help="path PDF, contoh: ../downloads/BSN/laporan.pdf")
    ap.add_argument("--period", required=True, help="contoh: 2026-05-31")
    args = ap.parse_args()

    conn = get_connection()
    try:
        process_bank(conn, args.bank, args.pdf, args.period)
    finally:
        conn.close()


if __name__ == "__main__":
    main()