# 🎸 Bandcamp Sales — Data Warehouse & Dashboard

Proyek **Data Warehouse** berbasis *Star Schema* (model Kimball) untuk menganalisis
penjualan musik independen di platform **Bandcamp**, lengkap dengan **pipeline ETL**,
**7 query OLAP**, dan **dashboard visualisasi interaktif** (Streamlit + Plotly).

Dataset: ~1 juta transaksi penjualan Bandcamp (September–Oktober 2020).

---

## ✨ Fitur Utama

- **Pipeline ETL end-to-end** di satu notebook: *Extract → Validate → Transform → Load*.
- **Star Schema** dengan *integer surrogate key*, *foreign key*, *index*, dan baris **"Unknown" (-1)** untuk menjaga *referential integrity*.
- **Date dimension** penuh (rentang tanggal kontigu) + atribut kalender (hari, kuartal, akhir pekan, Bandcamp Friday).
- **7 query OLAP** untuk menjawab pertanyaan bisnis (revenue bulanan, Bandcamp Friday, top artis, dll).
- **Dashboard interaktif** dengan filter (negara, tipe produk, tanggal), KPI, peta dunia, dan grafik dinamis.
- **Tab "Bayar Sesukanya"** — analisis *pay-what-you-want*: tingkat kelebihan bayar per tipe produk, item gratis vs berbayar, dan **kurva konsentrasi pendapatan artis** (long-tail).

---

## 🗂️ Struktur Proyek

```
bandcamp-dwh/
├── main_pipeline.ipynb     # Pipeline ETL + OLAP (jalankan ini dulu)
├── app.py                  # Dashboard Streamlit
├── .streamlit/
│   └── config.toml         # Tema warna dashboard
├── requirements.txt        # Daftar dependency
├── dataset/                # Data mentah CSV (file 1 juta baris di-ignore git)
├── database/               # Output: bandcamp_dw.db (SQLite) — dibuat ulang oleh notebook
├── etl/                    # Output: ekspor tabel DWH ke CSV — dibuat ulang oleh notebook
└── olap/                   # Output: hasil 7 query analisis bisnis
```

> ⚠️ Folder `database/` dan `etl/` berisi **artefak hasil generate** (file besar) dan
> sengaja **tidak ikut di-commit** ke git. Keduanya dibuat ulang otomatis saat notebook dijalankan.

---

## 🏗️ Arsitektur (Star Schema)

Satu tabel fakta di tengah, dikelilingi 5 dimensi:

```
                 ┌──────────────┐
                 │  Dim_Waktu   │
                 └──────┬───────┘
 ┌────────────┐         │          ┌──────────────┐
 │ Dim_Lokasi │────┐    │    ┌─────│   Dim_Item   │
 └────────────┘    │    │    │     └──────────────┘
                 ┌─┴────┴────┴─┐
                 │ Fact_Sales  │   grain = 1 baris / transaksi
                 └─┬─────────┬─┘
 ┌────────────┐    │         │     ┌────────────────┐
 │ Dim_Artis  │────┘         └─────│ Dim_Penggemar  │
 └────────────┘                    └────────────────┘
```

**Measures** di `Fact_Sales`: `Gross_Rev`, `Bandcamp_Cut`, `Artist_Revenue` (semua USD).

---

## 🚀 Cara Menjalankan

### 1. Prasyarat
- Python 3.10+ (diuji pada 3.14)
- Install dependency:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Bangun Data Warehouse
Buka `main_pipeline.ipynb` (VS Code / Jupyter) lalu **Run All**.
Notebook ini akan menghasilkan:
- `database/bandcamp_dw.db` — warehouse SQLite
- `etl/export_*.csv` — ekspor 5 dimensi + tabel fakta
- `olap/hasil_query*.csv` — 7 hasil analisis bisnis

> Default memakai dataset penuh (~1 juta baris, ±75 detik). Untuk uji cepat, ubah
> `RAW_DATA_PATH` di sel pertama ke `dataset/sample_bandcamp_sales.csv`.

### 3. Jalankan Dashboard
```bash
streamlit run app.py
```
Buka di browser: **http://localhost:8501**
(Pastikan `database/bandcamp_dw.db` sudah ada dari langkah 2.)

---

## 📊 Insight Bisnis Utama

| # | Insight | Angka |
|---|---|---|
| 1 | Produk **fisik/merch** adalah mesin pendapatan | 51% revenue dari hanya 23% transaksi |
| 2 | **Bandcamp Friday** (2 Okt) menggratiskan biaya → 100% ke artis | $1,36 jt dalam 1 hari = **4,1× hari biasa** |
| 3 | Pasar sangat terkonsentrasi | AS 44% + UK 14% + Jerman 8% = **~66% revenue** |
| 4 | Pola **bayar sesukanya** (*pay-what-you-want*) | 25% order < $2, tapi order besar menyetir ~72% revenue |
| 5 | Ekonomi **long-tail** artis | Top 1% artis = **43%** total revenue (Top 5% = 67%) |
| 6 | **Generositas fan** — bayar di atas harga minimum | 36% order bayar lebih → **$1,28 jt** ekstra (**14%** dari gross) |
| 7 | Item **gratis (name-your-price)** tetap dibayar | 11,5% transaksi ber-harga $0, fan tetap bayar **~$400 rb** sukarela |

---

## 🔌 7 Query OLAP

1. Revenue bulanan + *Average Transaction Value*
2. Revenue per genre & artis *(genre sintetis)*
3. Dampak **Bandcamp Friday** vs hari biasa
4. Negara dengan pembelian produk fisik tertinggi
5. Top 10 artis berdasarkan pendapatan bersih merch
6. Volume penjualan: tipe produk × negara × kuartal
7. Subscriber vs Standard *(data sintetis)*

---

## ⚠️ Catatan Integritas Data

Kolom berikut adalah **data sintetis** (tidak tersedia di sumber Bandcamp) dan ditandai eksplisit:
- `Dim_Artis.Primary_Genre`
- `Dim_Penggemar` (User & `Fan_Status`)

Query 2 & 7 yang memakainya bersifat **demonstrasi metodologi**, bukan insight bisnis nyata.

---

## 🛠️ Tech Stack

`Python` · `pandas` · `SQLite` · `Streamlit` · `Plotly` · `Jupyter Notebook`
