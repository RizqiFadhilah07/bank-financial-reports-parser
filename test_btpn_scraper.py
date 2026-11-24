from bs4 import BeautifulSoup

from scrapers.btpn_scraper import BtpnScraper

URL = (
    "http://www.btpnsyariah.com/api/media/pdf/699bfca1f1b7ede5d005b402/view"
    "?ownerType=financial-report&ownerId=699bfc6b1cdd69c5b08c1a46"
)


def buat_soup(label):
    html = (
        '<html><body><a href="' + URL.replace("&", "&amp;") + '">'
        "<div><h4>" + label + "</h4></div></a></body></html>"
    )
    return BeautifulSoup(html, "lxml")


def test_find_reports_menerima_tautan_api_media():
    scraper = BtpnScraper()
    scraper.valid_years = ["2026"]

    hasil = scraper.find_reports(buat_soup("Januari 2026"))

    assert hasil == [
        {"pdf_url": URL, "filename": "laporan-bulanan-BTPN-januari-2026.pdf"}
    ]


def test_find_reports_melewati_label_tanpa_bulan():
    scraper = BtpnScraper()
    scraper.valid_years = ["2026"]

    assert scraper.find_reports(buat_soup("Ikhtisar 2026")) == []