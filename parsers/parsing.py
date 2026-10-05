import re
import pdfplumber
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from db import get_connection

conn = get_connection()
cur = conn.cursor()

# FILE PATH MANUAL
PDF_PATH = "../downloads/Aladin/laporan-bulanan-Aladin-mei-2026.pdf"
BANK_NAME = "Aladin"
PERIOD_DATE = "2026-05-31"

# Cari bank_id dari nama BANK
cur.execute("SELECT bank_id, period_type FROM banks WHERE bank_name = %s", (BANK_NAME,))
result = cur.fetchone()
if result is None:
    raise ValueError(f"Bank '{BANK_NAME}' tidak ditemukan di tabel banks.")
bank_id, period_type = result
print(f"Bank ditemukan: {BANK_NAME} | bank_id={bank_id} | period_type={period_type}")


# Dictionary untuk bank (untuk bank bca apa aja metric nya)
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
lookup = [(t.replace("’", "'").replace("‘", "'"), a, o) for t, a, o in lookup]
alias_label = {a: t for t, a , o in lookup}
print(f"Metric Dictionary: {len(lookup)} metrik untuk bank ini")

# Baca pdf
TWO_COLUMN_BANKS = {"BTPN Syariah"}
SPLIT_X = 391.5

raw_pages = []
with pdfplumber.open(PDF_PATH) as pdf:
    for page in pdf.pages:
        if BANK_NAME in TWO_COLUMN_BANKS:
            left  = page.crop((0,       0, SPLIT_X,    page.height)).extract_text() or ""
            right = page.crop((SPLIT_X, 0, page.width, page.height)).extract_text() or ""
            raw_pages.append(left)
            raw_pages.append(right)
        else:
            raw_pages.append(page.extract_text() or "")

# cleaning
def fix_spaced_words(line):
    pattern = r"\b(?:[A-Za-z]\s+){2,}[A-Za-z]\b"
    previous = None
    while previous != line:
        previous = line
        line = re.sub(pattern, lambda m: m.group(0).replace(" ", ""), line)
    return line

fixed_lines = []

for page_text in raw_pages:
    for line in page_text.split("\n"):
        line = re.sub(r"^\d{2}[a-z]\s+", "", line)
        line = re.sub(r"(?<=\d)\s+(?=[\d.,])", "", line)
        line = re.sub(r"(?<=\d)\s+(?=,)", "", line)
        line = re.sub(r"(?<=,)\s+(?=\d)", "", line)
        line = re.sub(r"(?<=\()\s+(?=\d)", "", line) 
        line = fix_spaced_words(line)
        fixed_lines.append(line)

text = " ".join(fixed_lines)
text = re.sub(r"\s+", " ", text)
text = text.replace("’", "'").replace("‘", "'")

text = re.sub(
    r"\b([a-z])(?=(?:Keuntungan|Kerugian)\b)",
    r"\1 ",
    text,
    flags=re.IGNORECASE
)

# Cocokin ke teks

NUMBER_RE = re.compile(r"\(?-?\d[\d.,]*\)?")


def parse_number(raw):
    raw = raw.strip()
    if not raw or raw in ("-", "-/-"):
        return None
    raw = raw.strip("()").lstrip("-")

    if re.fullmatch(r"\d{1,3}(?:,\d{3})+",raw):
        cleaned = raw.replace(",","")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+",raw):
        cleaned = raw.replace(".","")
    elif "." in raw and "," in raw:
        cleaned = (raw.replace(".", "").replace(",","."))
    else:
        cleaned = raw

    try:
        return abs(float(cleaned))
    except ValueError:
        return None


NEG_RE = re.compile(r"\b(beban|rugi|kerugian|biaya)\b", re.IGNORECASE)
POS_RE = re.compile(r"\b(laba|keuntungan|pendapatan|penghasilan)\b", re.IGNORECASE)
PAREN_NUM_RE = re.compile(r"\(\s*\d[\d.,]*\s*\)")

def get_sign_type(alias,label, raw_text=""):

    if PAREN_NUM_RE.search(raw_text):
        return "-"

    if re.search(r"(?<![\w/-])-\d", raw_text):
        return "-"

    if alias in NEGATIVE_ALIASES:
        return "-"

    if "-/-" in raw_text:
        return "-"

    name = label.lower()
    has_neg = bool(NEG_RE.search(label))
    has_pos = bool(POS_RE.search(label))

    if has_neg and has_pos:
        return "+"

    if has_neg:
        return "-"

    return "+"


def build_pattern(term):
    parts = re.split(r"\s*/\s*", term)
    escaped_parts = [re.escape(p).replace(r"\)", r"\s*\)") for p in parts]
    body = r"(?:\s*/\s*|\s+)".join(escaped_parts)
    return re.compile(r"(?<!\w)" + body + r"(?:\s*\d+\))?(?![A-Za-z])", re.IGNORECASE)


