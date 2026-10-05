import requests

url = "https://cdn1.ocbc.id/asset/media/Feature/AboutOCBC/Hubungan-Investor/Informasi-Keuangan/Laporan-Keuangan/Laporan-Keuangan-Bulanan/2025/202501-laporan-keuangan-bulanan_id.pdf"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )
}

response = requests.head(url, headers=HEADERS, allow_redirects=True)
print(f"Status akhir: {response.status_code}")
print(f"URL akhir: {response.url}")