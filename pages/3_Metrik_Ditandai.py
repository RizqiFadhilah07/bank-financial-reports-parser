import streamlit as st
from notes import list_flags, ALLOWED_TRANSITIONS, change_status

st.set_page_config(page_title="Metrik Ditandai", layout="wide")

REASON_LABELS = {
    "value_mismatch": "Nilai tidak sesuai PDF",
    "wrong_sign_type": "Tanda salah",
    "other": "Lainnya",
}
STATUS_LABELS = {
    "needs_check": "Perlu dicek",
    "on_review": "On review",
    "done": "Done",
}

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


view = flags_df.assign(
    reason = flags_df["reason"].map(REASON_LABELS),
    status = flags_df["status"].map(STATUS_LABELS),
).fillna("-")

table_key = f"flags-{selected_bank}-{selected_period}-{selected_status}"
event = st.dataframe(
    view,
    hide_index=True,
    column_order=[
        "id", "bank_name", "period_date", "metric_alias", "value_at_flag",
        "reason", "note", "flagged_by", "created_at", "status",
        "updated_by", "updated_at",
    ],
    column_config={
        "id": st.column_config.NumberColumn("No."),
        "bank_name": st.column_config.TextColumn("Bank"),
        "period_date": st.column_config.TextColumn("Periode"),
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
selected_rows = event.selection.rows
if not selected_rows:
    st.caption(f"Pilih satu baris untuk mengubah statusnya.")
    st.stop()

row = flags_df.iloc[selected_rows[0]]
st.subheader("Ubah status")
st.write(
    f"No. {row['id']}: {row['bank_name']}, {row['period_date']}, "
    f"{row['metric_alias']} (status sekarang: {STATUS_LABELS[row['status']]})"
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
        st.success("Status diperbarui.")
        st.stop()