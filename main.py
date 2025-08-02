import streamlit as st
import pandas as pd
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime

# ---------- konfigurasi ----------
NAMA_PEMBAYAR = ["Rizal", "Fikrie", "Rendika", "Thesi", "Nanda", "Ryanta"]
KEPERLUAN = [
    "Iuran bulanan",
    "Donasi",
    "Pembelian bahan",
    "Transport",
    "Lain-lain"
]

st.set_page_config(
    page_title="Pendataan Keuangan",
    page_icon="💰",
    layout="wide"
)

st.title("Pendataan Keuangan: Rizal, Fikrie, Rendika, Thesi, Nanda, Ryanta")

# ---------- cek secrets ----------
if "MONGO_URI" not in st.secrets:
    st.error("MONGO_URI belum diset di .streamlit/secrets.toml. Cek file secrets.toml.")
    st.stop()

# ---------- koneksi MongoDB via st.secrets ----------
@st.cache_resource(show_spinner=False)
def get_collection():
    uri = st.secrets["MONGO_URI"]
    client = MongoClient(uri)
    db = client["bali"]           # sesuai permintaan: GaitDB
    collection = db["bali"]    # sesuai permintaan: gait_data
    return collection

collection = get_collection()

# ---------- helper ----------
def tambah_transaksi(nama, jumlah, keperluan, catatan=""):
    doc = {
        "nama": nama,
        "jumlah": float(jumlah),
        "keperluan": keperluan,
        "catatan": catatan,
        "waktu": datetime.utcnow()
    }
    collection.insert_one(doc)

def ambil_semua_transaksi():
    cursor = collection.find().sort("waktu", -1)
    df = pd.DataFrame(list(cursor))
    if not df.empty:
        df["waktu"] = pd.to_datetime(df["waktu"])
        df["jumlah"] = df["jumlah"].astype(float)
        df = df.rename(columns={"_id": "id"})
        df["id"] = df["id"].astype(str)
    return df

def rekap_per_orang(df: pd.DataFrame):
    if df.empty:
        return pd.DataFrame()
    summary = (
        df.groupby("nama")
        .agg(
            total_dibayar=pd.NamedAgg(column="jumlah", aggfunc="sum"),
            jumlah_transaksi=pd.NamedAgg(column="jumlah", aggfunc="count"),
        )
        .reset_index()
    )
    return summary

# ---------- form input ----------
with st.form("form_input"):
    col1, col2, col3 = st.columns(3)
    with col1:
        nama = st.selectbox("Pilih Nama", NAMA_PEMBAYAR)
    with col2:
        jumlah = st.number_input("Jumlah Bayar (Rp)", min_value=0.0, format="%.2f")
    with col3:
        keperluan = st.selectbox("Keperluan Pembayaran", KEPERLUAN)
    catatan = st.text_input("Catatan (opsional)")
    submitted = st.form_submit_button("Simpan")

if submitted:
    if jumlah <= 0:
        st.warning("Jumlah harus lebih dari 0.")
    else:
        try:
            tambah_transaksi(nama, jumlah, keperluan, catatan)
            st.success(f"Transaksi {nama} sebesar Rp {jumlah:,.2f} untuk '{keperluan}' tersimpan.")
        except Exception as e:
            st.error(f"Gagal menyimpan transaksi: {e}")

st.divider()

# ---------- ambil & tampilkan data ----------
df = ambil_semua_transaksi()

# Rekap keseluruhan
st.subheader("Rekap Keseluruhan")
if df.empty:
    st.info("Belum ada transaksi yang tercatat.")
else:
    summary = rekap_per_orang(df)
    st.dataframe(
        summary.sort_values("total_dibayar", ascending=False).reset_index(drop=True),
        use_container_width=True
    )
    total_semua = df["jumlah"].sum()
    st.markdown(f"**Total semua pembayaran: Rp {total_semua:,.2f}**")

st.divider()

# Tabel per orang
st.subheader("Tabel Per Orang")
selected_person = st.selectbox("Pilih orang untuk melihat detail", ["Semua"] + NAMA_PEMBAYAR)

if df.empty:
    st.write("Tidak ada data untuk ditampilkan.")
else:
    if selected_person != "Semua":
        df_person = df[df["nama"] == selected_person].copy()
        if df_person.empty:
            st.write(f"Tidak ada transaksi untuk {selected_person}.")
        else:
            st.write(f"Transaksi {selected_person}:")
            st.dataframe(df_person.sort_values("waktu", ascending=False).reset_index(drop=True))
            subtotal = df_person["jumlah"].sum()
            st.markdown(f"**Total {selected_person}: Rp {subtotal:,.2f}**")
    else:
        st.write("Semua transaksi:")
        st.dataframe(df.sort_values("waktu", ascending=False).reset_index(drop=True))

# Admin / debugging: hapus transaksi
with st.expander("🛠️ Hapus transaksi (admin/debug)"):
    st.write("Hati-hati: ini akan menghapus data permanen.")
    to_delete_id = st.text_input("Masukkan ID transaksi untuk dihapus")
    if st.button("Hapus"):
        if not to_delete_id:
            st.warning("Masukkan ID dulu.")
        else:
            try:
                result = collection.
