from datetime import date

import pytest

from run_monthly import baca_last_run, hitung_due, tulis_last_run


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


def test_baca_last_run_file_tidak_ada(tmp_path):
    assert baca_last_run(tmp_path / "last_run.txt") is None


def test_tulis_lalu_baca_last_run(tmp_path):
    path = tmp_path / "last_run.txt"
    tulis_last_run(path, date(2026, 11, 15))
    assert baca_last_run(path) == date(2026, 11, 15)


def test_tulis_last_run_menimpa(tmp_path):
    path = tmp_path / "last_run.txt"
    tulis_last_run(path, date(2026, 10, 31))
    tulis_last_run(path, date(2026, 11, 15))
    assert baca_last_run(path) == date(2026, 11, 15)


def test_baca_last_run_isi_rusak(tmp_path):
    path = tmp_path / "last_run.txt"
    path.write_text("bukan tanggal", encoding="utf-8")
    assert baca_last_run(path) is None


def test_baca_last_run_file_kosong(tmp_path):
    path = tmp_path / "last_run.txt"
    path.write_text("", encoding="utf-8")
    assert baca_last_run(path) is None