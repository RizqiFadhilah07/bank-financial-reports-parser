import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

REASONS = ("value_mismatch", "wrong_sign_type", "other")
STATUS = ("needs_check", "on_review", "done")
ALLOWED_TRANSITIONS = {
    "needs_check": ("on_review",),
    "on_review": ("needs_check", "done"),
    "done": (),
}

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "notes.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS flag (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_name TEXT NOT NULL,
    period_date TEXT NOT NULL,
    metric_alias TEXT NOT NULL,
    value_at_flag TEXT,
    reason TEXT NOT NULL,
    note TEXT,
    flagged_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'needs_check',
    updated_by TEXT,
    updated_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_flag
ON flag (bank_name, period_date, metric_alias)
WHERE status != 'done';
"""

def _now():
    return datetime.now().isoformat(timespec="seconds")


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    return conn


def add_flag(bank_name, period_date, metric_alias, value, reason, note,
            flagged_by, db_path=DEFAULT_DB_PATH):
    if reason not in REASONS:
        raise ValueError(f"Alasan tidak dikenal: {reason}")
    flagged_by = (flagged_by or "").strip()
    if not flagged_by:
        raise ValueError(f"Nama pengisi wajib diisi.")
    note = (note or "").strip() or None

    conn = _connect(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO flag(bank_name, period_date, metric_alias, value_at_flag,
                            reason, note, flagged_by, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (bank_name, str(period_date), metric_alias, str(value),
             reason, note, flagged_by, _now()),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError("Metrik ini sudah punya flag yang belum selesai.")
    finally:
        conn.close()


def change_status(flag_id, new_status, updated_by, db_path=DEFAULT_DB_PATH):
    if new_status not in STATUS:
        raise ValueError(f"Status tidak dikenal: {new_status}")
    updated_by = (updated_by or "").strip()
    if not updated_by:
        raise ValueError("Nama pengisi wajib diisi.")

    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT status FROM flag WHERE id = ?", (flag_id,)
        ).fetchone()
        if row is None:
            raise ValueError("Flag tidak ditemukan.")
        current_status = row[0]
        if current_status == "done":
            raise ValueError("Flag yang sudah selesai tidak bisa diubah lagi.")
        if new_status not in ALLOWED_TRANSITIONS[current_status]:
            raise ValueError(
                f'Perpindahan status dari "{current_status}" '
                f'ke "{new_status}" tidak diizinkan.'
            )
        cur = conn.execute(
            """
            UPDATE flag SET status = ?, updated_by = ?, updated_at = ? WHERE id = ?
            """,
            (new_status, updated_by, _now(), flag_id)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError("Flag tidak ditemukan.")
    except sqlite3.IntegrityError:
        raise ValueError("Metrik ini sudah punya flag yang belum selesai.")
    finally:
        conn.close()


def list_flags(bank_name=None, period_date=None, status=None, db_path=DEFAULT_DB_PATH):
    sql = "SELECT * FROM flag WHERE 1 = 1"
    params = []
    if bank_name is not None:
        sql += " AND bank_name = ?"
        params.append(bank_name)
    if period_date is not None:
        sql += " AND period_date = ?"
        params.append(str(period_date))
    if status is not None:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY created_at DESC, id DESC"

    conn = _connect(db_path)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()