# import os
import uuid
import streamlit as st
import pandas as pd
from pymongo import MongoClient
from bson.objectid import ObjectId
from gridfs import GridFS
from datetime import datetime

# ---------- konfigurasi ----------
NAMA_PEMBAYAR = ["Rizal", "Fikrie", "Rendika", "Thesi", "Nanda", "Ryanta"]

st.set_page_config(page_title="Keuangan Bersama", page_icon="💰", layout="wide")
st.title("Pendataan Keuangan & Bukti Transfer")

# ---------- cek secrets ----------
if "MONGO_URI" not in st.secrets:
    st.error("MONGO_URI belum diset di .streamlit/secrets.toml.")
    st.stop()
if "ADMIN_PASSWORD" not in st.secrets:
    st.error("ADMIN_PASSWORD belum diset di .streamlit/secrets.toml.")
    st.stop()

# ---------- koneksi MongoDB ----------
@st.cache_resource(show_spinner=False)
def get_collection():
    client = MongoClient(st.secrets["MONGO_URI"])
    db = client["bali"]
    fs = GridFS(db)
    return db["bali"], fs

collection, fs = get_collection()

# ---------- helper ----------
def tambah_transaksi(nama, jumlah, keperluan, tipe="masuk", catatan="", bukti_file=None, bukti_id=None):
    if not bukti_id and bukti_file:
        filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}.jpg"
        bukti_id = fs.put(bukti_file.getvalue(), filename=filename, content_type=bukti_file.type)

    doc = {
        "nama": nama,
        "jumlah": float(jumlah),
        "keperluan": keperluan,
        "tipe": tipe,
        "catatan": catatan,
        "waktu": datetime.utcnow(),
        "bukti_id": bukti_id
    }
    collection.insert_one(doc)

def ambil_semua_transaksi():
    cursor = collection.find().sort("waktu", -1)
    df = pd.DataFrame(list(cursor))
    if df.empty:
        return df
    df["waktu"] = pd.to_datetime(df.get("waktu"), errors="coerce")
    df["jumlah"] = pd.to_numeric(df.get("jumlah"), errors="coerce").fillna(0.0)
    df["tipe"] = df.get("tipe", "masuk").fillna("masuk")
    df["nama"] = df.get("nama", "Unknown").fillna("Unknown")
    df = df.rename(columns={"_id": "id"})
    df["id"] = df["id"].astype(str)
    return df

def rekap_per_orang(df):
    if df.empty:
        return pd.DataFrame()
    masuk = df[df["tipe"] == "masuk"].groupby("nama").agg(total_masuk=("jumlah", "sum"))
    keluar = df[df["tipe"] == "keluar"].groupby("nama").agg(total_keluar=("jumlah", "sum"))
    summary = pd.concat([masuk, keluar], axis=1).fillna(0).reset_index()
    summary["Total Saldo"] = summary["total_masuk"] - summary["total_keluar"]
    summary["jumlah_transaksi"] = df.groupby("nama").size().reindex(summary["nama"]).fillna(0).astype(int).values
    return summary

