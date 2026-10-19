from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
import os
import re
import time
try :
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper


class MegaSyariahScraper (BaseScraper):
    def __init__(self):
        super().__init__(
            bank_code="MegaSyariah",
            base_url="https://www.megasyariah.co.id",
            page_url="https://www.megasyariah.co.id/id/tentang-kami/laporan-keuangan-perusahaan/laporan-bulanan"
        )


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

        for link in soup.find_all("a"):
            href = link.get("href")

            if not href:
                continue
            if not href.lower().endswith(".pdf"):
                continue
            if "LapKeuBul" not in href and "Bulanan" not in href and "Publikasi" not in href:
                continue

            month, year = self.extract_month_year(href)

            if not (month and year):
               for eng_month, ind_month in self.ENGLISH_MONTH_MAP.items():
                   if eng_month in href:
                       month = ind_month
                       year_match = re.search(r"(\d{4})", href)
                       year = year_match.group(1) if year_match else None
                       break

            if not (month and year):
                fallback_match = re.search(r"_(\d{2})(\d{2})\.pdf", href, re.IGNORECASE)
                if fallback_match:
                    month_num = int(fallback_match.group(1))
                    year_2digit = fallback_match.group(2)
                    if (1 <= month_num <= 12):
                        month = self.MONTH_MAP[month_num - 1]
                        year = "20" + year_2digit

            if not (month and year):
                print(f"Tidak dapat menentukan bulan/tahun dari {href}")
                continue 

            if year not in self.valid_years:
                continue

            pdf_url = urljoin(self.base_url, href)
            filename = self.build_filename(month, year)
            reports.append({"pdf_url": pdf_url, "filename": filename})

        return reports

    def expected_server_name(self, pdf_url):
        return unquote(os.path.basename(urlparse(pdf_url).path))

    def name_matches_url(self, server_name, expected):
        name = server_name.lower()
        stem, ext = os.path.splitext(expected.lower())
        return re.fullmatch(rf"{re.escape(stem)}( \(\d+\))?{re.escape(ext)}", name) is not None

    def wait_until_idle(self, timeout=30):
        seconds = 0
        while seconds < timeout:
            if not any(f.endswith(".crdownload") for f in os.listdir(self.download_dir)):
                return True
            time.sleep(1)
            seconds += 1
        print("PERINGATAN: masih ada unduhan (.crdownload) yang belum selesai")
        return False


    def wait_for_new_files(self, files_before, expected, timeout=15, max_wait=60):
        seconds = 0
        partial = expected + ".crdownload"

        while seconds < max_wait:
            files_now = set(os.listdir(self.download_dir))
            new_files = {
                f for f in (files_now - files_before)
                if self.name_matches_url(f, expected)
            }

            if new_files:
                return new_files.pop()

            downloading = any(f.lower() == partial.lower() for f in files_now)
            if seconds >= timeout and not downloading:
                break

            time.sleep(1)
            seconds += 1

        return None

    def download_pdf(self, pdf_url, filename):
        self.wait_until_idle()
        files_before = set(os.listdir(self.download_dir))
        expected = self.expected_server_name(pdf_url)

        print(f"Downloading : {filename}")
        self.driver.get(pdf_url)

        downloaded_name = self.wait_for_new_files(files_before, expected)

        if not downloaded_name:
            ignored = set(os.listdir(self.download_dir)) - files_before
            print(f"GAGAL: tidak ada file unduhan bernama '{expected}' untuk {filename}")
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
    scraper = MegaSyariahScraper()
    scraper.run()

                