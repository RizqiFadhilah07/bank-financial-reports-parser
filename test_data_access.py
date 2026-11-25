from data_access import _samarkan_path

def test_path_windows_jadi_nama_file():
    teks = r"File tidak ada: C:\Users\Doni\downloads\Mega\laporan.pdf"
    assert _samarkan_path(teks) == "File tidak ada: laporan.pdf"


def test_none_dikembalikan_apa_adanya():
    assert _samarkan_path(None) is None


def test_teks_tanpa_path_tidak_berubah():
    assert _samarkan_path("Teks scan kosong") == "Teks scan kosong"


def test_dua_path_dalam_satu_teks():
    teks = r"A: C:\x\a.pdf dan B: D:\y\z\b.pdf"
    assert _samarkan_path(teks) == "A: a.pdf dan B: b.pdf"



def test_beri_nama_metrik_hanya_untuk_metric_hilang():
    import pandas as pd
    from data_access import naming_metric

    df = pd.DataFrame(
        [
            ("metric_hilang", "Aladin", "2026-10-31", "lease_financing"),
            ("neraca", "Aladin", "2026-10-31", "aset=1 pasiva=NULL"),
            ("metric_hilang", "Aladin", "2026-10-31", "alias_tak_dikenal"),
        ],
        columns=["rule", "bank_name", "period_date", "detail"],
    )
    hasil = naming_metric(df, {"lease_financing": "Pembiayaan sewa"})
    assert hasil["detail"].tolist() == [
        "Pembiayaan sewa (lease_financing)",
        "aset=1 pasiva=NULL",
        "alias_tak_dikenal",
    ]