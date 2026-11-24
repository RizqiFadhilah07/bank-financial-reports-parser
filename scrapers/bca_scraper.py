import re
from urllib.parse import urljoin
try:
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper

class BcaScraper (BaseScraper):
    JSON_URL_PATTERN = re.compile(
        r'https://pustaka\.bca\.co\.id/[^"\\\s]*Laporan-Bulanan/[^"\\\s]*\.pdf',
        re.IGNORECASE,
    )

    def __init__(self):
        super().__init__(
            bank_code = "BCA",
            base_url = "https://www.bca.co.id",
            page_url = "https://www.bca.co.id/id/tentang-bca/Hubungan-Investor/laporan-presentasi/Laporan-Keuangan",
        )

    def find_reports(self, soup):
        reports = []

        candidates = [link.get("href") for link in soup.find_all("a")]
        candidates += self.JSON_URL_PATTERN.findall(str(soup))

        for href in dict.fromkeys(candidates):
            if not href:
                continue
            if "laporan-bulanan" not in href.lower():
                continue
            if not self.has_valid_year(href):
                continue
            if not href.lower().endswith(".pdf"):
                continue

            pdf_url = urljoin(self.base_url, href)
            month, year = self.extract_month_year(href)

            if not (month and year):
                print(f"Tidak dapat menentukan bulan/tahun dari {href}")
                continue

            filename = self.build_filename(month, year)
            reports.append({"pdf_url" : pdf_url, "filename" : filename})

        return reports


if __name__ == "__main__":
    scraper = BcaScraper()
    scraper.run()