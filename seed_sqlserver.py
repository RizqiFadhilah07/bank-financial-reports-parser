import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from db import get_connection

SEED_FILE = Path(__file__).resolve().parent / "seed" / "seed_export.json"
TABLES = ["master_metrics", "banks", "bank_metric_mapping"]

def count_rows(cur, table):
    cur.execute(f"SELECT COUNT(*) FROM dbo.{table}")
    return cur.fetchone()[0]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="tulis ke database")
    args = ap.parse_args()

    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    expected = {t:len(data[t]) for t in TABLES}

    conn = get_connection()
    cur = conn.cursor()

    for table in TABLES:
        n = count_rows(cur, table)
        print(f"{table:22} JSON={expected[table]:5} database={n:5}")
        if n != 0:
            print(f"Dibatalkan: tabel {table} tidak kosong.")
            conn.close()
            return 1

    if not args.apply:
        print(f"\nDry-run: belum ada yang ditulis ke database. Tambahkan --apply untuk menulis.")
        conn.close()
        return 0

    try:
        for r in data["master_metrics"]:
            cur.execute(
                """
                INSERT INTO dbo.master_metrics
                (metric_alias, category, sub_category, metric_name, metric_order)
                VALUES (?, ?, ?, ?, ?)
                """,
                (r["metric_alias"], r["category"], r["sub_category"], r["metric_name"], r["metric_order"]),
            )

        for r in data["banks"]:
                cur.execute(
                "INSERT INTO dbo.banks (bank_name, bank_type, period_type, report_url, is_active) "
                "VALUES (?, ?, ?, ?, ?)",
                (r["bank_name"], r["bank_type"], r["period_type"],
                r["report_url"], r["is_active"]),
            )

        cur.execute("SELECT bank_id, bank_name FROM dbo.banks")
        bank_ids = {name: bid for bid, name in cur.fetchall()}

        for r in data["bank_metric_mapping"]:
                cur.execute(
                "INSERT INTO dbo.bank_metric_mapping (bank_id, metric_alias, is_applicable, local_term) "
                "VALUES (?, ?, ?, ?)",
                (bank_ids[r["bank_name"]], r["metric_alias"],
                r["is_applicable"], r["local_term"]),
            )

        ok = True
        for table in TABLES:
            n = count_rows(cur,table)
            status = "MATCH" if n == expected[table] else "MISMATCHED"
            ok = ok and n == expected[table]
            print(f"{table:22} JSON={expected[table]:5}  database={n:5}  {status}")

        cur.execute(
            """
            SELECT b.bank_name, COUNT(*) FROM dbo.bank_metric_mapping m
            JOIN dbo.banks b ON b.bank_id = m.bank_id 
            GROUP BY b.bank_name
            """
        )
        per_bank_db = {name: n for name, n in cur.fetchall()}
        per_bank_json = Counter(r["bank_name"] for r in data["bank_metric_mapping"])
        if per_bank_db != dict(per_bank_json):
            print("Jumlah mapping per bank BEDA:", per_bank_db, dict(per_bank_json))
            ok = False

        if not ok:
            conn.rollback()
            print("Dibatalkan (rollback): ada yang tidak cocok. ")
            return 1

        conn.commit()
        print("\nSeed tersimpan. ")
        return 0

    except Exception as e:
        conn.rollback()
        print(f"Gagal, rollback: {type(e).__name__}: {e}")
        return 1
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())




        
        