# 💰 Shared Finance - Bali Trip

This is a **Streamlit + MongoDB (GridFS)** application to record and manage our **shared travel funds** for the Bali trip.
I was trusted as the treasurer, so this app helps track **income, expenses, and transfer receipts** transparently for all members.

---

## 🚀 Main Features

1. **Add Income**

   * Each member can upload their payment receipt and record contributions.
   * Data is stored securely in MongoDB.

2. **Add Shared Expenses** (Admin only)

   * Admin (me) can record group expenses.
   * Expenses are automatically split equally among all members.

3. **Per-Person Summary**

   * Displays each member’s total income, expenses, and balance.
   * Can be filtered by member name or transaction type (income/expense).

4. **Transfer Receipts**

   * All uploaded receipts are viewable directly in the app.

5. **Edit & Delete Transactions** (Admin only)

   * Admin can fix incorrect entries or remove transactions if necessary.

---

## 🛠️ Tech Stack

* **Python 3.11**
* **Streamlit** for the UI
* **MongoDB + GridFS** for data & receipt storage
* **Pandas** for data processing

---

## 📂 Data Structure

Each transaction is stored with this format:

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

* **Admin**: only Rizal (with password)
* **User**: other members log in by selecting their name

---

## ⚙️ How to Run

1. Clone this repo / copy the script.
2. Create a `.streamlit/secrets.toml` file:

   ```toml
   MONGO_URI = "mongodb+srv://..."
   ADMIN_PASSWORD = "your_admin_password"
   ```
3. Run the app:

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

This app was built to ensure **transparent financial management** during our trip, so every member can easily track contributions, expenses, and balances without manual notes.


