import argparse
import calendar
import logging
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG_DIR = HERE / "logs"
logger = logging.getLogger("run_monthly")

STEPS = [
    ("scrapers", ["run_scrapers.py"], False),
    ("register", ["register_downloads.py", "--apply"], True),
    ("pipeline", ["pipeline.py"], True),
    ("validate", ["validate.py"], False),
]

def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(LOG_DIR / "run_monthly.log", mode="a", encoding="utf-8")
    fh.setFormatter(fmt)
    ch = logging.StreamHandler()
    logger.setLevel(logging.INFO)
    logger.addHandler(fh)
    logger.addHandler(ch)

def is_run_day(today):
    return today.day == 15 or today.day == calendar.monthrange(today.year, today.month)[1]


def run_step(nama, argumen):
    cmd = [sys.executable, "-u", *argumen]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    logger.info("=== MULAI %s: %s", nama, " ".join(argumen))
    proc = subprocess.Popen(
        cmd, cwd=HERE, env = env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text = True, encoding = "utf-8", errors = "replace",
    )
    scraper_gagal = 0
    for line in proc.stdout:
        line = line.rstrip()
        if not line:
            continue
        logger.info("[%s] %s", nama, line)
        if line.startswith("Gagal scraping"):
            scraper_gagal += 1
    rc = proc.wait()
    logger.info("=== SELESAI %s: kode keluar %d", nama, rc)
    return rc, scraper_gagal

def main():
    ap = argparse.ArgumentParser(description="Jalankan pipeline bulanan lengkap")
    ap.add_argument("--force", action="store_true",
                    help="abaikan cek tanggal 15 / akhir bulan")
    ap.add_argument("--skip-scrapers", action="store_true",
                    help="lewati scraping pdf, lanjut ke sisa alur")
    args = ap.parse_args()

    setup_logging()
    today = date.today()
    if not args.force and not is_run_day(today):
        logger.info("Hari ini %s bukan tanggal 15 / akhir bulan, dilewati.", today)
        return 0

    problem = []
    for nama, argumen, stop in STEPS:
        if nama == "scrapers" and args.skip_scrapers:
            logger.info("Langkah scrapers dilewati (--skip scrapers)")
            continue

        rc, scraper_gagal = run_step(nama, argumen)

        if nama == "scrapers" and scraper_gagal:
            problem.append(f"scrapers: {scraper_gagal} bank gagal")
            logger.warning("%d scraper gagal, alur tetap lanjut", scraper_gagal)
        if rc != 0:
            problem.append(f"{nama} kode keluar {rc}")
            if stop:
                logger.error("%s gagal, alur dihentikan", nama)
                break

    if problem:
        logger.warning("Selesai dengan masalah: %s", "; ".join(problem))
        return 1
    logger.info("Complete without any problem.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
    
