from urllib.parse import urljoin, urlparse
import requests
import re
try: 
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper

class OcbcScraper (BaseScraper):
    def __init__(self):
        super().__init__(
            bank_code = "OCBC",
            base_url= "https://cdn1.ocbc.id/",
            page_url= "https://www.ocbc.id/id/tentang-ocbc/hubungan-investor/informasi-keuangan"
        )


    def find_reports(self, soup):
        reports = []

        for year in self.valid_years:
            for month_num in range(1,13):
                month_str = f"{month_num:02d}"

                pdf_url = (
                    f"{self.base_url}/asset/media/Feature/AboutOCBC/Hubungan-Investor/"
                    f"Informasi-Keuangan/Laporan-Keuangan/Laporan-Keuangan-Bulanan/"
                    f"{year}/{year}{month_str}-laporan-keuangan-bulanan_id.pdf"
                )

                response = requests.head(pdf_url, headers=self.HEADERS)

                if response.status_code != 200:
                    print(f"Laporan {month_str}/{year} belum tersedia, skip")
                    continue

                month = self.MONTH_MAP[month_num-1]
                filename = self.build_filename(month, str(year))
                reports.append({"pdf_url" : pdf_url, "filename": filename})

            return reports

if __name__ == "__main__":
    scraper = OcbcScraper()
    scraper.run()