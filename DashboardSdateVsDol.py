import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Claim Portfolio Dashboard", layout="wide")

st.title("📊 Claim Portfolio & Loss Timing Dashboard")

# ===============================
# UPLOAD DATA
# ===============================
uploaded_file = st.file_uploader(
    "Upload Excel data (template standar)",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("Silakan upload file Excel untuk memulai analisis.")
    st.stop()

df_raw = pd.read_excel(uploaded_file)

st.subheader("📄 Preview Data Mentah")
st.dataframe(df_raw.head())

# ===============================
# DATA VALIDATION
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
    "Kategori Risiko"
]

missing_required = [c for c in REQUIRED_COLS if c not in df_raw.columns]

if missing_required:
    st.error(f"Kolom wajib tidak ditemukan: {missing_required}")
    st.stop()

# ===============================
# DATA CLEANING
# ===============================
df = df_raw.copy()

# Convert date columns
df["StartDate"] = pd.to_datetime(df["StartDate"], errors="coerce")
df["Date of Loss"] = pd.to_datetime(df["Date of Loss"], errors="coerce")

initial_rows = len(df)

# Drop missing critical
df = df.dropna(subset=REQUIRED_COLS)

after_drop_rows = len(df)

# Fill optional columns
for col in OPTIONAL_COLS:
    if col in df.columns:
        df[col] = df[col].fillna("UNKNOWN")
    else:
        df[col] = "UNKNOWN"

# ===============================
# DEDUPLICATION
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
        "Kategori Risiko": "first"
    })
)

after_dedup_rows = len(df)

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

# ===============================
# DATA QUALITY SUMMARY
# ===============================
st.subheader("⚠️ Data Quality Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Total Baris Awal", initial_rows)
col2.metric("Baris Setelah Cleaning", after_drop_rows)
col3.metric("Klaim Unik (Final)", after_dedup_rows)

# ===============================
# FILTERS
# ===============================
st.sidebar.header("🔍 Filter Data")

filter_okupasi = st.sidebar.multiselect(
    "Kode Okupasi",
    sorted(df["Kode Okupasi"].unique()),
    default=df["Kode Okupasi"].unique()
)

filter_occupancy = st.sidebar.multiselect(
    "Occupancy",
    sorted(df["Occupancy"].unique()),
    default=df["Occupancy"].unique()
)

filter_risk = st.sidebar.multiselect(
    "Kategori Risiko",
    sorted(df["Kategori Risiko"].unique()),
    default=df["Kategori Risiko"].unique()
)

df_f = df[
    (df["Kode Okupasi"].isin(filter_okupasi)) &
    (df["Occupancy"].isin(filter_occupancy)) &
    (df["Kategori Risiko"].isin(filter_risk))
]

# ===============================
# DASHBOARD
# ===============================
st.subheader("📈 Loss Timing Analysis")

col1, col2 = st.columns(2)

# Frequency by loss timing
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

col1.plotly_chart(fig_freq, use_container_width=True)

# Amount by loss timing
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

col2.plotly_chart(fig_amt, use_container_width=True)

# ===============================
# CAUSE OF LOSS CONTRIBUTION
# ===============================
st.subheader("🎯 Cause of Loss Contribution")

col3, col4 = st.columns(2)

# Frequency contribution
cause_freq = (
    df_f
    .groupby("Cause of Loss")
    .size()
    .reset_index(name="Frekuensi")
)

cause_freq["% Kontribusi"] = cause_freq["Frekuensi"] / cause_freq["Frekuensi"].sum() * 100

fig_cf = px.pie(
    cause_freq,
    names="Cause of Loss",
    values="% Kontribusi",
    title="% Kontribusi Frekuensi by Cause of Loss"
)

col3.plotly_chart(fig_cf, use_container_width=True)

# Amount contribution
cause_amt = (
    df_f
    .groupby("Cause of Loss")["Claim Amount"]
    .sum()
    .reset_index()
)

cause_amt["% Kontribusi"] = cause_amt["Claim Amount"] / cause_amt["Claim Amount"].sum() * 100

fig_ca = px.pie(
    cause_amt,
    names="Cause of Loss",
    values="% Kontribusi",
    title="% Kontribusi Amount by Cause of Loss"
)

col4.plotly_chart(fig_ca, use_container_width=True)

# ===============================
# FINAL TABLE
# ===============================
st.subheader("📋 Data Klaim Final (Setelah Cleaning)")
st.dataframe(df_f)
