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