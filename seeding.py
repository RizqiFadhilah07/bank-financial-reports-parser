import openpyxl
from db import get_connection

conn = get_connection()
cur = conn.cursor()

wb = openpyxl.load_workbook("Data_Bank_FINAL.xlsx", data_only=True)

# ====================================================
# Banks
# ====================================================  
ws = wb['Banks']

for row in ws.iter_rows(min_row=2, values_only=True):
    bank_name = row[1]
    bank_type = row[2]
    period_type = row[3]
    url = row[4]

    cur.execute(
        """
        INSERT INTO banks (bank_name, bank_type, period_type, report_url) VALUES (%s, %s, %s, %s)
        ON CONFLICT (bank_name) DO UPDATE
        SET bank_type = EXCLUDED.bank_type,
            period_type = EXCLUDED.period_type,
            report_url = EXCLUDED.report_url""",
        (bank_name, bank_type, period_type, url)
    )
    print(f"Berhasil insert: {bank_name}")

print("Data inserted successfully into the banks table.")

# ====================================================
# Master Metrics
# ====================================================   
ws2 = wb['Master Metric']
for i, row in enumerate(ws2.iter_rows(min_row=2, values_only=True), start=1):
    category = row[0]
    sub_category = row[1]
    metric_name = row[2]
    metric_alias = row[3]

    if not metric_alias or not metric_name:
        continue

    cur.execute(
        """
        INSERT INTO master_metrics (category, sub_category, metric_name, metric_alias, metric_order) 
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (metric_alias) DO UPDATE
        SET category = EXCLUDED.category,
            sub_category = EXCLUDED.sub_category,
            metric_name = EXCLUDED.metric_name,
            metric_order = EXCLUDED.metric_order
        """,
        (category, sub_category, metric_name, metric_alias, i)
    )

    print(f"Berhasil insert: {metric_name} - {metric_alias}")

print("Data inserted successfully into the master_metrics table.")

# ====================================================
# Bank Mapping
# ====================================================  

cur.execute(
    """
        SELECT bank_id, bank_name FROM banks
    """
)

bank_name_to_id = {name: id for id, name in cur.fetchall()}

ws3 = wb["Bank Mapping"]
header_row = next(ws3.iter_rows(min_row=1, max_row=1, values_only=True))

for row in ws3.iter_rows(min_row=2, values_only=True):
    metric_alias = row[0]
    standard_term = row[1]

    if not metric_alias or not standard_term:
        continue

    for col_index in range(2, len(header_row)):
        bank_name = header_row[col_index]
        if bank_name not in bank_name_to_id:
            print(f"Bank name '{bank_name}' not found in the banks table. Skipping.")                
            continue
        bank_id = bank_name_to_id[bank_name] 
        cell_value = row[col_index]

        is_applicable = cell_value is not None and str(cell_value).strip() != "-"
        local_term = str(cell_value).strip() if is_applicable else None


        cur.execute(
            """
                INSERT INTO bank_metric_mapping (bank_id, metric_alias, is_applicable, local_term)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (bank_id, metric_alias) DO UPDATE
                SET 
                    is_applicable = EXCLUDED.is_applicable,
                    local_term = EXCLUDED.local_term
            """,
            (bank_id, metric_alias, is_applicable, local_term)
        )
        print(f"Berhasil insert mapping: Bank ID {bank_id}, Metric Alias {metric_alias}, Local Term {local_term}")

print("Data inserted successfully into the bank_metric_mapping table.")


conn.commit()
cur.close()
conn.close()