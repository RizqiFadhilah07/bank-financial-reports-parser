import pandas as pd
import re

from db import get_connection

def _query_df(sql, params=()):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        columns = [c[0] for c in cur.description]
        rows = [tuple(r) for r in cur.fetchall()]
        return pd.DataFrame(rows, columns=columns)
    finally:
        conn.close()

def _samarkan_path(teks):
    if teks is None:
        return teks
    return re.sub(r"[A-Za-z]:\\(?:[^\\\s]+\\)*([^\\\s]+)", r"\1", teks)

def get_banks():
    return _query_df(
        """
        SELECT bank_id, bank_name, bank_type, period_type, is_active
        FROM banks
        ORDER BY bank_name
        """
    )

def get_reports():
    df = _query_df(
        """
        SELECT r.report_id, b.bank_name, r.period_date, r.status, r.error_message
        FROM dbo.financial_reports r
        JOIN dbo.banks b
        ON r.bank_id = b.bank_id
        ORDER BY b.bank_name, r.period_date
        """
    )
    df["error_message"] = df["error_message"].map(_samarkan_path)
    return df

def get_metrics(bank_name, period_date):
    return _query_df(
        """
        SELECT mm.category, mm.sub_category, mm.metric_order,
               d.metric_alias, mm.metric_name, d.value, d.sign_type, d.raw_text
        FROM dbo.financial_data d
        JOIN dbo.financial_reports r ON r.report_id = d.report_id
        JOIN dbo.banks b ON b.bank_id = r.bank_id
        JOIN dbo.master_metrics mm ON mm.metric_alias = d.metric_alias
        WHERE b.bank_name = ? AND r.period_date = ?
        ORDER BY mm.metric_order
        """,
        (bank_name, period_date),
    )


def naming_metric(df, kamus):
    hasil = df.copy()
    adalah_hilang = hasil["rule"] == "metric_hilang"
    hasil.loc[adalah_hilang, "detail"] = hasil.loc[adalah_hilang, "detail"].map(
        lambda alias: f"{kamus[alias]} ({alias})" if alias in kamus else alias
    )
    return hasil


def get_metric_dict():
    df = _query_df("SELECT metric_alias, metric_name FROM dbo.master_metrics")
    return dict(zip(df["metric_alias"], df["metric_name"]))


def get_findings(month=None):
    import validate

    conn = get_connection()
    try:
        cur = conn.cursor()
        rules = validate.run_rules(cur,month)
        cur.close()
    finally:
        conn.close()

    rows = []
    for rule, findings in rules:
        for bank, period, detail in findings:
            rows.append((rule, bank, period, detail))
    df = pd.DataFrame(rows, columns=["rule", "bank_name", "period_date", "detail"])
    return naming_metric(df, get_metric_dict())