from preview import cek_nama_bank


def test_bca_cocok():
    assert cek_nama_bank("BCA", "Laporan Bank Central Asia") is True


def test_bank_salah_terdeteksi():
    assert cek_nama_bank("Mandiri", "Laporan Bank Central Asia") is False


def test_mega_vs_mega_syariah():
    assert cek_nama_bank("Bank Mega", "Laporan Bank Mega Syariah") is False


def test_bank_mega_syariah_cocok():
    assert cek_nama_bank("Bank Mega Syariah", "Laporan Bank Mega Syariah") is True


def test_bni_tidak_bisa_dicek():
    assert cek_nama_bank("BNI", "teks apa saja") is None


def test_uob_tidak_bisa_dicek():
    assert cek_nama_bank("UOB", "teks apa saja") is None