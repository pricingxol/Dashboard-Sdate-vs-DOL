import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="Claim Loss Timing Dashboard",
    layout="wide"
)

st.title("📊 Claim Loss Timing & Cause Analysis")

# ===============================
# UPLOAD DATA
# ===============================
uploaded_file = st.file_uploader(
    "Upload Excel Data Klaim",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("Silakan upload file Excel untuk memulai.")
    st.stop()

df_raw = pd.read_excel(uploaded_file)

st.subheader("📄 Preview Data Mentah")
st.dataframe(df_raw.head())

# ===============================
# COLUMN MAPPING (ADAPTIF KE EXCEL USER)
# ===============================
COLUMN_MAPPING = {
    "Kode okupasi": "Kode Okupasi",
    "kode okupasi": "Kode Okupasi",
    "Kategori Okupasi": "Kategori Risiko",
    "kategori okupasi": "Kategori Risiko",
    "EDate": "End Date",
    "Edate": "End Date",
    "COB": "Channel Business"
}

df_raw = df_raw.rename(columns=COLUMN_MAPPING)

# ===============================
# REQUIRED & OPTIONAL COLUMNS
# ===============================
REQUIRED_COLS = [
    "Nomor klaim",
    "StartDate",
    "Date of Loss",
    "Claim Amount",
    "Cause of Loss"
]

OPTIONAL_COLS = [
    "Kode Okupasi",
    "Occupancy",
    "Kategori Risiko",
    "Channel Business"
]

missing_required = [c for c in REQUIRED_COLS if c not in df_raw.columns]

if missing_required:
    st.error(f"Kolom wajib tidak ditemukan: {missing_required}")
    st.stop()

# ===============================
# DATA CLEANING
# ===============================
df = df_raw.copy()
initial_rows = len(df)

# Date parsing
df["StartDate"] = pd.to_datetime(df["StartDate"], errors="coerce")
df["Date of Loss"] = pd.to_datetime(df["Date of Loss"], errors="coerce")

# Drop missing critical
df = df.dropna(subset=REQUIRED_COLS)
after_drop = len(df)

# Optional columns handling
for col in OPTIONAL_COLS:
    if col not in df.columns:
        df[col] = "ALL"
    else:
        df[col] = df[col].fillna("UNKNOWN")

# ===============================
# DEDUPLICATION (1 Nomor Klaim = 1 Loss)
# ===============================
df = (
    df
    .groupby("Nomor klaim", as_index=False)
    .agg({
        "StartDate": "min",
        "Date of Loss": "min",
        "Claim Amount": "sum",
        "Cause of Loss": "first",
        "Kode Okupasi": "first",
        "Occupancy": "first",
        "Kategori Risiko": "first",
        "Channel Business": "first"
    })
)

after_dedup = len(df)

# ===============================
# FEATURE ENGINEERING
# ===============================
df["Loss Lag Days"] = (df["Date of Loss"] - df["StartDate"]).dt.days
df["Loss Lag Months"] = df["Loss Lag Days"] / 30

def loss_bucket(x):
    if x <= 3:
        return "0–3 bulan"
    elif x <= 6:
        return ">3–6 bulan"
    elif x <= 12:
        return ">6–12 bulan"
    elif x <= 24:
        return ">12–24 bulan"
    else:
        return ">24 bulan"

df["Loss Timing Bucket"] = df["Loss Lag Months"].apply(loss_bucket)

df["UY"] = df["StartDate"].dt.year.astype(str)

# ===============================
# DATA QUALITY SUMMARY
# ===============================
st.subheader("⚠️ Data Quality Summary")
c1, c2, c3 = st.columns(3)
c1.metric("Total Baris Awal", initial_rows)
c2.metric("Setelah Cleaning", after_drop)
c3.metric("Klaim Unik Dianalisis", after_dedup)

# ===============================
# SIDEBAR FILTERS
# ===============================
st.sidebar.header("🔍 Filter Data")

def safe_multiselect(label, col):
    values = sorted(df[col].unique())
    return st.sidebar.multiselect(label, values, default=values)

filter_risk = safe_multiselect("Kategori Risiko", "Kategori Risiko")
filter_occ = safe_multiselect("Occupancy", "Occupancy")
filter_col = safe_multiselect("Cause of Loss", "Cause of Loss")
filter_ch = safe_multiselect("Channel Business", "Channel Business")

df_f = df[
    (df["Kategori Risiko"].isin(filter_risk)) &
    (df["Occupancy"].isin(filter_occ)) &
    (df["Cause of Loss"].isin(filter_col)) &
    (df["Channel Business"].isin(filter_ch))
]

# ===============================
# DASHBOARD
# ===============================
st.subheader("📈 Loss Timing Analysis")

left, right = st.columns(2)

freq = (
    df_f
    .groupby("Loss Timing Bucket")
    .size()
    .reset_index(name="Frekuensi Klaim")
)

fig_freq = px.bar(
    freq,
    x="Loss Timing Bucket",
    y="Frekuensi Klaim",
    title="Frekuensi Klaim berdasarkan Loss Timing"
)

left.plotly_chart(fig_freq, use_container_width=True)

amt = (
    df_f
    .groupby("Loss Timing Bucket")["Claim Amount"]
    .sum()
    .reset_index()
)

fig_amt = px.bar(
    amt,
    x="Loss Timing Bucket",
    y="Claim Amount",
    title="Amount Klaim berdasarkan Loss Timing"
)

right.plotly_chart(fig_amt, use_container_width=True)

# ===============================
# CAUSE OF LOSS CONTRIBUTION
# ===============================
st.subheader("🎯 Cause of Loss Contribution")

c3, c4 = st.columns(2)

cause_freq = (
    df_f
    .groupby("Cause of Loss")
    .size()
    .reset_index(name="Frekuensi")
)

cause_freq["% Kontribusi"] = (
    cause_freq["Frekuensi"] / cause_freq["Frekuensi"].sum() * 100
)

fig_cf = px.pie(
    cause_freq,
    names="Cause of Loss",
    values="% Kontribusi",
    title="% Kontribusi Frekuensi"
)

c3.plotly_chart(fig_cf, use_container_width=True)

cause_amt = (
    df_f
    .groupby("Cause of Loss")["Claim Amount"]
    .sum()
    .reset_index()
)

cause_amt["% Kontribusi"] = (
    cause_amt["Claim Amount"] / cause_amt["Claim Amount"].sum() * 100
)

fig_ca = px.pie(
    cause_amt,
    names="Cause of Loss",
    values="% Kontribusi",
    title="% Kontribusi Amount"
)

c4.plotly_chart(fig_ca, use_container_width=True)

# ===============================
# FINAL TABLE
# ===============================
st.subheader("📋 Data Klaim (Final)")
st.dataframe(df_f)
