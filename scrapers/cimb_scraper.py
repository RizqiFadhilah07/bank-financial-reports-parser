from urllib.parse import urlparse, parse_qs
import re
try:
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper


class CimbScraper(BaseScraper):

    def __init__(self):
        super().__init__(
            bank_code="CIMB",
            base_url="https://investor.cimbniaga.co.id",
            page_url="https://investor.cimbniaga.co.id/financials.html",
        )

    def find_reports(self, soup):
        reports = []

        for link in soup.find_all("a"):
            href = link.get("href")

            if not href:
                continue
            if not self.has_valid_year(href):
                continue
            if "redirect=" not in href:
                continue

            parsed = urlparse(href)
            params = parse_qs(parsed.query)
            pdf_url = params.get("redirect", [None])[0]

            if not pdf_url:
                continue
            if not pdf_url.lower().endswith(".pdf"):
                continue

            month = None
            for month_name in self.ENGLISH_MONTH_MAP:
                if month_name in pdf_url:
                    month = self.ENGLISH_MONTH_MAP[month_name]
                    break
            year_match = re.search(r"(\d{4})", pdf_url)
            year = year_match.group(1) if year_match else None

            if not (month and year):
                print(f"Tidak dapat menentukan bulan/tahun dari {href}")
                continue

            filename = self.build_filename(month, year)
            reports.append({"pdf_url": pdf_url, "filename": filename})
            
        return reports


if __name__ == "__main__":
    scraper = CimbScraper()
    scraper.run()