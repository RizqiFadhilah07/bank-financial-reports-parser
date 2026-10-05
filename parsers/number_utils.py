import re
from config import NEGATIVE_ALIASES, NEG_RE, POS_RE, PAREN_NUM_RE


def parse_number(raw):
    raw = raw.strip()
    if not raw or raw in ("-", "-/-"):
        return None
    raw = raw.strip("()").lstrip("-")

    if re.fullmatch(r"\d{1,3}(?:,\d{3})+", raw):
        cleaned = raw.replace(",", "")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
        cleaned = raw.replace(".", "")
    elif "." in raw and "," in raw:
        cleaned = raw.replace(".", "").replace(",", ".")
    else:
        cleaned = raw

    try:
        return abs(float(cleaned))
    except ValueError:
        return None


def get_sign_type(alias, label, raw_text=""):
    if PAREN_NUM_RE.search(raw_text):
        return "-"

    if re.search(r"(?<![\w/-])-\d", raw_text):
        return "-"

    if alias in NEGATIVE_ALIASES:
        return "-"

    if "-/-" in raw_text:
        return "-"

    has_neg = bool(NEG_RE.search(label))
    has_pos = bool(POS_RE.search(label))

    if has_neg and has_pos:
        return "+"

    if has_neg:
        return "-"

    return "+"