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

@st.cache_data
def load_metrics(bank_name, period_date):
    return get_metrics(bank_name, period_date)

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

metrics_df = load_metrics(selected_bank, selected_period)
metrics_df["value"] = pd.to_numeric(metrics_df["value"])
categories = ["Semua"] + sorted(metrics_df["category"].unique().tolist())
selected_category = st.selectbox("Pilih kategori", categories)
if selected_category != "Semua":
    metrics_df = metrics_df[metrics_df["category"] == selected_category]
sub_categories = ["Semua"] + sorted(metrics_df["sub_category"].unique().tolist())
selected_sub_category = st.selectbox("Pilih sub-kategori", sub_categories)
if selected_sub_category != "Semua":
    metrics_df = metrics_df[metrics_df["sub_category"] == selected_sub_category]
st.write("Jumlah baris:", len(metrics_df))
st.dataframe(metrics_df)
