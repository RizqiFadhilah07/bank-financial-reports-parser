import json
from pathlib import Path
from db import get_connection

OUT = Path(__file__).resolve().parent / "baseline" / "seed_export.json"


def fetch(cur, sql):
    cur.execute(sql)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


conn = get_connection()
cur = conn.cursor()
data = {
    "master_metrics": fetch(cur,
        "SELECT metric_alias, category, sub_category, metric_name, metric_order "
        "FROM master_metrics ORDER BY metric_order, metric_alias"),
    "banks": fetch(cur,
        "SELECT bank_name, bank_type, period_type, report_url, is_active "
        "FROM banks ORDER BY bank_id"),
    "bank_metric_mapping": fetch(cur,
        "SELECT b.bank_name, m.metric_alias, m.is_applicable, m.local_term "
        "FROM bank_metric_mapping m JOIN banks b ON b.bank_id = m.bank_id "
        "ORDER BY b.bank_id, m.metric_alias"),
}
conn.close()

OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
for name, rows in data.items():
    print(f"{name}: {len(rows)} baris")
print("Tersimpan:", OUT)