import streamlit as st

from data_access import get_banks, get_reports

st.set_page_config(page_title="Bank Reports", layout="wide")

st.title("Bank Financial Reports")

banks_df = get_banks()
bank_names = banks_df['bank_name'].tolist()

selected_bank = st.selectbox("Pilih bank", bank_names)
st.write("Bank terpilih: ", selected_bank)

reports_df = get_reports()
bank_reports = reports_df[reports_df["bank_name"] == selected_bank]
periods = bank_reports["period_date"].tolist()

selected_period = st.selectbox("Pilih periode", periods)
st.write("Periode terpilih:", selected_period)