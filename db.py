import os
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

def _kutip(nilai):
    return "{" + nilai.replace("}", "}}" + "}")


def build_connection_string():
    driver = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    host = os.getenv("DB_HOST", "localhost")
    name = os.getenv("DB_NAME")
    auth = os.getenv("DB_AUTH", "windows").strip().lower()

    if not name:
        raise RuntimeError("DB_NAME tidak ditemukan. Cek file .env")

    parts = [
        "DRIVER={" + driver + "}",
        "SERVER=" + host,
        "DATABASE=" + name,
    ]

    if auth == "windows":
        parts.append("Trusted_Connection=yes")
    elif auth == "sql":
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        if not user or not password:
            raise RuntimeError("DB_USER dan DB_PASSWORD wajib diisi untuk DB_AUTH=sql. Cek file .env")
        parts.append("UID=" + _kutip(user))
        parts.append("PWD=" + _kutip(password))
    else:
        raise RuntimeError(f"DB_AUTH tidak dikenal: '{auth}'. Pilih 'windows' atau 'sql'.")

    if os.getenv("DB_TRUST_CERT", "no").strip().lower() == "yes":
        parts.append("TrustServerCertificate=yes")

    return ";".join(parts) + ";"

def get_connection():
    return pyodbc.connect(build_connection_string(), autocommit=False)