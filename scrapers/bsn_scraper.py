from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import re
import time
try:
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper


class BsnScrapper (BaseScraper):
    def __init__(self):
        super().__init__(
            bank_code = "BSN",
            base_url = "https://bankbsn.co.id",
            page_url = "https://bankbsn.co.id/laporan-bank/bulanan"
        )
        self.driver = None

    def fetch_page(self):
        os.makedirs(self.download_dir, exist_ok=True)

        options = webdriver.ChromeOptions()
        prefs = {
            "download.default_directory": os.path.abspath(self.download_dir),
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True
        }
        options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(options=options)
        self.driver.get(self.page_url)
        time.sleep(5)

        html = self.driver.page_source
        return BeautifulSoup(html, "lxml")

    def find_reports(self, soup):
        reports = []

        for link in soup.find_all("a"):
            href = link.get("href")

            if not href :
                continue
            if "/laporan-bank/download/bulanan/" not in href:
                continue
            if not self.has_valid_year(href):
                continue

            match = re.search(r"/(\d{4})/(\d{1,2})", href)
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

    def wait_for_new_file(self, files_before, timeout=15):
        seconds = 0

        while seconds < timeout:
            files_now = set(os.listdir(self.download_dir))
            new_files = files_now - files_before
            new_files = {f for f in new_files if not f.endswith(".crdownload") and not f.endswith(".tmp")}

            if new_files:
                return new_files.pop()

            time.sleep(1)
            seconds += 1

        return None

    def download_pdf(self, pdf_url, filename):
        files_before = set(os.listdir(self.download_dir))

        print(f"Downloading : {filename}")
        self.driver.get(pdf_url)

        downloaded_name = self.wait_for_new_file(files_before)

        if not downloaded_name:
            print(f"FAILED: tidak ada file baru terdeteksi untuk {filename}\n")
            return False

        old_path = os.path.join(self.download_dir, downloaded_name)
        new_path = os.path.join(self.download_dir, filename)
        os.replace(old_path, new_path)

        print(f"Saved: {new_path}\n")
        return True

    def run(self):
        soup = self.fetch_page()
        reports = self.find_reports(soup)

        unique_reports = {r["filename"]: r for r in reports}
        reports = list(unique_reports.values())

        print(f"Found {len(reports)} monthly reports\n")
        for report in reports:
            print(f"{report['filename']}")
            print(f"URL : {report['pdf_url']}\n")

        for report in reports:
            if self.download_pdf(report["pdf_url"], report["filename"]):
                self.record_source(report["filename"], report["pdf_url"])

        self.driver.quit()


if __name__ == "__main__":
    scraper = BsnScrapper()
    scraper.run()