def build_pattern_tolerant(term):
    if term.strip().lower() == "lainnya":
        return re.compile(r"(?<!\w)La\s*innya(?![A-Za-z])", re.IGNORECASE)
    return build_pattern(term)

def build_fuzzy_pattern(term):
    parts = re.split(r"\s*/\s*", term)
    result_parts = []

    for part in parts:
        chars = []
        for ch in part:
            if ch == " ":
                chars.append(r"\s*")
            else:
                chars.append(re.escape(ch))
        fuzzy = r"\s?".join(chars)
        fuzzy = fuzzy.replace(r"\)", r"\s*\)")
        result_parts.append(fuzzy)
    body = r"\s*/?\s*".join(result_parts)
    return re.compile(r"(?<!\w)" + body + r"(?!\w)", re.IGNORECASE)

def find_section_anchored(section_header, sub_term, text):
    sec_pattern = build_pattern(section_header)
    m_sec = sec_pattern.search(text)
    if not m_sec:
        return None

    window_start = m_sec.end()
    window = text[window_start:window_start + section_window]

    term_pattern = build_pattern_tolerant(sub_term)
    for m_term in term_pattern.finditer(window):
        abs_start = window_start + m_term.start()
        abs_end = window_start + m_term.end()
        before = text[max(0, abs_start - 20):abs_start]
        if re.search(r"(komprehensif|instrumen)\s*$", before, re.IGNORECASE):
            continue
        return abs_start, abs_end
    return None


def build_interrupted_pattern(term):
    words = [w for w in term.split() if w != "/"]
    patterns = []
    value_pattern = r"\s*(?:[a-z]\.?\s*)?(?:\(?-?\d[\d.,]*\)?|-)\s*"
    for i in range(1, len(words)):
        left = r"\s*".join(re.escape(w) for w in words[:i])
        right = r"\s*".join(re.escape(w) for w in words[i:])
        pattern = r"(?<!\w)" + left + value_pattern + right + r"(?!\w)"
        patterns.append(re.compile(pattern, re.IGNORECASE))
    return patterns

section_anchored_metrics = {
    "other_commitment_receivables" : "TAGIHAN KOMITMEN",
    "other_commitment_obligations" : "KEWAJIBAN KOMITMEN",
    "other_accrued_income" : "Pendapatan dalam penyelesaian",
    "other_contingent_receivables" : "TAGIHAN KONTINJENSI",
    "other_contingent_obligations" : "KEWAJIBAN KONTINJENSI",
    "other_non_reclassifiable_oci": "Pos-pos yang tidak akan direklasifikasi ke laba rugi",
    "other_reclassifiable_oci": "Pos-pos yang akan direklasifikasi ke laba rugi",
    "other_additional_paid_in_capital": "Tambahan modal disetor",
    "other_fund_distribution_income": "Pendapatan Sewa",
}


section_window = 400

NEGATIVE_ALIASES = {
    "interest_expense", "personnel_expense", "promotion_expense",
    "other_operating_expense", "impairment_loss_recovery", "operational_risk_loss",
    "wadiah_bonus_expense", "other_non_financial_asset_impairment",
    "unpaid_capital", "treasury_stock", "dividends_paid",
    "other_comprehensive_income_loss", "impairment_allowance",
    "held_securities_impairment", "loans_and_sharia_financing_impairment",
    "other_asset_impairment", "accumulated_amortization_intangible_assets",
    "accumulated_depreciation_fixed_assets", "current_tax_expense",
    "share_discount", "istishna_progress_billing", "income_tax",
    "profit_distribution_to_investment_fund_owners",
    "non_profit_sharing_distribution", "profit_sharing_distribution",
    "profit_distribution_to_investment_fund_owners",
    "non_profit_sharing_distribution",
    "profit_sharing_distribution",
}

LETTERED_SUBITEM_FALLBACK = {
    "revaluation_gain_fixed_assets": ("Pos-pos yang tidak akan direklasifikasi ke laba rugi", 1, True),
    "remeasurement_defined_benefit_gain_loss": ("Pos-pos yang tidak akan direklasifikasi ke laba rugi", 2, True),
    "foreign_currency_translation_gain_loss": ("Pos-pos yang akan direklasifikasi ke laba rugi", 1, True),
    "fair_value_oci_gain_loss": ("Pos-pos yang akan direklasifikasi ke laba rugi", 2, True),
    "current_tax_expense": ("Pajak penghasilan", 1, False),
}

PURE_HEADER_METRICS = {
    "BSI" : {"income_tax"}
}

