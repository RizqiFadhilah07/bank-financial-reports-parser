from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
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
        self.driver.set_page_load_timeout(60)
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

    def month_of(self, filename):
        m = re.search(r"-([a-z]+)-\d{4}\.pdf$", filename)
        return m.group(1) if m else None

    def name_matches_month(self, server_name, month):
        name = server_name.lower()
        keys = {month}
        keys |= {eng.lower() for eng, ind in self.ENGLISH_MONTH_MAP.items() if ind == month}
        if any(k in name for k in keys):
            return True
        number = self.MONTH_MAP.index(month) + 1
        return re.fullmatch(rf"{number}( \(\d+\))?\.pdf", name) is not None

    def wait_until_idle(self, timeout=30):
        seconds = 0
        while seconds < timeout:
            if not any(f.endswith(".crdownload") for f in os.listdir(self.download_dir)):
                return True
            time.sleep(1)
            seconds += 1
        print("PERINGATAN: masih ada unduhan (.crdownload) yang belum selesai")
        return False

    def wait_for_new_file(self, files_before, month, timeout=15, max_wait=60):
        seconds = 0

        while seconds < max_wait:
            files_now = set(os.listdir(self.download_dir))
            new_files = {
                f for f in (files_now - files_before)
                if f.lower().endswith(".pdf") and self.name_matches_month(f, month)
            }

            if new_files:
                return new_files.pop()

            downloading = any(f.lower().endswith(".crdownload") for f in files_now - files_before)
            if seconds >= timeout and not downloading:
                break

            time.sleep(1)
            seconds += 1

        return None

    def download_pdf(self, pdf_url, filename):
        self.wait_until_idle()
        files_before = set(os.listdir(self.download_dir))
        month = self.month_of(filename)

        print(f"Downloading : {filename}")
        try:
            self.driver.get(pdf_url)
        except TimeoutException:
            print("PERINGATAN: halaman unduhan melewati batas waktu, tetap menunggu file")

        downloaded_name = self.wait_for_new_file(files_before, month)

        if not downloaded_name:
            ignored = set(os.listdir(self.download_dir)) - files_before
            print(f"GAGAL: tidak ada file unduhan yang cocok dengan bulan '{month}' untuk {filename}")
            if ignored:
                print(f"  File baru yang diabaikan karena nama tidak cocok: {sorted(ignored)}")
            print()
            return False

        old_path = os.path.join(self.download_dir, downloaded_name)
        new_path = os.path.join(self.download_dir, filename)
        os.replace(old_path, new_path)

        print(f"Saved: {new_path}\n")
        return True

    def run(self):
        try:
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
        finally:
            if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    scraper = BsnScrapper()
    scraper.run()

