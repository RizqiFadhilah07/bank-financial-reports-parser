import sqlite3

import pytest

import notes


@pytest.fixture
def db(tmp_path):
    return tmp_path / "tes_notes.db"


def _tambah(db, **override):
    data = dict(
        bank_name="BCA",
        period_date="2026-08-31",
        metric_alias="total_assets",
        value=1000.0,
        reason="value_mismatch",
        note=None,
        flagged_by="Rizqi",
        db_path=db,
    )
    data.update(override)
    return notes.add_flag(**data)


def test_add_flag_mengembalikan_id(db):
    assert _tambah(db) == 1
    assert _tambah(db, metric_alias="net_income") == 2


def test_flag_terbuka_kembar_ditolak(db):
    _tambah(db)
    with pytest.raises(ValueError, match="belum selesai"):
        _tambah(db)


@pytest.mark.parametrize("alasan", ["tidak_ada", "", None])
def test_alasan_tidak_valid_ditolak(db, alasan):
    with pytest.raises(ValueError, match="Alasan tidak dikenal"):
        _tambah(db, reason=alasan)


@pytest.mark.parametrize("nama", ["", "   ", None])
def test_nama_pengisi_kosong_ditolak(db, nama):
    with pytest.raises(ValueError, match="Nama pengisi wajib diisi"):
        _tambah(db, flagged_by=nama)


@pytest.mark.parametrize("catatan", ["", "   "])
def test_catatan_kosong_disimpan_null(db, catatan):
    flag_id = _tambah(db, note=catatan)
    conn = sqlite3.connect(db)
    try:
        baris = conn.execute(
            "SELECT note FROM flag WHERE id = ?", (flag_id,)
        ).fetchone()
    finally:
        conn.close()
    assert baris[0] is None


def _baca_status(db, flag_id):
    conn = sqlite3.connect(db)
    try:
        return conn.execute(
            "SELECT status, updated_by FROM flag WHERE id = ?", (flag_id,)
        ).fetchone()
    finally:
        conn.close()


def test_change_status_berhasil(db):
    flag_id = _tambah(db)
    assert _baca_status(db, flag_id) == ("needs_check", None)
    notes.change_status(flag_id, "on_review", "Pengecek", db_path=db)
    assert _baca_status(db, flag_id) == ("on_review", "Pengecek")


@pytest.mark.parametrize(
    "status, nama, flag_id, pesan",
    [
        ("tidak_ada", "Pengecek", 1, "Status tidak dikenal"),
        ("done", "", 1, "Nama"),
        ("done", None, 1, "Nama"),
        ("done", "Pengecek", 99, "Flag tidak ditemukan"),
    ],
)
def test_change_status_input_tidak_valid(db, status, nama, flag_id, pesan):
    _tambah(db)
    with pytest.raises(ValueError, match=pesan):
        notes.change_status(flag_id, status, nama, db_path=db)


def test_flag_baru_boleh_setelah_done(db):
    pertama = _tambah(db)
    notes.change_status(pertama, "on_review", "Pengecek", db_path=db)
    notes.change_status(pertama, "done", "Pengecek", db_path=db)
    kedua = _tambah(db)
    assert kedua == pertama + 1


def test_done_tidak_bisa_diubah_lagi(db):
    pertama = _tambah(db)
    notes.change_status(pertama, "on_review", "Pengecek", db_path=db)
    notes.change_status(pertama, "done", "Pengecek", db_path=db)
    with pytest.raises(ValueError, match="sudah selesai"):
        notes.change_status(pertama, "needs_check", "Pengecek", db_path=db)


def _isi_tiga_flag(db):
    _tambah(db, bank_name="BCA", period_date="2026-07-31")
    _tambah(db, bank_name="BNI", period_date="2026-08-31")
    id3 = _tambah(db, bank_name="BCA", period_date="2026-08-31")
    notes.change_status(id3, "on_review", "Pengecek", db_path=db)


def test_list_flags_filter_dan_urutan(db):
    _isi_tiga_flag(db)
    semua = notes.list_flags(db_path=db)
    assert list(semua["id"]) == [3, 2, 1]
    assert len(notes.list_flags(bank_name="BCA", db_path=db)) == 2
    assert len(notes.list_flags(period_date="2026-08-31", db_path=db)) == 2
    assert len(notes.list_flags(status="on_review", db_path=db)) == 1
    assert len(
        notes.list_flags(bank_name="BCA", status="needs_check", db_path=db)
    ) == 1


def test_list_flags_kosong_tetap_punya_kolom(db):
    hasil = notes.list_flags(db_path=db)
    assert len(hasil) == 0
    assert "id" in hasil.columns
    assert "bank_name" in hasil.columns

def test_lompat_needs_check_ke_done_ditolak(db):
    flag_id = _tambah(db)
    with pytest.raises(ValueError, match="tidak diizinkan"):
        notes.change_status(flag_id, "done", "Pengecek", db_path=db)
    assert _baca_status(db, flag_id) == ("needs_check", None)


def test_mundur_on_review_ke_needs_check_berhasil(db):
    flag_id = _tambah(db)
    notes.change_status(flag_id, "on_review", "Pengecek", db_path=db)
    notes.change_status(flag_id, "needs_check", "Pengecek", db_path=db)
    assert _baca_status(db, flag_id)[0] == "needs_check"


def test_status_sama_ditolak(db):
    flag_id = _tambah(db)
    with pytest.raises(ValueError, match="tidak diizinkan"):
        notes.change_status(flag_id, "needs_check", "Pengecek", db_path=db)
    assert _baca_status(db, flag_id) == ("needs_check", None)
