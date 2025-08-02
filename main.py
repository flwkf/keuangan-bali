import os
import uuid
import streamlit as st
import pandas as pd
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime

# ---------- konfigurasi ----------
NAMA_PEMBAYAR = ["Rizal", "Fikrie", "Rendika", "Thesi", "Nanda", "Ryanta"]
UPLOAD_DIR = "uploads"  # tempat simpan bukti

# buat folder kalau belum ada
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    return db["bali"]

collection = get_collection()

# ---------- helper ----------
def tambah_transaksi(nama, jumlah, keperluan, tipe="masuk", catatan="", bukti_path=None):
    doc = {
        "nama": nama,
        "jumlah": float(jumlah),
        "keperluan": keperluan,
        "tipe": tipe,
        "catatan": catatan,
        "waktu": datetime.utcnow(),
        "bukti": bukti_path,
    }
    collection.insert_one(doc)

def ambil_semua_transaksi():
    cursor = collection.find().sort("waktu", -1)
    df = pd.DataFrame(list(cursor))
    if df.empty:
        return df
    if "waktu" in df.columns:
        df["waktu"] = pd.to_datetime(df["waktu"], errors="coerce")
    else:
        df["waktu"] = pd.NaT
    if "jumlah" in df.columns:
        df["jumlah"] = pd.to_numeric(df["jumlah"], errors="coerce").fillna(0.0)
    else:
        df["jumlah"] = 0.0
    df["tipe"] = df.get("tipe", "masuk").fillna("masuk")
    df["nama"] = df.get("nama", "Unknown").fillna("Unknown")
    df = df.rename(columns={"_id": "id"})
    df["id"] = df["id"].astype(str)
    return df

def rekap_per_orang(df: pd.DataFrame):
    if df.empty:
        return pd.DataFrame()
    masuk = (
        df[df["tipe"] == "masuk"]
        .groupby("nama")
        .agg(total_masuk=pd.NamedAgg(column="jumlah", aggfunc="sum"))
    )
    keluar = (
        df[df["tipe"] == "keluar"]
        .groupby("nama")
        .agg(total_keluar=pd.NamedAgg(column="jumlah", aggfunc="sum"))
    )
    summary = pd.concat([masuk, keluar], axis=1).fillna(0).reset_index()
    summary["netto"] = summary["total_masuk"] - summary["total_keluar"]
    summary["jumlah_transaksi"] = df.groupby("nama").size().reindex(summary["nama"]).fillna(0).astype(int).values
    for col in ["total_masuk", "total_keluar", "netto"]:
        summary[col] = summary[col].astype(float)
    return summary

def render_rekap(df, user_name, is_admin):
    st.subheader("Rekap & Ringkasan")

    if df.empty:
        st.info("Belum ada transaksi.")
        return

    # pilihan nama: admin bisa pilih "Semua" atau per orang; user biasa hanya namanya
    if is_admin:
        pilihan_nama = ["Semua"] + NAMA_PEMBAYAR
        filter_nama = st.selectbox("Tampilkan untuk:", pilihan_nama, key="rekap_filter_nama")
    else:
        filter_nama = user_name

    # filter tipe transaksi
    pilihan_tipe = st.selectbox("Tipe transaksi:", ["Semua", "masuk", "keluar"], key=f"rekap_filter_tipe_{'admin' if is_admin else 'user'}")

    df_filtered = df.copy()
    if filter_nama != "Semua":
        df_filtered = df_filtered[df_filtered["nama"] == filter_nama]
    if pilihan_tipe != "Semua":
        df_filtered = df_filtered[df_filtered["tipe"] == pilihan_tipe]

    summary = rekap_per_orang(df_filtered)

    # tampil kolom sesuai tipe
    if pilihan_tipe == "masuk":
        display_cols = ["nama", "total_masuk", "jumlah_transaksi"]
    elif pilihan_tipe == "keluar":
        display_cols = ["nama", "total_keluar", "jumlah_transaksi"]
    else:
        display_cols = ["nama", "total_masuk", "total_keluar", "netto", "jumlah_transaksi"]

    st.markdown("**Rekap per orang:**")
    st.dataframe(
        summary[display_cols]
        .sort_values("netto", ascending=False)
        .reset_index(drop=True),
        use_container_width=True
    )

    # totals berdasarkan filter
    total_masuk_all = df_filtered[df_filtered["tipe"] == "masuk"]["jumlah"].sum()
    total_keluar_all = df_filtered[df_filtered["tipe"] == "keluar"]["jumlah"].sum()
    netto_all = total_masuk_all - total_keluar_all

    if pilihan_tipe == "masuk":
        st.markdown(
            f"**Total pemasukan:** Rp {total_masuk_all:,.2f} "
        )
    elif pilihan_tipe == "keluar":
        st.markdown(
            f"**Total pengeluaran:** Rp {total_keluar_all:,.2f}"
        )
    else:
        st.markdown(
            f"**Total pemasukan:** Rp {total_masuk_all:,.2f}  \n"
            f"**Total pengeluaran:** Rp {total_keluar_all:,.2f}  \n"
            f"**Netto:** Rp {netto_all:,.2f}"
        )

    st.markdown("---")
    st.markdown("**Detail transaksi terbaru:**")
    st.dataframe(
        df_filtered.sort_values("waktu", ascending=False).reset_index(drop=True),
        use_container_width=True
    )

    st.markdown("---")
    st.subheader("Bukti Transfer (sesuai filter)")
    df_with_bukti = df_filtered[df_filtered["bukti"].notnull()]
    if df_with_bukti.empty:
        st.info("Tidak ada bukti untuk filter ini.")
    else:
        for _, row in df_with_bukti.iterrows():
            with st.expander(f"{row['nama']} | {'+' if row['tipe']=='masuk' else '-'}Rp {row['jumlah']:,.2f} | {row['keperluan']}"):
                st.write(f"Waktu: {row['waktu']}")
                st.write(f"Catatan: {row.get('catatan','')}")
                if row.get("bukti"):
                    try:
                        st.image(row["bukti"], caption=f"ID: {row['id']}", width=300)
                    except Exception:
                        st.write("Gagal menampilkan gambar (mungkin file hilang).")

