import streamlit as st
import pandas as pd
from data_access import get_banks, get_reports, get_metrics

st.set_page_config(page_title="Bank Reports", layout="wide")

@st.cache_data
def load_banks():
    return get_banks()

@st.cache_data
def load_reports():
    return get_reports()

st.title("Bank Financial Reports")

banks_df = load_banks()
bank_names = banks_df['bank_name'].tolist()

selected_bank = st.selectbox("Pilih bank", bank_names)
st.write("Bank terpilih: ", selected_bank)

reports_df = load_reports()
bank_reports = reports_df[reports_df["bank_name"] == selected_bank]
periods = bank_reports["period_date"].tolist()

selected_period = st.selectbox("Pilih periode", periods)
st.write("Periode terpilih:", selected_period)

metrics_df = get_metrics(selected_bank, selected_period)
metrics_df["value"] = pd.to_numeric(metrics_df["value"])
st.write("Jumlah baris:", len(metrics_df))
st.dataframe(metrics_df)