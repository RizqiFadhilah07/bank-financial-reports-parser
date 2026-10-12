import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from db import get_connection

from pdf_reader import read_pages, clean_text
from extractor import extract_metrics
from number_utils import get_sign_type
from config import TERM_VARIANTS


def load_lookup(cur, bank_id):
    cur.execute(
        """
        SELECT COALESCE(bmm.local_term, mm.metric_name) AS search_term,
               bmm.metric_alias,
               mm.metric_order
        FROM bank_metric_mapping bmm
        JOIN master_metrics mm ON mm.metric_alias = bmm.metric_alias
        WHERE bmm.bank_id = %s AND bmm.is_applicable = TRUE
        ORDER BY mm.metric_order ASC
        """,
        (bank_id,)
    )
    lookup = cur.fetchall()
    lookup.sort(key=lambda row: len(row[0]), reverse=True)
    return [(t.replace("’", "'").replace("‘", "'"), a, o) for t, a, o in lookup]


def save_results(cur, bank_id, period_date, period_type, pdf_path, results):
    cur.execute(
        """
        INSERT INTO financial_reports (bank_id, period_date, period_type, file_path, status, downloaded_at)
        VALUES (%s, %s, %s, %s, 'downloaded', now())
        ON CONFLICT (bank_id, period_date) DO UPDATE
            SET file_path = EXCLUDED.file_path, status = 'downloaded', downloaded_at = now()
        RETURNING report_id
        """,
        (bank_id, period_date, period_type, pdf_path)
    )
    report_id = cur.fetchone()[0]
    print(f"\nreport_id: {report_id}")

    for metric_order, metric_alias, value, raw_text, sign in results:
        cur.execute(
            """
            INSERT INTO financial_data (report_id, bank_id, period_date, metric_alias, value, sign_type, raw_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (report_id, metric_alias) DO UPDATE
                SET value = EXCLUDED.value,
                    sign_type = EXCLUDED.sign_type,
                    raw_text = EXCLUDED.raw_text,
                    updated_at = now()
            """,
            (report_id, bank_id, period_date, metric_alias, value, sign, raw_text)
        )

    cur.execute(
        "UPDATE financial_reports SET status = 'parsed', parsed_at = now() WHERE report_id = %s",
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


def process_bank(conn, bank_name, pdf_path, period_date, verbose=True):
    cur = conn.cursor()

    cur.execute("SELECT bank_id, period_type FROM banks WHERE bank_name = %s", (bank_name,))
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
    raw_results = extract_metrics(text, lookup, bank_name)

    results = [
        (order, alias, 0 if value is None else value, raw_text,
         get_sign_type(alias, alias_label[alias], raw_text))
        for order, alias, value, raw_text in raw_results
    ]
    results.sort(key=lambda r: r[0])

    if verbose:
        for metric_order, metric_alias, value, raw_text, sign in results:
            print(f"    {metric_alias:40}{value:>18,.0f}  {sign}   {raw_text}")

    missing = {row[1] for row in lookup} - {r[1] for r in results}
    if missing:
        print(f"\n{len(missing)} metrik gagal terbaca")
        for alias in sorted(missing):
            print(f"    -{alias}")

    save_results(cur, bank_id, str(period_date), period_type, str(pdf_path), results)
    conn.commit()
    cur.close()
    print("Semua data tersimpan ke financial_data.")
    return {"jumlah_metric" : len(results), "gagal" : sorted(missing)}


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