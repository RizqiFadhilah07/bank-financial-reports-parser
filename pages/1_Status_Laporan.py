import streamlit as st
from data_access import get_reports, get_findings

st.set_page_config(page_title="Status Laporan", layout="wide")

@st.cache_data
def load_reports():
    return get_reports()

@st.cache_data
def load_findings():
    return get_findings()

def color_status(value):
    if value == "failed":
        return "background-color: #8b2e2e; color: white"
    if value == "downloaded":
        return "background-color: #1f6f43; color: white"
    return ""


st.title("Status Laporan")

reports_df = load_reports()
findings_df = load_findings()
col1,col2,col3,col4 = st.columns(4)
col1.metric("Total laporan", len(reports_df), border=True)
col2.metric("Parsed", int((reports_df["status"] == "parsed").sum()), border=True)
col3.metric("Bermasalah", int((reports_df["status"] != "parsed").sum()), border=True)
col4.metric("Temuan validasi", len(findings_df), border=True)
status_pivot = reports_df.pivot(index="bank_name", columns="period_date", values="status").fillna("-")
styled_pivot = status_pivot.style.map(color_status)
st.dataframe(styled_pivot, width="stretch", column_config={"bank_name": "Bank"})
st.caption("Merah: laporan gagal. Hijau: laporan sudah diunduh tetapi belum diproses. Tanda -: laporan untuk periode itu tidak ada.")


st.subheader("Laporan Bermasalah")
problem_df = reports_df[reports_df["status"] != "parsed"]
if problem_df.empty:
    st.success("Semua laporan berstatus parsed.")
else:
    st.dataframe(
        problem_df[["bank_name", "period_date", "status", "error_message"]],
        hide_index=True,
        width="stretch",
        column_config={
            "bank_name": st.column_config.TextColumn("Bank"),
            "period_date": st.column_config.DateColumn("Periode", format="YYYY-MM-DD"),
            "status": st.column_config.TextColumn("Status"),
            "error_message": st.column_config.TextColumn("Pesan error"),
        },
    )

st.subheader("Temuan Validasi")
if findings_df.empty:
    st.success("Semua aturan validasi lolos, tidak ada temuan.")
else:
    st.dataframe(
        findings_df,
        hide_index=True,
        width="stretch",
        column_config={
            "rule": st.column_config.TextColumn("Aturan"),
            "bank_name": st.column_config.TextColumn("Bank"),
            "period_date": st.column_config.DateColumn("Periode", format="YYYY-MM-DD"),
            "detail": st.column_config.TextColumn("Detail"),
        },
    )