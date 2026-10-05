from urllib.parse import urljoin, unquote
try:
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper


class MandiriScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            bank_code="Mandiri",
            base_url="https://www.bankmandiri.co.id",
            page_url="https://www.bankmandiri.co.id/web/ir/monthly-financials",
        )

    def extract_filename_from_href(self, href):
        path_no_query = href.split("?")[0]
        segments = path_no_query.split("/")

        for segment in segments:
            if ".pdf" in segment.lower():
                return unquote(segment).replace("+", " ")

        return unquote(path_no_query.split("/")[-1]).replace("+", " ")

    def find_reports(self, soup):
        reports = []

        for link in soup.find_all("a"):
            href = link.get("href")

            if not href:
                continue
            if not self.has_valid_year(href):
                continue
            if ".pdf" not in href:
                continue
            if "IR+" not in href:
                continue

            pdf_url = urljoin(self.base_url, href)
            original_filename = self.extract_filename_from_href(href)
            month, year = self.extract_month_year(original_filename)

            if not (month and year):
                print(f"Tidak dapat menentukan bulan/tahun dari {href}")
                continue

            filename = self.build_filename(month, year)
            reports.append({"pdf_url": pdf_url, "filename": filename})

        return reports


if __name__ == "__main__":
    scraper = MandiriScraper()
    scraper.run()