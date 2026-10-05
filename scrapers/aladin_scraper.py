from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests
import json
import re
try:
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper


class AladinScraper(BaseScraper):

    AJAX_URL = "https://aladinbank.id/wordpress/wp-admin/admin-ajax.php"

    def __init__(self):
        super().__init__(
            bank_code= "Aladin",
            base_url= "https://aladinbank.id",
            page_url= "https://aladinbank.id/laporan-bulanan"
        )

    def fetch_loadmore_soup(self):
        query = {
            "page": 0, "pagename": "laporan-bulanan", "error": "", "m": "", "p": 0,
            "post_parent": "", "subpost": "", "subpost_id": "", "attachment": "",
            "attachment_id": 0, "name": "laporan-bulanan", "page_id": 0, "second": "",
            "minute": "", "hour": "", "day": 0, "monthnum": 0, "year": 0, "w": 0,
            "category_name": "", "tag": "", "cat": "", "tag_id": "", "author": "",
            "author_name": "", "feed": "", "tb": "", "paged": 0, "meta_key": "",
            "meta_value": "", "preview": "", "s": "", "sentence": "", "title": "",
            "fields": "", "menu_order": "", "embed": "", "category__in": [],
            "category__not_in": [], "category__and": [], "post__in": [],
            "post__not_in": [], "post_name__in": [], "tag__in": [], "tag__not_in": [],
            "tag__and": [], "tag_slug__in": [], "tag_slug__and": [],
            "post_parent__in": [], "post_parent__not_in": [], "author__in": [],
            "author__not_in": [], "search_columns": [], "orderby": "menu_order",
            "order": "ASC", "post_type": ["post", "page", "e-landing-page"],
            "ignore_sticky_posts": False, "suppress_filters": False,
            "cache_results": True, "update_post_term_cache": True,
            "update_menu_item_cache": False, "lazy_load_term_meta": True,
            "update_post_meta_cache": True, "posts_per_page": 100,
            "nopaging": False, "comments_per_page": "50", "no_found_rows": False,
        }

        ecs_ajax_settings = {
            "current_page": 1, "max_num_pages": "5", "load_method": "loadmore",
            "widget_id": "16770721", "post_id": 1796, "theme_id": 1796,
            "change_url": False, "reinit_js": False,
        }

        payload = {
            "action": "ecsload",
            "query": json.dumps(query),
            "ecs_ajax_settings": json.dumps(ecs_ajax_settings),
        }
        response = requests.post(self.AJAX_URL, data=payload, headers=self.HEADERS)
        response.raise_for_status()

        return BeautifulSoup(response.text, "lxml")

    def parse_links(self, soup):
        reports = []

        for link in soup.find_all("a"):
            href = link.get("href")

            if not href:
                continue
            if not self.has_valid_year(href):
                continue
            if not href.lower().endswith(".pdf"):
                continue

            pdf_url = urljoin(self.base_url, href)
            month = None
            for month_name in self.INDONESIA_MONTH_MAP:
                if month_name in pdf_url:
                    month = self.INDONESIA_MONTH_MAP[month_name]
                    break

            if not month:
                for month_name in self.ENGLISH_MONTH_MAP:
                    if month_name in pdf_url:
                        month = self.ENGLISH_MONTH_MAP[month_name]
                        break
            
            year_match = re.search(r"(\d{4})", pdf_url)
            year = year_match.group(1) if year_match else None
            
            if not(month and year):
                print(f"Tidak dapat menentukan bulan/tahun dari {href}")
                continue

            filename = self.build_filename(month, year)
            reports.append({"pdf_url": pdf_url, "filename": filename})

        return reports

    def find_reports(self, soup):
        reports = self.parse_links(soup)

        loadmore_soup = self.fetch_loadmore_soup()
        reports += self.parse_links(loadmore_soup)

        return reports

if __name__ == "__main__":
    scraper = AladinScraper()
    scraper.run()