def render_rekap(df, user_name, is_admin):
    st.subheader("Rekap & Ringkasan")

    if df.empty:
        st.info("Belum ada transaksi.")
        return

    pilihan_nama = ["Semua"] + NAMA_PEMBAYAR
    filter_nama = st.selectbox("Tampilkan untuk:", pilihan_nama, key="rekap_filter_nama")

    pilihan_tipe = st.selectbox("Tipe transaksi:", ["Semua", "masuk", "keluar"], key=f"rekap_filter_tipe_{'admin' if is_admin else 'user'}")

    df_filtered = df.copy()
    if filter_nama != "Semua":
        df_filtered = df_filtered[df_filtered["nama"] == filter_nama]
    if pilihan_tipe != "Semua":
        df_filtered = df_filtered[df_filtered["tipe"] == pilihan_tipe]

    summary = rekap_per_orang(df_filtered)

    if pilihan_tipe == "masuk":
        display_cols = ["nama", "total_masuk", "jumlah_transaksi"]
        sort_by = "total_masuk"
    elif pilihan_tipe == "keluar":
        display_cols = ["nama", "total_keluar", "jumlah_transaksi"]
        sort_by = "total_keluar"
    else:
        display_cols = ["nama", "total_masuk", "total_keluar", "Total Saldo", "jumlah_transaksi"]
        sort_by = "Total Saldo"

    st.markdown("**Rekap per orang:**")
    to_show = summary[display_cols].sort_values(sort_by, ascending=False)
    st.dataframe(to_show.reset_index(drop=True), use_container_width=True)

    total_masuk_all = df_filtered[df_filtered["tipe"] == "masuk"]["jumlah"].sum()
    total_keluar_all = df_filtered[df_filtered["tipe"] == "keluar"]["jumlah"].sum()
    total_saldo_all = total_masuk_all - total_keluar_all

    st.markdown(f"**Total pemasukan:** Rp {total_masuk_all:,.2f}")
    st.markdown(f"**Total pengeluaran:** Rp {total_keluar_all:,.2f}")
    st.markdown(f"**Total Saldo:** Rp {total_saldo_all:,.2f}")

    st.markdown("---")
    st.subheader("Bukti Transfer (sesuai filter)")
    if "bukti_id" in df_filtered.columns:
        df_with_bukti = df_filtered[df_filtered["bukti_id"].notnull()]
    else:
        df_with_bukti = pd.DataFrame()

    if df_with_bukti.empty:
        st.info("Tidak ada bukti untuk filter ini.")
    else:
        for _, row in df_with_bukti.iterrows():
            with st.expander(f"{row['nama']} | {'+' if row['tipe']=='masuk' else '-'}Rp {row['jumlah']:,.2f} | {row['keperluan']}"):
                st.write(f"Waktu: {row['waktu']}")
                st.write(f"Catatan: {row.get('catatan','')}")
                try:
                    image_data = fs.get(ObjectId(row["bukti_id"])).read()
                    st.image(image_data, caption=f"ID: {row['id']}", width=300)
                except Exception:
                    st.warning("Gagal menampilkan gambar dari database.")

# ---------- autentikasi ----------
st.sidebar.header("Masuk / Pilih Nama")
user_name = st.sidebar.selectbox("Pilih nama kamu", NAMA_PEMBAYAR)

is_admin = False
if user_name == "Rizal":
    pwd = st.sidebar.text_input("Password admin", type="password")
    if pwd and pwd == st.secrets["ADMIN_PASSWORD"]:
        is_admin = True
        st.sidebar.success("Login sebagai admin (Rizal)")
    elif pwd:
        st.sidebar.error("Password salah")
else:
    st.sidebar.info(f"Masuk sebagai {user_name}")

df = ambil_semua_transaksi()

