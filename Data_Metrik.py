import streamlit as st
import pandas as pd
from data_access import get_banks, get_metrics, get_reports
from labels import REASON_LABELS, STATUS_LABELS
from notes import add_flag, list_flags

st.set_page_config(page_title="Bank Reports", layout="wide")

@st.cache_data(ttl=300)
def load_banks():
    return get_banks()

@st.cache_data(ttl=300)
def load_reports():
    return get_reports()

@st.cache_data(ttl=300)
def load_metrics(bank_name, period_date):
    return get_metrics(bank_name, period_date)

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
         "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

def format_periode(d):
    return f"{BULAN[d.month - 1]} {d.year}"

COLUMN_CONFIG = {
    "metric_name": st.column_config.TextColumn("Nama metrik", pinned=True),
    "flag_status": st.column_config.TextColumn("Ditandai", help="Status tanda yang belum selesai. '-' berarti belum ditandai.",),
    "value": st.column_config.NumberColumn(
        "Nilai (juta Rp)",
        format="localized",
        help="Tanpa tanda, dalam juta rupiah. Tandanya ada di kolom Tanda. Angka kosong di PDF disimpan sebagai 0.",
    ),
    "sign_type": st.column_config.TextColumn(
        "Tanda",
        help="Tanda nilai: + (positif) atau - (negatif).",
    ),
    "category": st.column_config.TextColumn("Kategori"),
    "sub_category": st.column_config.TextColumn("Sub-kategori"),
    "raw_text": st.column_config.TextColumn(
        "Teks asli",
        help="Potongan teks PDF tempat metrik ditemukan: label beserta angkanya, atau label saja bila tidak ada angka.",
    ),
    "metric_alias": st.column_config.TextColumn("Alias metrik"),
    "metric_order": st.column_config.NumberColumn("No. urut"),
}

st.title("Bank Financial Reports")

banks_df = load_banks()
bank_names = banks_df["bank_name"].tolist()

selected_bank = st.sidebar.selectbox("Pilih bank", bank_names)

reports_df = load_reports()
bank_reports = reports_df[reports_df["bank_name"] == selected_bank]
periods = sorted(bank_reports["period_date"], reverse=True)

selected_period = st.sidebar.selectbox("Pilih periode", periods, format_func=format_periode)
if not periods:
    st.info("Belum ada laporan untuk bank ini.")
    st.stop()
report_status = bank_reports.loc[bank_reports["period_date"] == selected_period, "status"].iloc[0]

metrics_df = load_metrics(selected_bank, selected_period)
metrics_df["value"] = pd.to_numeric(metrics_df["value"])
total_metrics = len(metrics_df)

categories = ["Semua"] + sorted(metrics_df["category"].unique().tolist())
selected_category = st.sidebar.selectbox("Pilih kategori", categories)
if selected_category != "Semua":
    metrics_df = metrics_df[metrics_df["category"] == selected_category]

sub_categories = ["Semua"] + sorted(metrics_df["sub_category"].unique().tolist())
selected_sub_category = st.sidebar.selectbox("Pilih sub-kategori", sub_categories)
if selected_sub_category != "Semua":
    metrics_df = metrics_df[metrics_df["sub_category"] == selected_sub_category]

keyword = st.sidebar.text_input("Cari metrik")
if keyword:
    mask = (
        metrics_df["metric_name"].str.contains(keyword, case=False, na=False, regex=False) |
        metrics_df["metric_alias"].str.contains(keyword, case=False, na=False, regex=False)
    )
    metrics_df = metrics_df[mask]

open_flags = list_flags(selected_bank, selected_period)
open_flags = open_flags[open_flags["status"] != "done"]
flag_by_alias = dict(zip(open_flags["metric_alias"], open_flags["status"]))
metrics_df = metrics_df.assign(
    flag_status=metrics_df["metric_alias"].map(flag_by_alias).map(STATUS_LABELS).fillna("-")
)
selected_columns = st.sidebar.multiselect(
    "Kolom yang ditampilkan",
    list(COLUMN_CONFIG),
    default=list(COLUMN_CONFIG),
    format_func=lambda c: COLUMN_CONFIG[c]["label"],
    placeholder="Pilih kolom",
)

st.subheader(f"{selected_bank} - {format_periode(selected_period)}")
col1, col2, col3 = st.columns(3)
col1.metric("Status laporan", report_status, border=True)
col2.metric("Metrik di laporan", total_metrics, border=True)
col3.metric("Baris ditampilkan", len(metrics_df), border=True)
if not selected_columns:
    st.info("Pilih minimal satu kolom di sidebar untuk menampilkan tabel.")
    st.stop()
table_version = st.session_state.get("metric_table_version", 0)
table_key = f"tabel_metrik_{selected_bank}_{selected_period}_{selected_category}_{selected_sub_category}_{keyword}_{table_version}"
event = st.dataframe(
    metrics_df,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key=table_key,
    width="stretch",
    column_order=[c for c in COLUMN_CONFIG if c in selected_columns],
    column_config=COLUMN_CONFIG,
)
if "metric_flash" in st.session_state:
    st.success(st.session_state.pop("metric_flash"))
selected_rows = event.selection.rows
if selected_rows:
    row = metrics_df.iloc[selected_rows[0]]
    st.subheader("Tandai Metrik")
    st.write(f"{row['metric_name']} ({row['metric_alias']}), nilai {row['value']:,.2f}")
    with st.form("form_tandai"):
        flagged_by = st.text_input("Nama Pengisi")
        reason = st.selectbox(
            "Alasan",
            list(REASON_LABELS),
            format_func=lambda r: REASON_LABELS[r],
        )
        note = st.text_input("Catatan (opsional)", max_chars=200)
        submitted = st.form_submit_button("Simpan notes")
    if submitted:
        try:
            flag_id = add_flag(
                selected_bank,
                selected_period,
                row["metric_alias"],
                row["value"],
                reason,
                note,
                flagged_by,
            )
        except ValueError as e:
            st.error(str(e))
        else:
            st.session_state["metric_flash"] = f"Tanda tersimpan (nomor {flag_id})."
            st.session_state["metric_table_version"] = table_version + 1
            st.rerun()