# ---------- autentikasi nama ----------
st.sidebar.header("Masuk / Pilih Nama")
user_name = st.sidebar.selectbox("Pilih nama kamu", NAMA_PEMBAYAR)

is_admin = False
if user_name == "Rizal":
    pwd = st.sidebar.text_input("Password admin", type="password")
    if pwd and pwd == st.secrets["ADMIN_PASSWORD"]:
        is_admin = True
        st.sidebar.success("Login sebagai admin (Rizal)")
    else:
        if pwd:
            st.sidebar.error("Password salah")
else:
    st.sidebar.info(f"Masuk sebagai {user_name} (bisa input pemasukan saja)")

# ambil data setiap refresh
df = ambil_semua_transaksi()

# ---------- tampilan ----------
if is_admin:
    tab1, tab2, tab3, tab4 = st.tabs(["Pemasukan", "Pengeluaran", "Rekap", "Edit"])
    with tab1:
        st.subheader("Tambah Pemasukan / Pembayaran Individu (Admin)")
        with st.form("form_input_masuk_admin"):
            col1, col2, col3 = st.columns(3)
            with col1:
                nama_in = st.selectbox("Pilih Nama", NAMA_PEMBAYAR, key="admin_masuk_nama")
            with col2:
                jumlah_in = st.number_input("Jumlah Bayar (Rp)", min_value=0.0, format="%.2f", key="admin_masuk_jumlah")
            with col3:
                # tidak ada pilihan keperluan, pakai tetap
                keperluan_in = "Pembayaran"
            catatan_in = st.text_input("Catatan (opsional)", key="admin_masuk_catatan")
            bukti_file = st.file_uploader("Upload bukti transfer", type=["jpg", "jpeg", "png"], key="admin_bukti")
            submitted_in = st.form_submit_button("Simpan Pemasukan")

        if submitted_in:
            if jumlah_in <= 0:
                st.warning("Jumlah harus lebih dari 0.")
            elif not bukti_file:
                st.warning("Upload bukti transfer wajib untuk pemasukan.")
            else:
                bukti_path = None
                ext = os.path.splitext(bukti_file.name)[1]
                nama_file = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}{ext}"
                path = os.path.join(UPLOAD_DIR, nama_file)
                with open(path, "wb") as f:
                    f.write(bukti_file.getbuffer())
                bukti_path = path
                tambah_transaksi(nama_in, jumlah_in, keperluan_in, tipe="masuk", catatan=catatan_in, bukti_path=bukti_path)
                st.success(f"Pemasukan untuk {nama_in} tersimpan.")


    with tab2:
        st.subheader("Tambah Pengeluaran Bersama (dibagi rata) dengan Bukti")
        with st.form("form_pengeluaran_admin"):
            total_pengeluaran = st.number_input("Total Pengeluaran Keseluruhan (Rp)", min_value=0.0, format="%.2f")
            keperluan_peng = st.text_input("Keperluan Pengeluaran", value="Pengeluaran bersama")
            catatan_peng = st.text_input("Catatan (opsional)", value="", help="Contoh: beli bahan, bensin, dsb.")
            bukti_pengeluaran = st.file_uploader("Upload bukti pengeluaran (gambar)", type=["jpg", "jpeg", "png"], help="Bukti umum untuk keseluruhan pengeluaran", key="bukti_pengeluaran")
            submitted_peng = st.form_submit_button("Bagi dan Simpan Pengeluaran")

        if submitted_peng:
            if total_pengeluaran <= 0:
                st.warning("Total pengeluaran harus lebih dari 0.")
            else:
                share = total_pengeluaran / len(NAMA_PEMBAYAR)
                bukti_path = None
                if bukti_pengeluaran:
                    ext = os.path.splitext(bukti_pengeluaran.name)[1]
                    nama_file = f"pengeluaran_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}{ext}"
                    path = os.path.join(UPLOAD_DIR, nama_file)
                    with open(path, "wb") as f:
                        f.write(bukti_pengeluaran.getbuffer())
                    bukti_path = path

                try:
                    for nama_p in NAMA_PEMBAYAR:
                        tambah_transaksi(
                            nama_p,
                            share,
                            f"{keperluan_peng} (share)",
                            tipe="keluar",
                            catatan=catatan_peng,
                            bukti_path=bukti_path
                        )
                    st.success(f"Pengeluaran Rp {total_pengeluaran:,.2f} dibagi rata ke {len(NAMA_PEMBAYAR)} orang, masing-masing Rp {share:,.2f}.")
                except Exception as e:
                    st.error(f"Gagal menyimpan pengeluaran bersama: {e}")

    with tab3:
        render_rekap(df, user_name, is_admin=True)

    with tab4:
        st.subheader("Edit / Hapus Transaksi")
        if df.empty:
            st.info("Belum ada transaksi.")
        else:
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
                row = df[df["id"] == pilihan].iloc[0]
                with st.form("form_edit_admin"):
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_nama = st.selectbox("Nama", NAMA_PEMBAYAR, index=NAMA_PEMBAYAR.index(row["nama"]) if row["nama"] in NAMA_PEMBAYAR else 0)
                        edit_tipe = st.selectbox("Tipe", ["masuk", "keluar"], index=0 if row.get("tipe", "masuk") == "masuk" else 1)
                    with col2:
                        edit_jumlah = st.number_input("Jumlah (Rp)", value=float(row.get("jumlah", 0.0)), format="%.2f")
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
                        st.success("Terupdate.")
                    except Exception as e:
                        st.error(f"Gagal update: {e}")

            with st.expander("Hapus transaksi"):
                to_delete = st.text_input("Masukkan ID transaksi untuk dihapus")
                if st.button("Hapus sekarang"):
                    if not to_delete:
                        st.warning("Masukkan ID.")
                    else:
                        try:
                            result = collection.delete_one({"_id": ObjectId(to_delete.strip())})
                            if result.deleted_count:
                                st.success("Terhapus.")
                            else:
                                st.error("ID tidak ditemukan.")
                        except Exception as e:
                            st.error(f"Gagal: {e}")
