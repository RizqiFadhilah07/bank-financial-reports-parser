import pytest

from scrapers.base_scraper import BaseScraper
from scrapers.bsn_scraper import BsnScrapper
from scrapers.megaSyariah_scraper import MegaSyariahScraper


class ScraperTiruan(BaseScraper):
    def __init__(self, laporan):
        super().__init__("TIRUAN", "https://contoh.test", "https://contoh.test/laporan")
        self.laporan = laporan
        self.diunduh = []

    def fetch_page(self):
        return None

    def find_reports(self, soup):
        return self.laporan

    def download_pdf(self, pdf_url, filename):
        self.diunduh.append(filename)
        return False


def test_run_tanpa_laporan_melempar_error():
    scraper = ScraperTiruan([])
    with pytest.raises(RuntimeError):
        scraper.run()


def test_run_dengan_laporan_tidak_melempar_error():
    laporan = [{"pdf_url": "https://contoh.test/a.pdf", "filename": "a.pdf"}]
    scraper = ScraperTiruan(laporan)
    scraper.run()
    assert scraper.diunduh == ["a.pdf"]


@pytest.mark.parametrize("kelas", [BsnScrapper, MegaSyariahScraper])
def test_run_selenium_tanpa_laporan_melempar_error(kelas, monkeypatch):
    scraper = kelas()
    monkeypatch.setattr(scraper, "fetch_page", lambda: None)
    monkeypatch.setattr(scraper, "find_reports", lambda soup: [])
    with pytest.raises(RuntimeError):
        scraper.run()