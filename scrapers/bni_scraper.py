from selenium import webdriver
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re
try:
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper

class BniScraper (BaseScraper):
    def __init__(self):
        super().__init__(
            bank_code= "BNI",
            base_url= "https://www.bni.co.id/id-id",
            page_url= "https://www.bni.co.id/id-id/investor/laporan-keuangan"
        )

    def fetch_page(self):
        driver = webdriver.Chrome()
        driver.get(self.page_url)
        time.sleep(5)

        html = driver.page_source
        driver.quit()

        return BeautifulSoup(html, "lxml")


    def find_reports(self, soup):
        reports = []


        for link in soup.find_all("a"):
            href = link.get("href")

            if not href:
                continue
            if "LKP_BLN" not in href:
                continue
            if not href.lower().endswith(".pdf"):
                continue
            if not self.has_valid_year(href):
                continue

            match = re.search(r"LKP_BLN_(\d{4})-(\d{2})", href)
            if not match:
                print(f"Tidak dapat menentukan bulan/tahun dari {href}")
                continue

            year = match.group(1)
            month_num = int(match.group(2))

            if not (1 <= month_num <= 12):
                continue

            month = self.MONTH_MAP[month_num-1]

            pdf_url = urljoin(self.base_url, href)
            filename = self.build_filename(month, year)
            reports.append({"pdf_url": pdf_url, "filename": filename})

        return reports

if __name__ == "__main__":
    scraper = BniScraper()
    scraper.run()
