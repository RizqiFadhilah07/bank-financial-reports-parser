# Pipeline Laporan Keuangan Bank (SQL Server)

Mengunduh laporan keuangan **bulanan** 13 bank di Indonesia dalam bentuk PDF, mengekstrak angkanya, menyimpannya ke database **SQL Server**, lalu memvalidasi hasilnya.

Bank yang tercakup: BCA, OCBC, Mandiri, UOB, BNI, BTN, Bank Mega, BSI, CIMB Niaga, BTPN Syariah, Aladin, Bank Mega Syariah, dan Bank Syariah Nasional.

> Versi PostgreSQL proyek ini ada di branch `gabung` dan tidak dikembangkan lagi. Branch `main` dan `sqlserver` adalah versi SQL Server.

## Alur kerja

```
run_monthly.py
  1. run_scrapers.py               unduh PDF 13 bank ke downloads/<kode>/
  2. register_downloads.py --apply catat file baru ke tabel financial_reports (status 'downloaded')
  3. pipeline.py                   proses semua laporan 'downloaded' -> status 'parsed'
  4. validate.py                   5 aturan validasi, kode keluar 1 bila ada temuan
```

- `run_monthly.py` hanya bekerja pada **tanggal 15** dan **hari terakhir bulan**. Di hari lain ia mencetak "dilewati" dan keluar dengan kode 0. Penjadwalan harian (Task Scheduler Windows) cukup memanggilnya tiap hari.
- Register dan pipeline **idempoten**: dijalankan ulang tidak menggandakan data. "0 file baru" adalah hasil normal.

## Kebutuhan

- Windows, Python 3.10
- SQL Server 2019 (teruji di 2019 Developer Edition)
- Microsoft ODBC Driver for SQL Server (teruji dengan **Driver 17**; Driver 18 belum diuji)
- Google Chrome, hanya untuk dua scraper berbasis Selenium (BSN dan Mega Syariah)
- Akses internet ke situs bank

## Instalasi

```powershell
git clone https://github.com/RizqiFadhilah07/bank-financial-reports-parser.git
cd bank-financial-reports-parser
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` memuat `beautifulsoup4`, `lxml`, `openpyxl`, `pdfplumber`, `pyodbc`, `python-dotenv`, `requests`, dan `selenium`. `lxml` wajib karena dipakai sebagai parser HTML oleh beberapa scraper.

## Konfigurasi koneksi (`.env`)

Salin `.env.example` menjadi `.env`, lalu isi. **Jangan commit `.env`** (sudah diabaikan Git).

| Variabel | Keterangan |
|---|---|
| `DB_DRIVER` | Nama driver ODBC. Bawaan: `ODBC Driver 17 for SQL Server` |
| `DB_HOST` | Alamat server, persis seperti di SSMS: `localhost`, `IP`, `IP,port`, atau `IP\instance`. Bawaan: `localhost` |
| `DB_NAME` | Nama database. **Wajib** |
| `DB_AUTH` | `windows` (bawaan) atau `sql` |
| `DB_USER`, `DB_PASSWORD` | Wajib bila `DB_AUTH=sql`. Tulis password apa adanya, tanpa tanda kutip dan tanpa kurung kurawal |
| `DB_TRUST_CERT` | Isi `yes` hanya bila muncul error sertifikat SSL. Bawaan: `no` |

Contoh untuk SQL login:

```
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_HOST=192.168.1.10
DB_NAME=nama_database_anda
DB_AUTH=sql
DB_USER=nama_login
DB_PASSWORD=isi_password_anda
DB_TRUST_CERT=no
```

Uji koneksi:

```powershell
.venv\Scripts\python.exe -c "from db import get_connection; c = get_connection(); print(c.cursor().execute('SELECT DB_NAME(), SUSER_SNAME()').fetchone())"
```

Hasil yang diharapkan: nama database dan nama login yang dipakai.

## Membangun database dari nol

Seluruh langkah memakai file di repositori ini.

