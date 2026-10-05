from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time
try:
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper


class UobScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            bank_code= "UOB",
            base_url= "https://www.uob.co.id",
            page_url= "https://www.uob.co.id/about/investor-relations/financial-statements/monthly.page"
        )
        self.driver = None

    def remove_cookie_popup(self):
        self.driver.execute_script(
            "var el = document.getElementById('cookie-alert'); if (el) el.remove();"
        )

    def fetch_page(self):
        self.driver = webdriver.Chrome()
        self.driver.get(self.page_url)
        
        time.sleep(5)

        self.driver.execute_script(
            "var el = document.getElementById('cookie-alert'); if (el) el.remove();"
        )

        html = self.driver.page_source

        return BeautifulSoup(html, "lxml")

    def select_year(self, year_2digit):
        self.remove_cookie_popup()
        button = self.driver.find_element(
            By.CSS_SELECTOR, "div.yearFilter button.dropdown-toggle"
        )
        button.click()

        option = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((
                By.XPATH,
                f"//div[contains(@class,'yearFilter')]//span[@class='text'][normalize-space(text())='{year_2digit}']"
            ))
        )
        self.driver.execute_script("arguments[0].click();", option)

        time.sleep(3)

    def parse_links(self,soup):
        reports = []

        for link in soup.find_all("a"):
            href = link.get("href")

            if not href:
                continue
            if "Laporan-Publikasi-Bulanan" not in href:
                continue
            if not href.lower().endswith(".pdf"):
                continue
            if not self.has_valid_year(href):
                continue

            pdf_url = urljoin(self.base_url, href)
            month, year = self.extract_month_year(href)

            if not (month and year):
                print(f"Tidak dapat menentukan bulan/tahun dari {href}")
                continue

            filename = self.build_filename(month, year)
            reports.append({"pdf_url": pdf_url, "filename": filename})

        return reports

    def find_reports(self, soup):
        reports = self.parse_links(soup)

        for year in self.valid_years:
            year_2digit = year[-2:]

            if year == self.current_year:
                continue

            print(f"Beralih ke tahun {year}")
            self.select_year(year_2digit)

            page_soup = BeautifulSoup(self.driver.page_source, "lxml")
            reports += self.parse_links(page_soup)


        self.driver.quit()
        return reports


if __name__ == "__main__":
    scraper = UobScraper()
    scraper.run()
