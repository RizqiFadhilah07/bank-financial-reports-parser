import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


def get_connection():
    if not os.getenv("DB_PASSWORD"):
        raise RuntimeError("DB_PASSWORD tidak ditemukan. Cek file .env")
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )