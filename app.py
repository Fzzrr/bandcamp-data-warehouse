"""
🎸 Bandcamp Sales — Data Warehouse Dashboard
=============================================
Dashboard visualisasi interaktif yang membaca langsung dari Data Warehouse
SQLite (Star Schema) hasil main_pipeline.ipynb.

Menjalankan:
    streamlit run app.py
"""

import os
import sqlite3

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "bandcamp_dw.db")

# ----------------------------------------------------------------------------
# Konfigurasi halaman + tema warna
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Bandcamp DWH Dashboard", page_icon="🎸", layout="wide")

TEAL = "#11999E"
DARK = "#16323A"
CORAL = "#E4572E"
SEQ = ["#11999E", "#40514E", "#E4572E", "#F4A259", "#5B8E7D", "#8A4F7D", "#2E86AB"]

# Pemetaan nama kolom mentah -> label tampilan yang rapi (tanpa underscore)
LABELS = {
    "Revenue": "Revenue (USD)",
    "Transaksi": "Jumlah Transaksi",
    "Negara": "Negara",
    "Nama_Artis": "Nama Artis",
    "Pendapatan": "Pendapatan Bersih (USD)",
    "Nama_Item": "Produk",
    "Tipe_Item": "Tipe Produk",
    "Pct_ke_Artis": "Persen ke Artis",
    "Rev_per_Hari": "Revenue per Hari (USD)",
    "Kategori": "Kategori Hari",
    "Tipe_Hari": "Tipe Hari",
    "Fan_Status": "Status Fan",
    "Avg_per_Fan": "Rata-rata per Fan (USD)",
    "Belanja": "Total Belanja (USD)",
    "Bucket": "Rentang Nilai Order",
    "Hari Bandcamp": "Hari",
    "Warna": "Kategori Hari",
    "Tanggal": "Tanggal",
    "Terjual": "Unit Terjual",
}

