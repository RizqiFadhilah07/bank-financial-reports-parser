import pandas as pd
import streamlit as st

from data_access import get_banks
from db import get_connection
from preview import extract_preview

st.set_page_config(page_title="Upload PDF", layout="wide")

@st.cache_data
def load_banks():
    return get_banks()

st.title("Upload PDF")
st.caption("Unggah satu PDF laporan, lalu lihat hasil ekstraksinya. Hasil TIDAK disimpan ke database.")

banks_df = load_banks()
bank_name = st.selectbox("Bank", sorted(banks_df["bank_name"]))
pdf_file = st.file_uploader("Unggah PDF", type="pdf")

if st.button("Ekstrak", type="primary"):
    if pdf_file is None:
        st.warning("Upload file PDF terlebih dahulu")
    else:
        conn = get_connection()
        try:
            with st.spinner("Membaca PDF..."):
                hasil = extract_preview(conn, bank_name, pdf_file)
            st.session_state["hasil"] = hasil
            st.session_state["hasil_bank"] = bank_name
        except Exception as e:
            st.session_state.pop("hasil", None)
            st.error(f"Gagal mengekstrak: {e}")
        finally:
            conn.close()

if "hasil" in st.session_state:
    hasil = st.session_state["hasil"]
    if hasil["nama_cocok"] is False:
        st.warning(
            "Nama bank yang Anda pilih tidak ditemukan di isi PDF. "
            "Pastikan bank dan file yang diunggah sudah sesuai."
        )
    df = pd.DataFrame(
        hasil["results"],
        columns=["metric_order", "metric_alias", "value", "raw_text", "sign_type"],
    )
    bank = st.session_state["hasil_bank"]
    nama_cocok = hasil["nama_cocok"]
    if nama_cocok is None:
        cek_nama = "Tidak dicek"
    elif nama_cocok:
        cek_nama = "Cocok"
    else:
        cek_nama = "Tidak cocok"

    if nama_cocok is None:
        st.info(
            f"Nama bank {bank} tidak bisa dicek otomatis dari isi PDF. "
            "Pastikan sendiri file yang diunggah sudah sesuai."
        )

    st.subheader(f"Hasil ekstraksi: {bank}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Metrik ditemukan", len(df), border=True)
    col2.metric("Metrik tidak ditemukan", len(hasil["missing"]), border=True)
    col3.metric("Nama bank di PDF", cek_nama, border=True)
    st.dataframe(
        df,
        width="stretch",
        column_order=["metric_order", "metric_alias", "value", "sign_type", "raw_text"],
        hide_index=True,
        column_config={
            "metric_order": st.column_config.NumberColumn("No. urut"),
            "metric_alias": st.column_config.TextColumn("Alias metrik"),
            "value": st.column_config.NumberColumn("Nilai (juta Rp)", format="localized"),
            "sign_type": st.column_config.TextColumn("Tanda"),
            "raw_text": st.column_config.TextColumn("Teks asli"),
        }
    )
    if hasil["missing"]:
        st.warning(f"{len(hasil['missing'])} metrik tidak ditemukan di PDF ini.")
        with st.expander("Lihat daftar metrik yang tidak ditemukan"):
            st.markdown("\n".join(f"- `{m}`" for m in hasil["missing"]))
    else:
        st.success("Semua metrik ditemukan.")

    st.download_button(
        "Unduh CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"hasil_ekstraksi_{bank.replace(' ', '_')}.csv",
        mime="text/csv",
    )