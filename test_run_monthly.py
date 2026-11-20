from datetime import date

import pytest

from run_monthly import hitung_due


@pytest.mark.parametrize(
    "hari_ini, harapan",
    [
        (date(2026, 11, 16), date(2026, 11, 15)),
        (date(2026, 11, 20), date(2026, 11, 15)),
        (date(2026, 11, 30), date(2026, 11, 30)),
        (date(2026, 12, 3), date(2026, 11, 30)),
        (date(2026, 12, 15), date(2026, 12, 15)),
        (date(2026, 11, 15), date(2026, 11, 15)),
        (date(2026, 1, 1), date(2025, 12, 31)),
        (date(2026, 3, 5), date(2026, 2, 28)),
        (date(2028, 3, 5), date(2028, 2, 29)),
        (date(2026, 2, 28), date(2026, 2, 28)),
        (date(2028, 2, 28), date(2028, 2, 15)),
        (date(2028, 2, 29), date(2028, 2, 29)),
    ],
)
def test_hitung_due(hari_ini, harapan):
    assert hitung_due(hari_ini) == harapan