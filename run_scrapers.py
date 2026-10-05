from scrapers.registry import SCRAPER_REGISTRY

def run_all():
    for bank_code, scraper_class in SCRAPER_REGISTRY.items():
        print(f"=== Menjalankan scraper: Bank {bank_code} ===\n")
        try:
            scraper = scraper_class()
            scraper.run()
        except Exception as e:
            print(f"Gagal scraping {bank_code}: {e}\n")

if __name__ == "__main__":
    run_all()