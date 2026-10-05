import re
from config import SECTION_WINDOW


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


def find_section_anchored(section_header, sub_term, text):
    sec_pattern = build_pattern(section_header)
    m_sec = sec_pattern.search(text)
    if not m_sec:
        return None

    window_start = m_sec.end()
    window = text[window_start:window_start + SECTION_WINDOW]

    term_pattern = build_pattern_tolerant(sub_term)
    for m_term in term_pattern.finditer(window):
        abs_start = window_start + m_term.start()
        abs_end = window_start + m_term.end()
        before = text[max(0, abs_start - 20):abs_start]
        if re.search(r"(komprehensif|instrumen)\s*$", before, re.IGNORECASE):
            continue
        return abs_start, abs_end
    return None


def find_lettered_subitem(section_header, ordinal, source_text, skip_aggregate=True):
    sec_pattern = build_pattern(section_header)
    m_sec = sec_pattern.search(source_text)
    if not m_sec:
        return None
    window = source_text[m_sec.end():m_sec.end() + SECTION_WINDOW]

    if skip_aggregate:
        agg_match = re.match(r"\s*(\(?-?\d[\d.,]*\)?|-)(?!\))", window)
        remainder = window[agg_match.end():] if agg_match else window
    else:
        remainder = window

    tokens = re.findall(r"(?<![\w.])(\(?-?\d[\d.,]*\)?|-)(?!\))", remainder)
    if len(tokens) < ordinal:
        return None
    return tokens[ordinal - 1]