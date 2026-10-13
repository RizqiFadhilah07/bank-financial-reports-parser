import re
from config import (
    NUMBER_RE, SECTION_ANCHORED_METRICS, LETTERED_SUBITEM_FALLBACK,
    PURE_HEADER_METRICS, DEFER_TO_FALLBACK_IF_EMPTY, SECTION_HEADER_METRICS,
)
from number_utils import parse_number
from patterns import (
    build_pattern, build_fuzzy_pattern, build_interrupted_pattern,
    find_section_anchored, find_lettered_subitem,
)


# Helper kecil

def blank_out(text, start, end):
    return text[:start] + (" " * (end - start)) + text[end:]


def _is_acceptable(text, cand):
    before = text[max(0, cand.start() - 4):cand.start()].lower()
    if before == 'dan ':
        return False
    if re.search(r"\bbank\s*$", text[max(0, cand.start() - 8):cand.start()], re.IGNORECASE):
        return False
    return True


def find_match(search_term, text):
    for cand in build_pattern(search_term).finditer(text):
        if _is_acceptable(text, cand):
            return cand, False

    for cand in build_fuzzy_pattern(search_term).finditer(text):
        if _is_acceptable(text, cand):
            return cand, False

    for pattern in build_interrupted_pattern(search_term):
        for cand in pattern.finditer(text):
            if _is_acceptable(text, cand):
                return cand, True

    return None, False


def empty_marker(after, alias):
    no_match = re.match(r"\s*-(?!/|\d)", after)
    if alias in SECTION_HEADER_METRICS:
        list_item_match = re.match(
            r"\s*\d{1,2}(?:"
            r"\.(?!\d)"
            r"|(?![\d.,])(?=\s+(?:[A-Za-z]|\d{1,2}(?![\d.,]))|\s*$)"
            r")",
            after
        )
    else:
        list_item_match = re.match(r"\s*\d{1,2}\.(?!\d)", after)
    return no_match or list_item_match


def value_from_interrupted(matched_text):
    value_match = re.search(r"\(?-?\d[\d.,]*\)?|-", matched_text)
    if not value_match:
        return None
    raw_value = value_match.group(0)
    if raw_value == "-":
        return None
    return parse_number(raw_value)



# metrik section-anchored

def extract_section_anchored(text, lookup, results, matched):
    for alias, section_header in SECTION_ANCHORED_METRICS.items():
        match_row = next((row for row in lookup if row[1] == alias), None)
        if match_row is None:
            continue
        search_term, _, order = match_row

        pos = find_section_anchored(section_header, search_term, text)
        if pos is None:
            continue
        m_start, m_end = pos

        after = text[m_end:m_end + 40]

        marker = empty_marker(after, alias)
        if marker:
            span_end = m_end + marker.end()
            results.append((order, alias, None, text[m_start:span_end].strip()))
            matched.add(alias)
            text = blank_out(text, m_start, span_end)
            continue

        vm = NUMBER_RE.search(after)
        if not vm:
            continue

        if re.search(r"[A-Za-z]", after[:vm.start()]):
            results.append((order, alias, None, text[m_start:m_end].strip()))
            matched.add(alias)
            text = blank_out(text, m_start, m_end)
            continue
            
        value = parse_number(vm.group(0))
        if value is None:
            continue

        span_end = m_end + vm.end()
        results.append((order, alias, value, text[m_start:span_end].strip()))
        matched.add(alias)
        text = blank_out(text, m_start, span_end)

    return text


# metrik normal

def extract_one_metric(text, search_term, alias, order, pure_headers):
    m, is_interrupted = find_match(search_term, text)
    if m is None:
        return None, text

    if is_interrupted:
        value = value_from_interrupted(m.group(0))
        entry = (order, alias, value, m.group(0).strip())
        return entry, blank_out(text, m.start(), m.end())

    after = text[m.end():m.end() + 40]
    base_end = m.end()

    dash_prefix = re.match(r"\s*\(?\s*-\s*/\s*-(?:\s*\))?", after)
    if dash_prefix:
        base_end = m.end() + dash_prefix.end()
        after = text[base_end:base_end + 40]

    if alias in pure_headers:
        entry = (order, alias, None, text[m.start():base_end].strip())
        return entry, blank_out(text, m.start(), base_end)

    if alias in DEFER_TO_FALLBACK_IF_EMPTY and not re.search(r"\d", after):
        return None, text

    marker = empty_marker(after, alias)
    if marker:
        span_end = base_end + marker.end()
        entry = (order, alias, None, text[m.start():span_end].strip())
        return entry, blank_out(text, m.start(), span_end)

    if not re.match(r"[\d(]", after.lstrip()):
        entry = (order, alias, None, text[m.start():base_end].strip())
        return entry, blank_out(text, m.start(), base_end)

    # Ada angka
    vm = NUMBER_RE.search(after)
    if not vm:
        return None, text
    value = parse_number(vm.group(0))
    if value is None:
        return None, text

    span_end = base_end + vm.end()
    entry = (order, alias, value, text[m.start():span_end].strip())
    return entry, blank_out(text, m.start(), span_end)


def extract_normal(text, lookup, bank_name, results, matched):
    pure_headers = PURE_HEADER_METRICS.get(bank_name, set())

    for search_term, alias, order in lookup:
        if alias in matched:
            continue
        entry, text = extract_one_metric(text, search_term, alias, order, pure_headers)
        if entry is not None:
            results.append(entry)
            matched.add(alias)

    return text


# fallback sub-item bernomor huruf

def extract_fallback(snapshot, lookup, results, matched):
    for alias, (section_header, ordinal, skip_agg) in LETTERED_SUBITEM_FALLBACK.items():
        if alias in matched:
            continue
        match_row = next((row for row in lookup if row[1] == alias), None)
        if match_row is None:
            continue
        _, _, order = match_row

        raw = find_lettered_subitem(section_header, ordinal, snapshot, skip_agg)
        if raw is None:
            continue
        value = parse_number(raw)
        raw_text = f"[fallback ordinal-{ordinal}] {section_header}: {raw}"
        results.append((order, alias, value, raw_text))
        matched.add(alias)



def extract_metrics(text, lookup, bank_name):
    results = []
    matched = set()

    text = extract_section_anchored(text, lookup, results, matched)
    snapshot = text
    extract_normal(text, lookup, bank_name, results, matched)
    extract_fallback(snapshot, lookup, results, matched)

    return results