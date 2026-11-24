from bs4 import BeautifulSoup

from scrapers.bca_scraper import BcaScraper

URL_OKTOBER = (
    "https://pustaka.bca.co.id/-/media/Feature/Report/File/S8/"
    "Laporan-Bulanan/2026/20261113-laporan-keuangan-publikasi-bulanan-oktober-2026-ind.pdf"
)
URL_AGUSTUS = (
    "https://pustaka.bca.co.id/-/media/Feature/Report/File/S8/"
    "Laporan-Bulanan/2026/20260915-laporan-keuangan-publikasi-bulanan-agustus-2026-ID.pdf"
)


def buat_soup():
    json_escape = (
        'self.__next_f.push([1,"{\\"year\\":2026,\\"url\\":\\"' + URL_OKTOBER + '\\"},'
        '{\\"year\\":2026,\\"url\\":\\"' + URL_AGUSTUS + '\\"}"])'
    )
    html = "<html><body><script>" + json_escape + "</script></body></html>"
    return BeautifulSoup(html, "lxml")


def test_find_reports_membaca_url_dari_json():
    scraper = BcaScraper()
    scraper.valid_years = ["2026"]

    hasil = scraper.find_reports(buat_soup())

    assert hasil == [
        {"pdf_url": URL_OKTOBER, "filename": "laporan-bulanan-BCA-oktober-2026.pdf"},
        {"pdf_url": URL_AGUSTUS, "filename": "laporan-bulanan-BCA-agustus-2026.pdf"},
    ]