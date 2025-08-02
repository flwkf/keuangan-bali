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

st.title("Pendataan Keuangan & Pembagian Pengeluaran Bersama")

# ---------- cek secrets ----------
if "MONGO_URI" not in st.secrets:
    st.error("MONGO_URI belum diset di .streamlit/secrets.toml. Cek file secrets.toml.")
    st.stop()

# ---------- koneksi MongoDB via st.secrets ----------
@st.cache_resource(show_spinner=False)
def get_collection():
    uri = st.secrets["MONGO_URI"]
    client = MongoClient(uri)
    db = client["GaitDB"]           # nama database
    collection = db["gait_data"]    # nama collection
    return collection

collection = get_collection()

# ---------- helper ----------
def tambah_transaksi(nama, jumlah, keperluan, tipe="masuk", catatan=""):
    # tipe: "masuk" atau "keluar"
    doc = {
        "nama": nama,
        "jumlah": float(jumlah),
        "keperluan": keperluan,
        "tipe": tipe,
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
    # Pisahkan masuk dan keluar
    masuk = df[df["tipe"] == "masuk"].groupby("nama").agg(total_masuk=pd.NamedAgg(column="jumlah", aggfunc="sum"))
    keluar = df[df["tipe"] == "keluar"].groupby("nama").agg(total_keluar=pd.NamedAgg(column="jumlah", aggfunc="sum"))
    summary = pd.concat([masuk, keluar], axis=1).fillna(0).reset_index()
    summary["netto"] = summary["total_masuk"] - summary["total_keluar"]
    summary["total_masuk"] = summary["total_masuk"].astype(float)
    summary["total_keluar"] = summary["total_keluar"].astype(float)
    summary["netto"] = summary["netto"].astype(float)
    summary["jumlah_transaksi"] = df.groupby("nama").size().reindex(summary["nama"]).fillna(0).astype(int).values
    return summary

# ---------- form input pemasukan ----------
with st.expander("Tambah Pemasukan / Pembayaran Individu"):
    with st.form("form_input"):
        col1, col2, col3 = st.columns(3)
        with col1:
            nama = st.selectbox("Pilih Nama", NAMA_PEMBAYAR, key="pemasukan_nama")
        with col2:
            jumlah = st.number_input("Jumlah Bayar (Rp)", min_value=0.0, format="%.2f", key="pemasukan_jumlah")
        with col3:
            keperluan = st.selectbox("Keperluan Pembayaran", KEPERLUAN, key="pemasukan_keperluan")
        catatan = st.text_input("Catatan (opsional)", key="pemasukan_catatan")
        submitted = st.form_submit_button("Simpan Pemasukan")

    if submitted:
        if jumlah <= 0:
            st.warning("Jumlah harus lebih dari 0.")
        else:
            try:
                tambah_transaksi(nama, jumlah, keperluan, tipe="masuk", catatan=catatan)
                st.success(f"Pemasukan: {nama} bayar Rp {jumlah:,.2f} untuk '{keperluan}' tersimpan.")
            except Exception as e:
                st.error(f"Gagal menyimpan pemasukan: {e}")

st.divider()

# ---------- form input pengeluaran bersama ----------
with st.expander("Tambah Pengeluaran Bersama (dibagi rata)"):
    with st.form("form_pengeluaran"):
        total_pengeluaran = st.number_input("Total Pengeluaran Keseluruhan (Rp)", min_value=0.0, format="%.2f")
        keperluan_peng = st.text_input("Keperluan Pengeluaran", value="Pengeluaran bersama")
        catatan_peng = st.text_input("Catatan (opsional)", value="", help="Misal: beli bahan, bensin, dsb.")
        submitted_peng = st.form_submit_button("Bagi dan Simpan Pengeluaran")

    if submitted_peng:
        if total_pengeluaran <= 0:
            st.warning("Total pengeluaran harus lebih dari 0.")
        else:
            share = total_pengeluaran / len(NAMA_PEMBAYAR)
            try:
                for nama_p in NAMA_PEMBAYAR:
                    # catat tiap orang sebagai pengeluaran (keluar)
                    tambah_transaksi(
                        nama=nama_p,
                        jumlah=share,
                        keperluan=f"{keperluan_peng} (share)",
                        tipe="keluar",
                        catatan=catatan_peng
                    )
                st.success(f"Pengeluaran Rp {total_pengeluaran:,.2f} dibagi rata ke {len(NAMA_PEMBAYAR)} orang, masing-masing Rp {share:,.2f}.")
            except Exception as e:
                st.error(f"Gagal menyimpan pengeluaran bersama: {e}")

st.divider()

# ---------- ambil & tampilkan data ----------
df = ambil_semua_transaksi()

# Rekap keseluruhan
st.subheader("Rekap Keseluruhan per Orang")
if df.empty:
    st.info("Belum ada transaksi.")
else:
    summary = rekap_per_orang(df)
    st.dataframe(
        summary[
            ["nama", "total_masuk", "total_keluar", "netto", "jumlah_transaksi"]
        ].sort_values("netto", ascending=False).reset_index(drop=True),
        use_container_width=True
    )
    total_masuk_all = df[df["tipe"] == "masuk"]["jumlah"].sum()
    total_keluar_all = df[df["tipe"] == "keluar"]["jumlah"].sum()
    netto_all = total_masuk_all - total_keluar_all
    st.markdown(f"**Total semua pemasukan: Rp {total_masuk_all:,.2f}**  \n"
                f"**Total semua pengeluaran: Rp {total_keluar_all:,.2f}**  \n"
                f"**Netto keseluruhan: Rp {netto_all:,.2f}**")

st.divider()

# Tabel per orang / semua
st.subheader("Detail Transaksi")
selected_person = st.selectbox("Pilih orang untuk lihat detail", ["Semua"] + NAMA_PEMBAYAR)

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
            masuk = df_person[df_person["tipe"] == "masuk"]["jumlah"].sum()
            keluar = df_person[df_person["tipe"] == "keluar"]["jumlah"].sum()
            netto = masuk - keluar
            st.markdown(
                f"**Total masuk:** Rp {masuk:,.2f}  \n"
                f"**Total keluar:** Rp {keluar:,.2f}  \n"
                f"**Netto:** Rp {netto:,.2f}"
            )
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
                result = collection.delete_one({"_id": ObjectId(to_delete_id.strip())})
                if result.deleted_count:
                    st.success("Transaksi terhapus.")
                else:
                    st.error("ID tidak ditemukan.")
            except Exception as e:
                st.error(f"Gagal menghapus: {e}")
