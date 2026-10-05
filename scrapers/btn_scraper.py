from selenium import webdriver
from selenium.webdriver.common.by import By
from urllib.parse import urljoin
import time
import re
try :
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper

class BtnScraper (BaseScraper):
    def __init__(self):
        super().__init__(
            bank_code="BTN",
            base_url="https://www.btn.co.id/id",
            page_url="https://www.btn.co.id/id/about/investor-relation/company-report/monthly-report"
        )
        self.driver = None

    def fetch_page(self):
        self.driver = webdriver.Chrome()
        self.driver.get(self.page_url)
        time.sleep(5)

        return None

    def find_reports(self, soup):
        reports = []

        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")

        for iframe in iframes:
            src = iframe.get_attribute('src')

            if not src:
                continue
            if not src.lower().endswith(".pdf"):
                continue
            if "Bulanan" not in src:
                continue
            if not self.has_valid_year(src):
                continue

            month, year = self.extract_month_year(src)
            pdf_url = urljoin(self.base_url, src)

            if not (month and year):
                fallback_match = re.search(r"_(\d{2})-(\d{4})", src)

                if fallback_match:
                    year = fallback_match.group(2)
                    month_num = int(fallback_match.group(1))
                    month = self.MONTH_MAP[month_num - 1]

            if not (month and year):
                print(f"Tidak dapat menentukan bulan/tahun dari {src}")
                continue

            
            filename = self.build_filename(month, year)
            reports.append({"pdf_url": pdf_url, "filename": filename})

        return reports

if __name__ == "__main__":
    scraper = BtnScraper()
    scraper.run()