else:
    # user biasa: input pemasukan + rekap (hanya untuk dirinya)
    st.subheader(f"Input Pemasukan: {user_name}")
    with st.form("form_input_nonadmin"):
        jumlah_in = st.number_input("Jumlah Bayar (Rp)", min_value=0.0, format="%.2f", key="user_jumlah")
        catatan_in = st.text_input("Catatan (opsional)", key="user_catatan")
        bukti_file = st.file_uploader("Upload bukti transfer (gambar)", type=["jpg", "jpeg", "png"], key="user_bukti")
        submitted_user = st.form_submit_button("Kirim Pemasukan")

    if submitted_user:
        if jumlah_in <= 0:
            st.warning("Jumlah harus lebih dari 0.")
        elif not bukti_file:
            st.warning("Upload bukti transfer wajib untuk pemasukan.")
        else:
            bukti_path = None
            ext = os.path.splitext(bukti_file.name)[1]
            nama_file = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}{ext}"
            path = os.path.join(UPLOAD_DIR, nama_file)
            with open(path, "wb") as f:
                f.write(bukti_file.getbuffer())
            bukti_path = path
            tambah_transaksi(user_name, jumlah_in, "Pembayaran", tipe="masuk", catatan=catatan_in, bukti_path=bukti_path)
            st.success("Pemasukan dikirim. Tunggu konfirmasi dari admin jika perlu.")


    st.markdown("---")
    render_rekap(df, user_name, is_admin=False)