CSS = """
<style>
    .block-container {padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1300px;}
    /* Hero header */
    .hero {
        background: linear-gradient(110deg, #11999E 0%, #16323A 100%);
        padding: 1.4rem 1.8rem; border-radius: 16px; color: #fff; margin-bottom: 1.2rem;
        box-shadow: 0 6px 20px rgba(17,153,158,.25);
    }
    .hero h1 {margin: 0; font-size: 1.7rem; font-weight: 800; letter-spacing:-.5px;}
    .hero p  {margin: .25rem 0 0; opacity: .85; font-size: .9rem;}
    /* KPI cards */
    .kpi-grid {display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: .4rem;}
    .kpi {
        background: #fff; border: 1px solid #E3ECEE; border-radius: 14px; padding: 16px 18px;
        box-shadow: 0 2px 10px rgba(22,50,58,.04);
    }
    .kpi .lbl {font-size: .74rem; text-transform: uppercase; letter-spacing: .6px; color: #6B8A92; font-weight: 700;}
    .kpi .val {font-size: 1.6rem; font-weight: 800; color: #16323A; line-height: 1.25; margin-top: 2px;}
    .kpi .sub {font-size: .76rem; color: #8AA1A8; margin-top: 1px;}
    .kpi.accent {background: linear-gradient(135deg,#11999E,#0E7C80); border: none;}
    .kpi.accent .lbl {color: #CFEFF0;} .kpi.accent .val, .kpi.accent .sub {color: #fff;}
    /* Insight callouts */
    .insight {
        background: #F3FAFA; border-left: 4px solid #11999E; border-radius: 8px;
        padding: 12px 16px; margin-bottom: 10px; font-size: .9rem; color: #234;
    }
    .insight b {color: #0E7C80;}
    @media (max-width: 1100px) {.kpi-grid {grid-template-columns: repeat(2,1fr);}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Koneksi & helper query (di-cache)
# ----------------------------------------------------------------------------
@st.cache_resource
def get_conn():
    if not os.path.exists(DB_PATH):
        st.error(
            f"Database tidak ditemukan di `{DB_PATH}`.\n\n"
            "Jalankan **main_pipeline.ipynb** dulu untuk membangun warehouse."
        )
        st.stop()
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data(show_spinner=False)
def run(sql: str, params: tuple = ()):
    return pd.read_sql_query(sql, get_conn(), params=params)


BASE = (
    "FROM Fact_Sales f "
    "JOIN Dim_Waktu  w ON f.Time_ID   = w.Time_ID "
    "JOIN Dim_Lokasi l ON f.Lokasi_SK = l.Lokasi_SK "
    "JOIN Dim_Item   i ON f.Item_SK   = i.Item_SK "
)


def build_where(countries, types, date_lo, date_hi):
    clauses, params = ["w.Time_ID <> -1"], []
    if countries:
        clauses.append(f"l.Negara IN ({','.join('?' * len(countries))})")
        params += list(countries)
    if types:
        clauses.append(f"i.Tipe_Item IN ({','.join('?' * len(types))})")
        params += list(types)
    clauses.append("w.Tanggal BETWEEN ? AND ?")
    params += [date_lo, date_hi]
    return " WHERE " + " AND ".join(clauses), tuple(params)


def fmt_usd(x):
    if x >= 1e6:
        return f"${x/1e6:.2f}M"
    if x >= 1e3:
        return f"${x/1e3:.0f}K"
    return f"${x:,.0f}"


def style_fig(fig, h=380):
    fig.update_layout(
        template="plotly_white", height=h, margin=dict(t=30, b=10, l=10, r=10),
        font=dict(family="sans-serif", color=DARK, size=12),
        legend=dict(title_text="", orientation="h", y=1.12, x=0),
        title_text="",  # judul ditampilkan via st.markdown; kosongkan agar tidak muncul "undefined"
    )
    return fig


# ----------------------------------------------------------------------------
# Sidebar — Filter
# ----------------------------------------------------------------------------
st.sidebar.markdown("### Filter Data")

all_countries = run("SELECT Negara FROM Dim_Lokasi WHERE Lokasi_SK<>-1 ORDER BY Negara")["Negara"].tolist()
all_types = run("SELECT DISTINCT Tipe_Item FROM Dim_Item WHERE Item_SK<>-1 ORDER BY Tipe_Item")["Tipe_Item"].tolist()
all_dates = run(
    "SELECT Tanggal FROM Dim_Waktu WHERE Time_ID<>-1 ORDER BY Tanggal"
)["Tanggal"].tolist()

sel_countries = st.sidebar.multiselect(
    "Negara",
    all_countries,
    default=[],
    help="Kosong = semua negara"
)

sel_types = st.sidebar.multiselect(
    "Tipe Produk",
    all_types,
    default=[],
    help="Kosong = semua tipe"
)

if len(all_dates) > 1:
    lo, hi = all_dates[0], all_dates[-1]

    date_lo, date_hi = st.sidebar.select_slider(
        "Rentang Tanggal",
        options=all_dates,
        value=(lo, hi)
    )

elif len(all_dates) == 1:
    lo = hi = all_dates[0]
    date_lo = date_hi = all_dates[0]

    st.sidebar.info(
        f"Rentang tanggal hanya tersedia pada {all_dates[0]}"
    )

else:
    st.error("Tidak ada data tanggal pada Dim_Waktu")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.caption(
    "⚠️ **Genre**, **Fan Status**, dan **User** adalah data *sintetis* "
    "(tidak ada di sumber Bandcamp), ditandai eksplisit. Sisanya data nyata."
)

WHERE, P = build_where(sel_countries, sel_types, date_lo, date_hi)


# ----------------------------------------------------------------------------
# Hero + KPI
# ----------------------------------------------------------------------------
st.markdown(
    f"""<div class="hero">
        <h1>Bandcamp Sales — Data Warehouse Dashboard</h1>
        <p>Star Schema · 1 tabel fakta + 5 dimensi · rentang data {lo} → {hi}</p>
    </div>""",
    unsafe_allow_html=True,
)

kpi = run(
    f"SELECT COUNT(*) tx, COALESCE(SUM(f.Gross_Rev),0) gross, "
    f"COALESCE(SUM(f.Artist_Revenue),0) artis, COALESCE(SUM(f.Bandcamp_Cut),0) cut, "
    f"COALESCE(AVG(f.Gross_Rev),0) avg {BASE}{WHERE}",
    P,
).iloc[0]

if not kpi["tx"]:
    st.warning("Tidak ada data untuk filter ini. Longgarkan filter di sidebar.")
    st.stop()

pct_artis = 100 * kpi["artis"] / kpi["gross"] if kpi["gross"] else 0
st.markdown(
    f"""<div class="kpi-grid">
      <div class="kpi"><div class="lbl">Transaksi</div><div class="val">{int(kpi['tx']):,}</div><div class="sub">Baris Fakta</div></div>
      <div class="kpi accent"><div class="lbl">Gross Revenue</div><div class="val">{fmt_usd(kpi['gross'])}</div><div class="sub">Total Penjualan</div></div>
      <div class="kpi"><div class="lbl">Ke Artis</div><div class="val">{fmt_usd(kpi['artis'])}</div><div class="sub">{pct_artis:.1f}% dari gross</div></div>
      <div class="kpi"><div class="lbl">Potongan Bandcamp</div><div class="val">{fmt_usd(kpi['cut'])}</div><div class="sub">{100-pct_artis:.1f}% dari gross</div></div>
      <div class="kpi"><div class="lbl">Avg / Order</div><div class="val">${kpi['avg']:.2f}</div><div class="sub">Nilai Rata-Rata</div></div>
    </div>""",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Pre-compute beberapa angka untuk insight callout (dinamis)
# ----------------------------------------------------------------------------
mix = run(
    f"SELECT i.Tipe_Item, SUM(f.Gross_Rev) Revenue, COUNT(*) Tx {BASE}{WHERE} "
    f"AND i.Item_SK <> -1 GROUP BY i.Tipe_Item ORDER BY Revenue DESC", P,
)
mix["pct_rev"] = 100 * mix["Revenue"] / mix["Revenue"].sum()
mix["pct_tx"] = 100 * mix["Tx"] / mix["Tx"].sum()
phys = mix[mix["Tipe_Item"] == "Physical / Merch"]

phys_pct_rev = (
    phys["pct_rev"].iloc[0]
    if not phys.empty
    else 0
)

phys_pct_tx = (
    phys["pct_tx"].iloc[0]
    if not phys.empty
    else 0
)

fri = run(
    f"SELECT CASE WHEN w.Hari='Friday' THEN 'Jumat' ELSE 'Lain' END g, "
    f"SUM(f.Gross_Rev)/COUNT(DISTINCT w.Tanggal) rph {BASE}{WHERE} GROUP BY g", P,
).set_index("g")["rph"]
fri_mult = (fri.get("Jumat", 0) / fri.get("Lain", 1)) if fri.get("Lain", 0) else 0

geo_df = run(
    f"SELECT l.Negara, SUM(f.Gross_Rev) r {BASE}{WHERE} "
    f"GROUP BY l.Negara ORDER BY r DESC LIMIT 1",
    P,
)

if geo_df.empty:
    geo_top = {"Negara": "-", "r": 0}
    geo_share = 0
else:
    geo_top = geo_df.iloc[0]
    geo_share = (
        100 * geo_top["r"] / kpi["gross"]
        if kpi["gross"]
        else 0
    )

st.markdown("---")


tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Ringkasan", "Geografi & Produk", "Waktu & Perilaku", "Segmen Pelanggan", "Data"])

with tab1:
    st.markdown(
        f"""<div class="insight"><b>{phys['pct_rev'].iloc[0]:.0f}%</b> revenue datang dari
        <b>produk fisik / merch</b>, padahal hanya <b>{phys['pct_tx'].iloc[0]:.0f}%</b> dari jumlah transaksi —
        merch punya nilai order ~2,7× lebih tinggi dari album digital.</div>
        <div class="insight">Hari <b>Jumat</b> menghasilkan rata-rata <b>{fri_mult:.1f}×</b> revenue/hari
        dibanding hari lain — efek <b>Bandcamp Friday</b> (biaya platform 0%).</div>
        <div class="insight"><b>{geo_top['Negara']}</b> menyumbang <b>{geo_share:.0f}%</b> dari seluruh revenue —
        pasar sangat terkonsentrasi.</div>""",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("##### Tren Revenue Harian — *Friday Effect*")
        daily = run(
            f"SELECT w.Tanggal, w.Hari, SUM(f.Gross_Rev) Revenue, COUNT(*) Transaksi "
            f"{BASE}{WHERE} GROUP BY w.Tanggal ORDER BY w.Tanggal", P,
        )
        daily["Hari Bandcamp"] = daily["Hari"].apply(lambda h: "Jumat" if h == "Friday" else "Hari Lain")
        fig = px.bar(
            daily, x="Tanggal", y="Revenue", color="Hari Bandcamp",
            color_discrete_map={"Jumat": CORAL, "Hari Lain": TEAL},
            hover_data={"Transaksi": ":,"}, labels=LABELS,
        )
        fig.update_traces(hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<br>"
                          "Transaksi: %{customdata[0]:,}<extra>%{fullData.name}</extra>")
        st.plotly_chart(style_fig(fig), use_container_width=True)
    with col2:
        st.markdown("##### Komposisi Revenue per Tipe Produk")
        fig = px.pie(mix, names="Tipe_Item", values="Revenue", hole=0.58, color_discrete_sequence=SEQ)
        fig.update_traces(textposition="inside", textinfo="percent+label", sort=False,
                          hovertemplate="%{label}<br>Revenue: $%{value:,.0f}<extra></extra>")
        st.plotly_chart(style_fig(fig).update_layout(showlegend=False), use_container_width=True)

    st.markdown("##### Distribusi Nilai Order — perilaku bayar sesukanya")
    dist = run(
        f"""SELECT CASE
            WHEN f.Gross_Rev<2 THEN '< $2' WHEN f.Gross_Rev<5 THEN '$2–5'
            WHEN f.Gross_Rev<10 THEN '$5–10' WHEN f.Gross_Rev<25 THEN '$10–25'
            ELSE '$25+' END Bucket,
            COUNT(*) Transaksi, SUM(f.Gross_Rev) Revenue {BASE}{WHERE} GROUP BY Bucket""", P,
    )
    order_cat = ["< $2", "$2–5", "$5–10", "$10–25", "$25+"]
    dist["Bucket"] = pd.Categorical(dist["Bucket"], order_cat, ordered=True)
    dist = dist.sort_values("Bucket")
    fig = go.Figure()
    fig.add_bar(x=dist["Bucket"], y=dist["Transaksi"], name="Jumlah Transaksi", marker_color=TEAL, yaxis="y",
                hovertemplate="%{x}<br>Transaksi: %{y:,}<extra></extra>")
    fig.add_trace(go.Scatter(x=dist["Bucket"], y=dist["Revenue"], name="Total Revenue", mode="lines+markers",
                             marker_color=CORAL, yaxis="y2",
                             hovertemplate="%{x}<br>Revenue: $%{y:,.0f}<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Rentang Nilai Order"), yaxis=dict(title="Jumlah Transaksi"),
                      yaxis2=dict(title="Total Revenue (USD)", overlaying="y", side="right"))
    st.plotly_chart(style_fig(fig, 330), use_container_width=True)

with tab2:
    geo = run(
        f"SELECT l.Negara, SUM(f.Gross_Rev) Revenue, COUNT(*) Transaksi {BASE}{WHERE} "
        f"AND l.Lokasi_SK <> -1 GROUP BY l.Negara ORDER BY Revenue DESC", P,
    )
    st.markdown("##### Sebaran Revenue per Negara")
    fig = px.choropleth(
        geo, locations="Negara", locationmode="country names", color="Revenue",
        color_continuous_scale="Teal", hover_name="Negara",
        hover_data={"Negara": False, "Revenue": ":,.0f", "Transaksi": ":,"}, labels=LABELS,
    )
    fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Revenue: $%{z:,.0f}<br>"
                      "Transaksi: %{customdata[2]:,}<extra></extra>")
    fig.update_geos(showframe=False, showcoastlines=False, projection_type="natural earth")
    st.plotly_chart(style_fig(fig, 400).update_layout(margin=dict(t=10, b=0, l=0, r=0)), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 15 Negara dengan Revenue Tertinggi")
        g15 = geo.head(15)
        fig = px.bar(g15.sort_values("Revenue"), x="Revenue", y="Negara", orientation="h",
                     color="Revenue", color_continuous_scale="Teal", labels=LABELS)
        fig.update_traces(hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<extra></extra>")
        st.plotly_chart(style_fig(fig, 430).update_layout(coloraxis_showscale=False), use_container_width=True)
    with col2:
        st.markdown("##### 🎤 15 Artis dengan Pendapatan Bersih Tertinggi")
        artis = run(
            f"SELECT a.Nama_Artis, SUM(f.Artist_Revenue) Pendapatan {BASE} "
            f"JOIN Dim_Artis a ON f.Artis_SK=a.Artis_SK {WHERE} AND a.Artis_SK <> -1 "
            f"GROUP BY a.Nama_Artis ORDER BY Pendapatan DESC LIMIT 15", P,
        )
        fig = px.bar(artis.sort_values("Pendapatan"), x="Pendapatan", y="Nama_Artis", orientation="h",
                     color="Pendapatan", color_continuous_scale="Oranges", labels=LABELS)
        fig.update_traces(hovertemplate="<b>%{y}</b><br>Pendapatan bersih: $%{x:,.0f}<extra></extra>")
        st.plotly_chart(style_fig(fig, 430).update_layout(coloraxis_showscale=False), use_container_width=True)

    st.markdown("##### 10 Produk dengan Revenue Tertinggi")
    prod = run(
        f"SELECT i.Nama_Item, i.Tipe_Item, COUNT(*) Terjual, SUM(f.Gross_Rev) Revenue "
        f"{BASE}{WHERE} AND i.Item_SK<>-1 GROUP BY i.Item_SK ORDER BY Revenue DESC LIMIT 10", P,
    )
    prod["Nama_Item"] = prod["Nama_Item"].str.slice(0, 45)
    fig = px.bar(prod.sort_values("Revenue"), x="Revenue", y="Nama_Item", orientation="h",
                 color="Tipe_Item", color_discrete_sequence=SEQ, hover_data={"Terjual": ":,"}, labels=LABELS)
    fig.update_traces(hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<br>"
                      "Unit terjual: %{customdata[0]:,}<extra>%{fullData.name}</extra>")
    st.plotly_chart(style_fig(fig, 400), use_container_width=True)

with tab3:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Bandcamp Friday vs Hari Biasa (rata-rata/hari)")
        bcf = run(
            f"SELECT CASE w.Bandcamp_Friday WHEN 1 THEN 'Bandcamp Friday' ELSE 'Hari Biasa' END Kategori, "
            f"SUM(f.Gross_Rev)/COUNT(DISTINCT w.Tanggal) Rev_per_Hari {BASE}{WHERE} "
            f"GROUP BY w.Bandcamp_Friday", P,
        )
        fig = px.bar(bcf, x="Kategori", y="Rev_per_Hari", color="Kategori", text_auto=".2s",
                     color_discrete_sequence=[TEAL, CORAL], labels=LABELS)
        fig.update_traces(hovertemplate="<b>%{x}</b><br>Revenue per hari: $%{y:,.0f}<extra></extra>")
        st.plotly_chart(style_fig(fig, 350).update_layout(showlegend=False,
                        xaxis_title=None, yaxis_title="Revenue per Hari (USD)"), use_container_width=True)
    with col2:
        st.markdown("##### Hari Kerja vs Akhir Pekan (rata-rata per hari)")
        we = run(
            f"SELECT CASE w.Is_Weekend WHEN 1 THEN 'Akhir Pekan' ELSE 'Hari Kerja' END Tipe_Hari, "
            f"SUM(f.Gross_Rev)/COUNT(DISTINCT w.Tanggal) Rev_per_Hari {BASE}{WHERE} "
            f"GROUP BY w.Is_Weekend", P,
        )
        fig = px.bar(we, x="Tipe_Hari", y="Rev_per_Hari", color="Tipe_Hari", text_auto=".2s",
                     color_discrete_sequence=["#5B8E7D", "#F4A259"], labels=LABELS)
        fig.update_traces(hovertemplate="<b>%{x}</b><br>Revenue per hari: $%{y:,.0f}<extra></extra>")
        st.plotly_chart(style_fig(fig, 350).update_layout(showlegend=False,
                        xaxis_title=None, yaxis_title="Revenue per Hari (USD)"), use_container_width=True)

    st.markdown("##### Persentase Revenue yang Diterima Artis per Hari")
    tr = run(
        f"SELECT w.Tanggal, w.Hari, 100.0*SUM(f.Artist_Revenue)/SUM(f.Gross_Rev) Pct_ke_Artis "
        f"{BASE}{WHERE} GROUP BY w.Tanggal ORDER BY w.Tanggal", P,
    )
    tr["Warna"] = tr["Hari"].apply(lambda h: "Bandcamp Friday" if h == "Friday" else "Hari Biasa")
    fig = px.bar(tr, x="Tanggal", y="Pct_ke_Artis", color="Warna",
                 color_discrete_map={"Bandcamp Friday": CORAL, "Hari Biasa": TEAL}, labels=LABELS)
    fig.update_traces(hovertemplate="<b>%{x}</b><br>%{y:.1f}% revenue ke artis<extra>%{fullData.name}</extra>")
    fig.update_yaxes(range=[80, 101], title="Persen ke Artis (%)")
    st.plotly_chart(style_fig(fig, 330), use_container_width=True)
    st.caption("Saat Bandcamp Friday, biaya platform 0% sehingga 100% revenue mengalir ke artis "
               "(terlihat sebagai lonjakan).")

with tab4:
    st.info("Data **Fan Status** & **User** bersifat *sintetis* (di-generate, bukan dari sumber Bandcamp). "
            "Tab ini mendemonstrasikan metodologi dimensi pelanggan, bukan insight bisnis nyata.")
    fan = run(
        f"SELECT p.Fan_Status, i.Tipe_Item, SUM(f.Gross_Rev) Belanja, "
        f"COUNT(DISTINCT p.Penggemar_SK) Fans {BASE} "
        f"JOIN Dim_Penggemar p ON f.Penggemar_SK=p.Penggemar_SK {WHERE} "
        f"AND p.Penggemar_SK<>-1 GROUP BY p.Fan_Status, i.Tipe_Item", P,
    )
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Total Belanja per Status Fan dan Tipe Produk")
        fig = px.bar(fan, x="Fan_Status", y="Belanja", color="Tipe_Item", barmode="group",
                     color_discrete_sequence=SEQ, labels=LABELS)
        fig.update_traces(hovertemplate="<b>%{x}</b> · %{fullData.name}<br>"
                          "Total belanja: $%{y:,.0f}<extra></extra>")
        st.plotly_chart(style_fig(fig, 380).update_layout(xaxis_title=None), use_container_width=True)
    with col2:
        st.markdown("##### Rata-rata Belanja per Fan")
        avg = run(
            f"SELECT p.Fan_Status, SUM(f.Gross_Rev)/COUNT(DISTINCT p.Penggemar_SK) Avg_per_Fan {BASE} "
            f"JOIN Dim_Penggemar p ON f.Penggemar_SK=p.Penggemar_SK {WHERE} "
            f"AND p.Penggemar_SK<>-1 GROUP BY p.Fan_Status", P,
        )
        fig = px.bar(avg, x="Fan_Status", y="Avg_per_Fan", color="Fan_Status", text_auto=".2s",
                     color_discrete_sequence=[TEAL, CORAL], labels=LABELS)
        fig.update_traces(hovertemplate="<b>%{x}</b><br>Rata-rata per fan: $%{y:,.0f}<extra></extra>")
        st.plotly_chart(style_fig(fig, 380).update_layout(showlegend=False, xaxis_title=None), use_container_width=True)

with tab5:
    st.markdown("##### Revenue per Tipe Produk untuk 10 Negara Teratas")
    pivot = run(
        f"SELECT l.Negara, i.Tipe_Item, SUM(f.Gross_Rev) Revenue {BASE}{WHERE} "
        f"AND l.Lokasi_SK <> -1 AND i.Item_SK <> -1 GROUP BY l.Negara, i.Tipe_Item", P,
    )
    totals = pivot.groupby("Negara")["Revenue"].sum().sort_values(ascending=False)
    top10 = totals.head(10).index.tolist()
    pt = (pivot[pivot["Negara"].isin(top10)]
          .pivot_table(index="Negara", columns="Tipe_Item", values="Revenue", fill_value=0)
          .round(0).reindex(top10))
    pt.index.name = "Negara"
    pt.columns.name = None  # buang label 'Tipe_Item' di pojok tabel
    st.dataframe(pt.style.format("${:,.0f}").background_gradient(cmap="GnBu", axis=None),
                 use_container_width=True)

    st.markdown("##### Unduh Data Ringkasan")
    summary = run(
        f"SELECT w.Tanggal AS Tanggal, w.Hari AS Hari, l.Negara AS Negara, "
        f"i.Tipe_Item AS 'Tipe Produk', COUNT(*) AS 'Jumlah Transaksi', "
        f"ROUND(SUM(f.Gross_Rev),2) AS 'Gross Revenue', ROUND(SUM(f.Artist_Revenue),2) AS 'Pendapatan Artis' "
        f"{BASE}{WHERE} GROUP BY w.Tanggal, l.Negara, i.Tipe_Item ORDER BY 6 DESC", P,
    )
    st.download_button("Unduh CSV (agregat sesuai filter)", summary.to_csv(index=False).encode("utf-8"),
                       "ringkasan_terfilter.csv", "text/csv")
    st.dataframe(summary.head(200), use_container_width=True, height=320)