# ---------- tampilan ----------
if is_admin:
    tab1, tab2, tab3, tab4 = st.tabs(["Pemasukan", "Pengeluaran", "Rekap", "Edit"])

    with tab1:
        st.subheader("Tambah Pemasukan (Admin)")
        with st.form("form_admin_masuk"):
            col1, col2 = st.columns(2)
            with col1:
                nama_in = st.selectbox("Nama", NAMA_PEMBAYAR)
            with col2:
                jumlah_in = st.number_input("Jumlah (Rp)", min_value=0.0, format="%.2f")
            catatan_in = st.text_input("Catatan")
            bukti_file = st.file_uploader("Upload Bukti", type=["jpg", "jpeg", "png"])
            submitted = st.form_submit_button("Simpan")

        if submitted:
            if jumlah_in <= 0 or not bukti_file:
                st.warning("Lengkapi jumlah dan bukti.")
            else:
                tambah_transaksi(nama_in, jumlah_in, "Pembayaran", tipe="masuk", catatan=catatan_in, bukti_file=bukti_file)
                st.success("Tersimpan.")

    with tab2:
        st.subheader("Tambah Pengeluaran Bersama")
        with st.form("form_pengeluaran"):
            total_pengeluaran = st.number_input("Total Pengeluaran", min_value=0.0, format="%.2f")
            keperluan_peng = st.text_input("Keperluan", value="Pengeluaran bersama")
            catatan_peng = st.text_input("Catatan")
            bukti_pengeluaran = st.file_uploader("Upload Bukti", type=["jpg", "jpeg", "png"])
            submitted_peng = st.form_submit_button("Simpan Pengeluaran")

        if submitted_peng:
            if total_pengeluaran <= 0:
                st.warning("Total pengeluaran tidak boleh nol.")
            else:
                share = total_pengeluaran / len(NAMA_PEMBAYAR)
                bukti_id = None
                if bukti_pengeluaran:
                    filename = f"pengeluaran_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}.jpg"
                    bukti_id = fs.put(bukti_pengeluaran.getvalue(), filename=filename, content_type=bukti_pengeluaran.type)
                for nama in NAMA_PEMBAYAR:
                    tambah_transaksi(nama, share, f"{keperluan_peng} (share)", tipe="keluar", catatan=catatan_peng, bukti_id=bukti_id)
                st.success("Pengeluaran berhasil dibagi.")

    with tab3:
        render_rekap(df, user_name, is_admin=True)

    # Tambahkan di tab4 (hanya admin yang bisa edit)
    with tab4:
        st.subheader("Edit / Hapus Transaksi")
    
        if df.empty:
            st.info("Belum ada transaksi.")
        else:
            # ----- EDIT TRANSAKSI -----
            pilihan = st.selectbox(
                "Pilih transaksi untuk diedit",
                options=df["id"].tolist(),
                format_func=lambda x: (
                    f"{x[:6]}... | {df.loc[df['id'] == x, 'nama'].values[0]} | "
                    f"{'+' if df.loc[df['id'] == x, 'tipe'].values[0]=='masuk' else '-'}Rp {df.loc[df['id'] == x, 'jumlah'].values[0]:,.2f} | "
                    f"{df.loc[df['id'] == x, 'keperluan'].values[0]}"
                )
            )
    
            if pilihan:
                try:
                    row = df[df["id"] == pilihan].iloc[0]
                except IndexError:
                    st.error("Data tidak ditemukan.")
                    st.stop()
    
                with st.form("form_edit_admin"):
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_nama = st.selectbox(
                            "Nama",
                            NAMA_PEMBAYAR,
                            index=NAMA_PEMBAYAR.index(row.get("nama", NAMA_PEMBAYAR[0])) if row.get("nama") in NAMA_PEMBAYAR else 0
                        )
                        edit_tipe = st.selectbox(
                            "Tipe",
                            ["masuk", "keluar"],
                            index=0 if row.get("tipe", "masuk") == "masuk" else 1
                        )
                    with col2:
                        edit_jumlah = st.number_input(
                            "Jumlah (Rp)",
                            value=float(row.get("jumlah", 0.0)),
                            format="%.2f"
                        )
                        edit_keperluan = st.text_input("Keperluan", value=row.get("keperluan", ""))
                    edit_catatan = st.text_input("Catatan", value=row.get("catatan", ""))
    
                    submitted_edit = st.form_submit_button("Simpan Perubahan")
    
                if submitted_edit:
                    try:
                        update_fields = {
                            "nama": edit_nama,
                            "jumlah": float(edit_jumlah),
                            "keperluan": edit_keperluan,
                            "tipe": edit_tipe,
                            "catatan": edit_catatan,
                        }
                        collection.update_one({"_id": ObjectId(pilihan)}, {"$set": update_fields})
                        st.success("Berhasil diperbarui.")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Gagal update: {e}")
    
            # ----- HAPUS TRANSAKSI -----
            with st.expander("Hapus transaksi"):
                hapus_pilihan = st.selectbox(
                    "Pilih transaksi untuk dihapus",
                    options=df["id"].tolist(),
                    format_func=lambda x: (
                        f"{x[:6]}... | {df.loc[df['id'] == x, 'nama'].values[0]} | "
                        f"{'+' if df.loc[df['id'] == x, 'tipe'].values[0]=='masuk' else '-'}Rp {df.loc[df['id'] == x, 'jumlah'].values[0]:,.2f} | "
                        f"{df.loc[df['id'] == x, 'keperluan'].values[0]}"
                    )
                )
                if st.button("Hapus sekarang"):
                    try:
                        result = collection.delete_one({"_id": ObjectId(hapus_pilihan)})
                        if result.deleted_count:
                            st.success("Transaksi berhasil dihapus.")
                            st.experimental_rerun()
                        else:
                            st.error("ID tidak ditemukan.")
                    except Exception as e:
                        st.error(f"Gagal menghapus: {e}")




else:
    st.subheader(f"Input Pemasukan: {user_name}")
    with st.form("form_user"):
        jumlah_in = st.number_input("Jumlah (Rp)", min_value=0.0, format="%.2f")
        catatan_in = st.text_input("Catatan")
        bukti_file = st.file_uploader("Upload Bukti", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("Kirim")

    if submitted:
        if jumlah_in <= 0 or not bukti_file:
            st.warning("Lengkapi jumlah dan bukti.")
        else:
            tambah_transaksi(user_name, jumlah_in, "Pembayaran", tipe="masuk", catatan=catatan_in, bukti_file=bukti_file)
            st.success("Data berhasil dikirim.")

    st.markdown("---")
    render_rekap(df, user_name, is_admin=False)
