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


def extract_metrics(text, lookup, bank_name):
    """Fase 1: logika dipindah persis dari parsing.py.

    Mengembalikan list of (metric_order, metric_alias, value, raw_text).
    value bisa None (akan diubah jadi 0 di main).
    """
    results = []
    matched_aliases = set()

    # ---------- Metric dengan Special Case ----------
    for metric_alias, section_header in SECTION_ANCHORED_METRICS.items():
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

    pure_header_metrics = PURE_HEADER_METRICS.get(bank_name, set())

    # ---------- Metric Normal ----------
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

            value_match = re.search(r"\(?-?\d[\d.,]*\)?|-", matched_text)

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
            text = text[:span_start] + (" " * (span_end - span_start)) + text[span_end:]
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
        if metric_alias in SECTION_HEADER_METRICS:
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

    # ---------- Fallback sub-item bernomor huruf ----------
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

    return results