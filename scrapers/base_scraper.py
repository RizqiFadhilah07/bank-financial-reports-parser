from abc import ABC, abstractmethod
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import unquote
import requests
import os
import re

class BaseScraper(ABC):
    HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
        )
    }
    MONTH_MAP = [
        "januari", "februari", "maret", "april", "mei", "juni",
        "juli", "agustus", "september", "oktober", "november", "desember",
    ]

    ENGLISH_MONTH_MAP = {
        "Jan": "januari",
        "Feb": "februari",
        "Mar": "maret",
        "Apr": "april", 
        "May": "mei",
        "Jun": "juni",
        "Jul": "juli",
        "Aug": "agustus",
        "Sep": "september",
        "Oct": "oktober",
        "Nov": "november",
        "Dec": "desember"
    }

    INDONESIA_MONTH_MAP = {
        "Jan": "januari",
        "Feb": "februari",
        "Mar": "maret",
        "Apr": "april", 
        "Mei": "mei",
        "Jun": "juni",
        "Jul": "juli",
        "Agu": "agustus",
        "Sep": "september",
        "Okt": "oktober",
        "Nov": "november",
        "Des": "desember"
    }

    START_YEAR = 2026

    def __init__(self, bank_code, base_url, page_url):
        self.bank_code = bank_code
        self.base_url = base_url
        self.page_url = page_url

        current_year_int = datetime.now().year
        self.current_year = str(current_year_int)
        self.year_before = str(current_year_int - 1)
        self.valid_years = [
            year for year in [self.current_year, self.year_before]
            if int(year) >= self.START_YEAR
        ]

        script_dir = os.path.dirname(os.path.abspath(__file__))
        financial_reports_dir = os.path.dirname(script_dir)
        self.download_dir = os.path.join(
            financial_reports_dir, "downloads", self.bank_code
        )

    def fetch_page(self):
        response = requests.get(self.page_url, headers = self.HEADERS)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")


    def extract_month_year(self, text):
        text_lower = text.lower()

        month = None
        for month_name in self.MONTH_MAP:
            if month_name in text_lower:
                month = month_name
                break

        year_match = re.search(r"\b20\d{2}\b", text)
        year = year_match.group() if year_match else None

        return month, year

    def build_filename(self, month, year):
        return f"laporan-bulanan-{self.bank_code}-{month}-{year}.pdf"


    def download_pdf(self, pdf_url, filename):
        os.makedirs(self.download_dir, exist_ok =True)
        filepath = os.path.join(self.download_dir, filename)

        print(f"Downloading : {filename}")
        try:
            response = requests.get(pdf_url, headers = self.HEADERS)
            response.raise_for_status()

            if not response.content.startswith(b"%PDF"):
                print(f"PERINGATAN: {filename} bukan file asli, skip")
                return
            
            with open(filepath, "wb") as file:
                file.write(response.content)

            print(f"Saved : {filepath}\n")
        except requests.exceptions.HTTPError as e:
            print(f"GAGAL download {filename}: {e}\n")



    def has_valid_year(self, href):
        return any(year in href for year in self.valid_years)


    @abstractmethod
    def find_reports(self, soup):
        pass

    def run(self):
        soup = self.fetch_page()
        reports = self.find_reports(soup)


        unique_reports = {r["filename"]: r for r in reports}
        reports = list(unique_reports.values())

        print(f"Found {len(reports)} monthly reports\n")
        for report in reports:
            print(f"{report['filename']}")
            print(f"URL : {report['pdf_url']}\n")

        for report in sorted(reports, key=lambda r: r["filename"], reverse=True):
            self.download_pdf(report["pdf_url"], report["filename"])
    