DEFER_TO_FALLBACK_IF_EMPTY = {"current_tax_expense"}

def find_lettered_subitem(section_header, ordinal, source_text, skip_aggregate=True):
    sec_pattern = build_pattern(section_header)
    m_sec = sec_pattern.search(source_text)
    if not m_sec:
        return None
    window = source_text[m_sec.end():m_sec.end() + section_window]

    if skip_aggregate:
        agg_match = re.match(r"\s*(\(?-?\d[\d.,]*\)?|-)(?!\))", window)
        remainder = window[agg_match.end():] if agg_match else window
    else:
        remainder = window

    tokens = re.findall(r"(?<![\w.])(\(?-?\d[\d.,]*\)?|-)(?!\))", remainder)
    if len(tokens) < ordinal:
        return None
    return tokens[ordinal - 1]


results = []
matched_aliases = set()



# Metric dengan Special Case
for metric_alias, section_header in section_anchored_metrics.items():
    match_row = next((row for row in lookup if row[1] == metric_alias), None)
    if match_row is None:
        continue
    search_term, _, metric_order = match_row

    pos = find_section_anchored(section_header, search_term, text)
    if pos is None:
        continue
    m_start, m_end = pos

    after = text[m_end:m_end + 40]
    no_match = re.match(r"\s*-(?!/|\d)", after)
    list_item_match = re.match(r"\s*\d{1,2}\.(?!\d)", after)

    if no_match or list_item_match:
        cut = no_match.end() if no_match else list_item_match.end()
        raw_text = text[m_start:m_end + cut].strip()
        results.append((metric_order, metric_alias, None, raw_text))
        matched_aliases.add(metric_alias)
        span_start, span_end = m_start, m_end + cut
        text = text[:span_start] + (" " * (span_end - span_start)) + text[span_end:]
        continue

    vm = NUMBER_RE.search(after)
    if not vm:
        continue

    value = parse_number(vm.group(0))
    if value is None:
        continue

    raw_text = text[m_start:m_end + vm.end()].strip()
    results.append((metric_order, metric_alias, value, raw_text))
    matched_aliases.add(metric_alias)

    span_start, span_end = m_start, m_end + vm.end()
    text = text[:span_start] + (" " * (span_end - span_start)) + text[span_end:]

text_snapshot_for_fallback = text


