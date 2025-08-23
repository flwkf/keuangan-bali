Nice 😃, kalau gitu saya rapikan jadi README versi **GitHub style** lengkap dengan badge teknologi biar lebih profesional:

---

# 💰 Shared Finance - Bali Trip

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-red?logo=streamlit)](https://streamlit.io/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Database-green?logo=mongodb)](https://www.mongodb.com/)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-purple?logo=pandas)](https://pandas.pydata.org/)

This is a **Streamlit + MongoDB (GridFS)** application to record and manage our **shared travel funds** for the Bali trip.
I was trusted as the treasurer, so this app helps track **income, expenses, and transfer receipts** transparently for all members.

---

## 🚀 Features

✅ Add Income (with receipt upload)

✅ Add Shared Expenses (auto split among members)

✅ Per-Person Financial Summary (income, expenses, balance)

✅ Receipt Viewer (all transfers can be checked)

✅ Admin Tools (edit & delete transactions)

---

## 🛠️ Tech Stack

* **Python 3.11**
* **Streamlit** for the frontend
* **MongoDB + GridFS** for data & receipt storage
* **Pandas** for aggregation & reporting

---

## 📂 Data Structure

Each transaction is stored in MongoDB like this:

```json
{
  "nama": "Rizal",
  "jumlah": 200000.0,
  "keperluan": "Payment",
  "tipe": "income",
  "catatan": "BCA transfer",
  "waktu": "2025-08-23T12:00:00Z",
  "bukti_id": "ObjectId(...)"
}
```

---

## 🔑 Authentication

* **Admin** → only Rizal (with password)
* **User** → members log in by selecting their name

---

## ⚙️ How to Run

1. Clone the repo:

   ```bash
   git clone https://github.com/your-username/shared-finance-bali.git
   cd shared-finance-bali
   ```
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.streamlit/secrets.toml` file:

   ```toml
   MONGO_URI = "mongodb+srv://..."
   ADMIN_PASSWORD = "your_admin_password"
   ```
4. Run the app:

   ```bash
   streamlit run app.py
   ```

---

## 👥 Members

* Rizal (Admin)
* Fikrie
* Rendika
* Thesi
* Nanda
* Ryanta

---

## 🎯 Purpose

To ensure **transparent financial management** during our trip, so every member can easily monitor contributions, expenses, and balances without manual notes.

---

## 📸 Mockup Screenshot

Sample interface of the app:

![App Screenshot](<img width="1024" height="1536" alt="ChatGPT Image 23 Agu 2025, 09 03 07" src="https://github.com/user-attachments/assets/7e181ab8-bbb4-47a1-b6fb-9b887aa8df2a" />
)

---

Mau saya bikinkan juga **requirements.txt** (isi dependency yang dipakai) biar repo-mu langsung bisa di-install siap jalan?
