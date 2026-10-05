import csv
import sys
from db import get_connection


def export(path):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT report_id, metric_alias, value, sign_type, raw_text
        FROM financial_data
        ORDER BY report_id, metric_alias
    """)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["report_id", "metric_alias", "value", "sign_type", "raw_text"])
        w.writerows(cur.fetchall())
    conn.close()
    print(f"Tersimpan: {path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Pemakaian: python export_baseline.py <path_output.csv>")
        sys.exit(1)
    export(sys.argv[1])