# Metric Normal
for search_term, metric_alias, metric_order in lookup:
    if metric_alias in matched_aliases:
        continue

    pattern = build_pattern(search_term)

    m = None
    for cand in pattern.finditer(text):
        before = text[max(0, cand.start() - 4):cand.start()].lower()
        if before == 'dan ':
            continue
        if re.search(r"\bbank\s*$", text[max(0, cand.start() - 8):cand.start()], re.IGNORECASE):
            continue
        m = cand
        break
    interrupted_match = None
    
    if m is None:
        fuzzy_pattern = build_fuzzy_pattern(search_term)
        for cand in fuzzy_pattern.finditer(text):
            before = text[max(0, cand.start() - 4):cand.start()].lower()
            if before == 'dan ':
                continue
            if re.search(r"\bbank\s*$", text[max(0, cand.start() - 8):cand.start()], re.IGNORECASE):
                continue
            m = cand
            break

    if m is None:
        interrupted_patterns = build_interrupted_pattern(search_term)
        for interrupted_pattern in interrupted_patterns:
            for cand in interrupted_pattern.finditer(text):

                before = text[max(0, cand.start() - 4):cand.start()].lower()

                if before == 'dan ':
                    continue
                if re.search(r"\bbank\s*$", text[max(0, cand.start() - 8):cand.start()], re.IGNORECASE):
                    continue
                m = cand
                interrupted_match = cand
                break

            if m is not None:
                break

    if interrupted_match is not None:
        matched_text = interrupted_match.group(0)

        value_match = re.search(r"\(?-?\d[\d.,]*\)?|-",matched_text)

        if value_match:
            raw_value = value_match.group(0)

            if raw_value == "-":
                value = None
            else:
                value = parse_number(raw_value)
        else:
            value = None

        raw_text = matched_text.strip()

        results.append((metric_order, metric_alias, value, raw_text))

        matched_aliases.add(metric_alias)

        span_start, span_end = m.start(), m.end()

        text = (
            text[:span_start] + (" " * (span_end - span_start)) + text[span_end:]
        )

        continue

    if m is None:
            continue
    
    after = text[m.end():m.end() + 40]
    base_end = m.end()

    dash_prefix = re.match(r"\s*-\s*/\s*-", after)
    if dash_prefix:
        base_end = m.end() + dash_prefix.end()
        after = text[base_end:base_end + 40]

    after_stripped = after.lstrip()

    pure_header_metrics = PURE_HEADER_METRICS.get(BANK_NAME, set())

    if metric_alias in pure_header_metrics:
        raw_text = text[m.start():base_end].strip()
        results.append((metric_order, metric_alias, None, raw_text))
        matched_aliases.add(metric_alias)

        span_start, span_end = m.start(), base_end
        text = text[:span_start] + (" " * (span_end - span_start)) + text[span_end:]
        continue

    if metric_alias in DEFER_TO_FALLBACK_IF_EMPTY and not re.search(r"\d", after):
        continue  

    no_match = re.match(r"\s*-(?!/|\d)", after)
    section_header_metrics = {
        "commitment_receivables", "commitment_payables",
        "contingent_receivables", "contingent_payables"
    }
    if metric_alias in section_header_metrics:
        list_item_match = re.match(
            r"\s*\d{1,2}(?:"
            r"\.(?!\d)"
            r"|(?![\d.,])(?=\s+(?:[A-Za-z]|\d{1,2}(?![\d.,]))|\s*$)"
            r")",
            after
        )
    else:
        list_item_match = re.match(r"\s*\d{1,2}\.(?!\d)", after)

    if no_match or list_item_match:
        cut = no_match.end() if no_match else list_item_match.end()
        raw_text = text[m.start():base_end + cut].strip()
        results.append((metric_order, metric_alias, None, raw_text))
        matched_aliases.add(metric_alias)
        span_start, span_end = m.start(), base_end + cut
        text = text[:span_start] + (" " * (span_end - span_start)) + text[span_end:]
        continue

    if not re.match(r"[\d(]", after_stripped):
        raw_text = text[m.start():base_end].strip()
        results.append((metric_order, metric_alias, None, raw_text))
        matched_aliases.add(metric_alias)
        span_start, span_end = m.start(), base_end
        text = text[:span_start] + (" " * (span_end - span_start)) + text[span_end:]
        continue

    vm = NUMBER_RE.search(after)
    if not vm:
        continue

    value = parse_number(vm.group(0))
    if value is None:
        continue

    raw_text = text[m.start():base_end + vm.end()].strip()
    results.append((metric_order, metric_alias, value, raw_text))
    matched_aliases.add(metric_alias)

    span_start, span_end = m.start(), base_end + vm.end()
    text = text[:span_start] + (" " * (span_end - span_start)) + text[span_end:]



for metric_alias, (section_header, ordinal, skip_agg) in LETTERED_SUBITEM_FALLBACK.items():
    if metric_alias in matched_aliases:
        continue
    match_row = next((row for row in lookup if row[1] == metric_alias), None)
    if match_row is None:
        continue
    _, _, metric_order = match_row

    raw = find_lettered_subitem(section_header, ordinal, text_snapshot_for_fallback, skip_agg)
    if raw is None:
        continue
    value = parse_number(raw)
    raw_text = f"[fallback ordinal-{ordinal}] {section_header}: {raw}"
    results.append((metric_order, metric_alias, value, raw_text))
    matched_aliases.add(metric_alias)


results = [
    (order, alias, 0 if value is None else value, raw_text,
     get_sign_type(alias, alias_label[alias], raw_text))
    for order, alias, value, raw_text in results
]

# Sorting
results.sort(key=lambda r: r[0])

for metric_order, metric_alias, value, raw_text, sign in results:
    print(f"    {metric_alias:40}{value:>18,.0f}  {sign}   {raw_text}")

matched_aliases_set = {r[1] for r in results}
lookup_aliases_set = {row[1] for row in lookup}
trully_missing = lookup_aliases_set - matched_aliases_set

if trully_missing:
    print(f"\n{len(trully_missing)} metrik gagal terbaca")
    for alias in sorted(trully_missing):
        print(f"    -{alias}")



# INSERT INTO DATABASE

cur.execute(
    """
    INSERT INTO financial_reports (bank_id, period_date, period_type, file_path, status, downloaded_at)
    VALUES (%s, %s, %s, %s, 'downloaded', now())
    ON CONFLICT (bank_id, period_date) DO UPDATE
        SET file_path = EXCLUDED.file_path, status = 'downloaded', downloaded_at = now()
    RETURNING report_id
    """,
    (bank_id, PERIOD_DATE, period_type, PDF_PATH)
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
        (report_id, bank_id, PERIOD_DATE, metric_alias, value, sign, raw_text)
    )
 
cur.execute(
    "UPDATE financial_reports SET status = 'parsed', parsed_at = now() WHERE report_id = %s",
    (report_id,)
)
 
conn.commit()
cur.close()
conn.close() 
print("Semua data tersimpan ke financial_data.")