import streamlit as st
from data_access import get_reports

st.set_page_config(page_title="Status Laporan", layout="wide")

@st.cache_data
def load_reports():
    return get_reports()

def color_status(value):
    if value == "failed":
        return "background-color: #8b2e2e"
    return ""

st.title("Status Laporan")

reports_df = load_reports()
status_pivot = reports_df.pivot(index="bank_name", columns="period_date", values="status")
st.dataframe(status_pivot.style.map(color_status), width="stretch")