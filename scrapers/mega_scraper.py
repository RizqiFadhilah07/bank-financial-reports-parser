from urllib.parse import urljoin, urlparse
import re
import requests
try:
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper


class MegaScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            bank_code= "Mega",
            base_url= "https://cdn.bankmega.com",
            page_url="https://bankmega.com/id/tentang-kami/hubungan-investor-new"
        )

    def extract_month_year(self, text):
        text_lower = text.lower()

        month = None
        for month_name in self.MONTH_MAP:
            if month_name in text_lower:
                month = month_name
                break

        year_match = re.search(r"_(\d{4})", text)
        year = year_match.group(1) if year_match else None
        return month, year        


    
    def find_reports(self, soup):
        reports = []

        for link in soup.find_all('a'):
            href = link.get("href")

            if not href:
                continue

            if not self.has_valid_year(href):
                continue

            if not href.lower().endswith(".pdf"):
                continue

            if "publikasi_bulanan" not in href:
                continue

            pdf_url = urljoin(self.base_url, href)
            month, year = self.extract_month_year(href)
            # print(f"DEBUG -> month: {month}, year: {year}")
            if not (month and year):
                print(f"Tidak dapat menentukan bulan/tahun dari {href}")
                continue

            filename = self.build_filename(month, year)
            reports.append({"pdf_url": pdf_url, "filename": filename})

        return reports

if __name__ == "__main__":
    scraper = MegaScraper()
    scraper.run()
