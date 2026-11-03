import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARSERS = HERE / "parsers"
if str(PARSERS) not in sys.path:
    sys.path.append(str(PARSERS))

from main import (load_lookup, add_term_variants, apply_sign_convention,
                  clean_text, read_pages, extract_metrics, get_sign_type,
                  MIN_TEXT_CHARS)

def extract_preview(conn, bank_name, pdf_file):
    cur = conn.cursor()
    cur.execute("""SELECT bank_id FROM banks WHERE bank_name = ?""", (bank_name,))
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"Bank '{bank_name}' tidak ditemukan di tabel banks.")
    bank_id = row[0]

    lookup = add_term_variants(load_lookup(cur, bank_id), bank_name)
    cur.close()
    alias_label = {a:t for t, a, o in lookup}

    text = clean_text(read_pages(pdf_file, bank_name))
    if len(text.strip()) < MIN_TEXT_CHARS:
        raise ValueError(
            f"PDF tidak punya teks yang bisa terbaca "
            f"({len(text.strip())} karakter), kemungkinan hasil scan."
        )

    results = [
        (order, alias, 0 if value is None else value, raw_text,
         apply_sign_convention(bank_name, alias, raw_text,
                               get_sign_type(alias, alias_label[alias], raw_text)))
        for order, alias, value, raw_text in extract_metrics(text, lookup, bank_name)
    ]
    results.sort(key=lambda r: r[0])
    missing = sorted({row[1] for row in lookup} - {r[1] for r in results})
    return {"results": results, "missing": missing}