import streamlit as st
from data_access import get_metrics
from labels import REASON_LABELS, STATUS_LABELS
from notes import list_flags, ALLOWED_TRANSITIONS, change_status

st.set_page_config(page_title="Metrik Ditandai", layout="wide")

st.title("Metrik Ditandai")

all_flags = list_flags()
if all_flags.empty:
    st.info("Belum ada metrik yang ditandai.")
    st.stop()

banks = ["Semua"] + sorted(all_flags["bank_name"].unique().tolist())
periods = ["Semua"] + sorted(all_flags["period_date"].unique().tolist(), reverse=True)
statuses = ["Semua"] + list(STATUS_LABELS)

selected_bank = st.sidebar.selectbox("Pilih bank", banks)
selected_period = st.sidebar.selectbox("Pilih periode", periods)
selected_status = st.sidebar.selectbox(
    "Pilih status",
    statuses,
    format_func=lambda s: s if s == "Semua" else STATUS_LABELS[s],
)

flags_df = list_flags(
    bank_name=None if selected_bank == "Semua" else selected_bank,
    period_date=None if selected_period == "Semua" else selected_period,
    status=None if selected_status == "Semua" else selected_status,
)


st.caption(f"Menampilkan {len(flags_df)} dari {len(all_flags)} tanda.")
if flags_df.empty:
    st.info("Tidak ada tanda yang cocok dengan filter.")
    st.stop()

@st.cache_data(ttl=300)
def load_names(bank, period):
    df = get_metrics(bank, period)
    return dict(zip(df["metric_alias"], df["metric_name"]))

names = {}
try:
    for bank, period in flags_df[["bank_name", "period_date"]].drop_duplicates().itertuples(index=False):
        names[(bank, period)] = load_names(bank, period)
except Exception:
    st.warning("Nama metrik tidak dapat dimuat; menampilkan alias.")

view = flags_df.assign(
    reason = flags_df["reason"].map(REASON_LABELS),
    status = flags_df["status"].map(STATUS_LABELS),
    metric_name = [
        names.get((b, p), {}).get(a, a)
        for b, p, a in zip(
            flags_df["bank_name"], flags_df["period_date"], flags_df["metric_alias"]
        )
    ],
).fillna("-")

table_version = st.session_state.get("table_version",0)
table_key = f"flags-{selected_bank}-{selected_period}-{selected_status}-{table_version}"
event = st.dataframe(
    view,
    hide_index=True,
    column_order=[
        "id", "bank_name", "period_date", "metric_name", "metric_alias", "value_at_flag",
        "reason", "note", "flagged_by", "created_at", "status",
        "updated_by", "updated_at",
    ],
    column_config={
        "id": st.column_config.NumberColumn("No.", pinned=True),
        "bank_name": st.column_config.TextColumn("Bank", pinned=True),
        "period_date": st.column_config.TextColumn("Periode"),
        "metric_name": st.column_config.TextColumn("Nama metrik"),
        "metric_alias": st.column_config.TextColumn("Alias metrik"),
        "value_at_flag": st.column_config.TextColumn("Nilai saat ditandai"),
        "reason": st.column_config.TextColumn("Alasan"),
        "note": st.column_config.TextColumn("Catatan"),
        "flagged_by": st.column_config.TextColumn("Ditandai oleh"),
        "created_at": st.column_config.TextColumn("Waktu ditandai"),
        "status": st.column_config.TextColumn("Status"),
        "updated_by": st.column_config.TextColumn("Diubah oleh"),
        "updated_at": st.column_config.TextColumn("Waktu diubah"),

    },
    key = table_key,
    on_select= "rerun",
    selection_mode="single-row",
)
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))
selected_rows = event.selection.rows
if not selected_rows:
    st.caption(f"Pilih satu baris untuk mengubah statusnya.")
    st.stop()

row = flags_df.iloc[selected_rows[0]]
st.subheader("Ubah status")
metric_name = view.iloc[selected_rows[0]]["metric_name"]
st.write(
    f"No. {row['id']}: {row['bank_name']}, {row['period_date']}, "
    f"{metric_name} ({row['metric_alias']}), "
    f"status sekarang: {STATUS_LABELS[row['status']]}"
)

current_status = row["status"]
if current_status == "done":
    st.info("Flag ini sudah selesai dan tidak bisa diubah lagi.")
    st.stop()
options = list(ALLOWED_TRANSITIONS[current_status])
with st.form("form_ubah_status"):
    new_status = st.selectbox(
        "Status tujuan",
        options,
        format_func=lambda s: STATUS_LABELS[s],
    )
    updated_by = st.text_input("Nama pengubah")
    submitted = st.form_submit_button("Simpan status")

if submitted:
    try:
        change_status(int(row["id"]), new_status, updated_by)
    except ValueError as e:
        st.error(str(e))
    else:
        st.session_state["flash"] = "Status diperbarui."
        st.session_state["table_version"] = table_version + 1
        st.rerun()
