from patterns import build_pattern
from extractor import _is_acceptable


def diagnose_failures(text, lookup, failed_aliases):
    reasons = {}
    for alias in failed_aliases:
        terms = [t for t, a, o in lookup if a == alias]
        accepted = 0
        rejected = 0
        for term in terms:
            for cand in build_pattern(term).finditer(text):
                if _is_acceptable(text, cand):
                    accepted += 1
                else:
                    rejected += 1
        if accepted:
            reasons[alias] = "label ada di teks, tetapi nilai tidak terbaca"
        elif rejected:
            reasons[alias] = "label hanya muncul di posisi yang ditolak filter"
        else:
            reasons[alias] = "label persis tidak ditemukan di teks PDF"
    return reasons


def add_history_notes(cur, bank_id, period_date, reasons):
    if not reasons:
        return reasons
    period = str(period_date)
    placeholders = ",".join("?" * len(reasons))
    cur.execute(
        f"""
        SELECT metric_alias, MAX(period_date)
        FROM financial_data
        WHERE bank_id = ? AND period_date < ? AND metric_alias IN ({placeholders})
        GROUP BY metric_alias
        """,
        (bank_id, period, *reasons)
    )
    last_seen = {alias: last_date for alias, last_date in cur.fetchall()}

    cur.execute(
        """
        SELECT CASE WHEN EXISTS (
            SELECT 1 FROM financial_data WHERE bank_id = ? AND period_date < ?
        ) THEN 1 ELSE 0 END
        """,
        (bank_id, period)
    )
    has_history = cur.fetchone()[0]

    for alias in reasons:
        if alias in last_seen:
            note = f"terbaca terakhir {last_seen[alias]}, kemungkinan format berubah"
        elif has_history:
            note = "belum pernah terbaca di bulan sebelumnya, kemungkinan memang tidak ada di dalam PDF"
        else:
            note = "tidak ada data bulan sebelumnya sebagai pembanding"
        reasons[alias] += f"; {note}"
    return reasons