**1. Buat schema.** Buka `schema_sqlserver.sql` di SSMS dan jalankan. Hasilnya 9 tabel, 5 trigger, dan 1 view (`v_financial_data_summary`).

- Nama database tertulis di **3 tempat** (`DB_ID`, `CREATE DATABASE`, `USE`). Ganti sesuai nama database yang Anda inginkan dan samakan dengan `DB_NAME` di `.env`. Sebaiknya kerjakan pada salinan file.
- Script ini **tidak bisa dijalankan dua kali** pada database yang sama.
- Bila akun Anda tidak boleh `CREATE DATABASE`, minta DBA membuat database dan menjalankan schema, lalu hapus bagian `CREATE DATABASE` yang tidak diperlukan.

**2. Isi data master** (13 bank, 171 metrik, 2.215 pemetaan metrik):

```powershell
.venv\Scripts\python.exe seed_sqlserver.py            # dry-run, tidak menulis
.venv\Scripts\python.exe seed_sqlserver.py --apply    # menulis dalam satu transaksi
```

Seed hanya `INSERT` dan menolak berjalan bila ada tabel master yang sudah terisi. Dengan `--apply`, hitungan JSON dan database dicocokkan per tabel, dan transaksi dibatalkan bila berbeda.

**3. Unduh laporan** (atau salin folder `downloads\` yang sudah ada):

```powershell
.venv\Scripts\python.exe run_scrapers.py
```

**4. Daftarkan dan proses:**

```powershell
.venv\Scripts\python.exe register_downloads.py            # dry-run
.venv\Scripts\python.exe register_downloads.py --apply
.venv\Scripts\python.exe pipeline.py
.venv\Scripts\python.exe validate.py
```

## Menjalankan rutin

```powershell
.venv\Scripts\python.exe run_monthly.py                        # hanya bekerja tgl 15 dan akhir bulan
.venv\Scripts\python.exe run_monthly.py --force --skip-scrapers   # abaikan cek tanggal, tanpa unduhan
```

> **Peringatan:** `--force` tanpa `--skip-scrapers` menjalankan scraper sungguhan, yang **menimpa** PDF di `downloads\`. Scraper tidak pernah menghapus file.

Untuk penjadwalan, buat tugas di Task Scheduler yang memanggil `.venv\Scripts\python.exe run_monthly.py` setiap hari, dengan *Start in* diarahkan ke folder proyek.

## Antarmuka web (Streamlit)

Tiga halaman untuk melihat data tanpa SSMS. UI hanya membaca database; halaman Upload PDF tidak menyimpan apa pun.

| Halaman | Fungsi |
|---|---|
| Data Metrik | Filter bank, periode, kategori, dan cari metrik; tabel nilai per laporan |
| Status Laporan | Pivot status per bank dan bulan, laporan bermasalah, temuan validasi |
| Upload PDF | Uji ekstraksi satu PDF terhadap bank terpilih, dengan peringatan bila nama bank tidak ada di isi PDF |

Menjalankan (dari folder proyek, database harus sudah terisi):

```powershell
git checkout ui
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run Data_Metrik.py --server.address 127.0.0.1
```

Buka `http://127.0.0.1:8501`. UI memakai `.env` yang sama dengan pipeline.

- Data di-cache. Setelah pipeline menambah data, hentikan server (`Ctrl+C`) lalu jalankan ulang.

## Hak akses database

Akun yang menjalankan pipeline cukup memiliki `CONNECT`, `SELECT`, `INSERT`, dan `UPDATE` pada schema `dbo`. Hak `DELETE`, `CREATE`, dan `DROP` tidak dibutuhkan (teruji dengan SQL login yang dibatasi demikian). Pembuatan schema dilakukan satu kali oleh akun yang berhak.

## Aturan data

- Kolom `value` selalu bernilai **absolut**. Tanda tersimpan di kolom `sign_type` (`+` atau `-`). Satuan: juta rupiah. Angka yang kosong di PDF disimpan sebagai 0.
- Metrik yang tidak terbaca dari PDF **tidak punya baris** di `financial_data`. Pipeline mencatatnya sebagai peringatan di log, dan `validate.py` mendeteksinya.
- Pipeline menolak PDF dengan teks kurang dari 200 karakter (biasanya hasil scan).
- `file_path` awalnya relatif (`../downloads/<kode>/<file>`) dan diganti path absolut saat laporan diproses.
- Pipeline tidak menulis status `failed`. Laporan yang gagal tetap `downloaded` dan dicoba lagi pada run berikutnya. Pesan kesalahan tersimpan di `error_message`.

## Validasi (`validate.py`)

Lima aturan: `neraca`, `laba`, `leaking_label`, `metric_hilang`, dan `laporan_kosong`. Kode keluar 0 bila tanpa temuan, 1 bila ada. Opsi `--month` membatasi ke satu periode, contoh: `validate.py --month 2026-08-31`. Ada pengecualian yang disengaja untuk UOB (tiga metrik yang memang tidak ada di PDF sejak Juli 2026) dan untuk laporan yang diketahui tidak terbaca.

## Struktur proyek

```
.
├── db.py                    koneksi database (get_connection)
├── schema_sqlserver.sql     schema SQL Server
├── seed_sqlserver.py        isi data master dari seed/seed_export.json
├── seed/seed_export.json
├── run_scrapers.py          menjalankan semua scraper
├── register_downloads.py    mencatat PDF baru ke financial_reports
├── pipeline.py              memproses laporan berstatus 'downloaded'
├── validate.py              validasi hasil
├── run_monthly.py           orkestrasi bulanan
├── coverage.py
├── scrapers/                satu scraper per bank + registry.py
├── parsers/                 pembacaan PDF dan ekstraksi metrik
├── requirements.txt
└── .env.example
```

Folder `downloads/`, `logs/`, `.venv/`, dan `.env` tidak masuk Git.

## Keterbatasan yang diketahui

- **"Found 0" dianggap sukses.** Scraper tidak memeriksa jumlah laporan yang ditemukan. Semua bank seharusnya punya beberapa laporan, jadi hasil 0 perlu dicurigai (misalnya internet mati atau halaman situs berubah). Periksa log.
- **Bank Mega Syariah Januari 2026** berupa PDF hasil scan tanpa teks, sehingga tidak bisa diparse.
- **Format laporan bisa berubah.** Pada laporan Mandiri September 2026, empat label metrik berubah sehingga empat metrik tidak terbaca. Pipeline menandainya, dan `validate.py` melaporkannya.
- Dua scraper (BSN dan Mega Syariah) memakai Selenium dan butuh Chrome terpasang.
- Server SQL Server jarak jauh dan ODBC Driver 18 belum diuji. Jika memakai Driver 18 dan muncul error sertifikat, coba `DB_TRUST_CERT=yes`.

## Pemecahan masalah

| Gejala | Kemungkinan penyebab |
|---|---|
| `DB_NAME tidak ditemukan. Cek file .env` | `.env` belum ada atau `DB_NAME` kosong |
| `DB_USER dan DB_PASSWORD wajib diisi untuk DB_AUTH=sql` | `DB_AUTH=sql` tetapi user atau password kosong |
| `Login failed for user ...` | password salah, atau server belum mengaktifkan *SQL Server and Windows Authentication mode* |
| `Login failed for user 'DOMAIN\nama'` (nama berformat DOMAIN\user) | Windows auth terpakai: `DB_AUTH=sql` tidak terbaca. Pastikan file bernama persis `.env` (bukan `.env.txt`), ada di folder proyek, dan tulis `DB_AUTH=sql` tanpa spasi atau tanda kutip |
| Error sertifikat SSL | isi `DB_TRUST_CERT=yes` |
| `bs4.FeatureNotFound: ... lxml` | `lxml` belum terpasang. Jalankan `pip install -r requirements.txt` |
| Scraper BSN atau Mega Syariah gagal | Chrome belum terpasang atau tidak bisa dijalankan |
| `502 Bad Gateway` saat mengunduh | gangguan sementara di server bank. Jalankan ulang scraper bank itu |