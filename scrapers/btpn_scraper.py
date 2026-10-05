from urllib.parse import urljoin
try:
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper

class BtpnScraper(BaseScraper):

    HEADERS = {
        **BaseScraper.HEADERS,
        "Referer": "https://www.btpnsyariah.com/"
    }

    def __init__(self):
        super().__init__(
            bank_code= "BTPN",
            base_url = "https://cdn-btpns-cms-prod.s3.ap-southeast-3.amazonaws.com/",
            page_url= "https://www.btpnsyariah.com/financial-report"
        )

    def find_reports(self, soup):
        reports = []

        for link in soup.find_all("a"):
            href = link.get("href")

            if not href:
                continue
            if not href.lower().endswith(".pdf"):
                continue

            h4_tag = link.find("h4")
            if not h4_tag:
                continue

            label_text = h4_tag.get_text()

            if not self.has_valid_year(label_text):
                continue

            pdf_url = urljoin(self.base_url, href)
            month, year = self.extract_month_year(label_text)

            filename = self.build_filename(month, year)
            reports.append({"pdf_url": pdf_url, "filename": filename})

        return reports

if __name__ == "__main__":
    scraper = BtpnScraper()
    scraper.run()