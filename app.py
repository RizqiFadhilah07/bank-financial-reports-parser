import streamlit as st

from data_access import get_banks

st.set_page_config(page_title="Bank Reports", layout="wide")

st.title("Bank Financial Reports")

banks_df = get_banks()
bank_names = banks_df['bank_name'].tolist()

selected_bank = st.selectbox("Pilih bank", bank_names)
st.write("Bank terpilih: ", selected_bank)