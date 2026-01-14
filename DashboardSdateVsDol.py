import streamlit as st
import pandas as pd

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Bundling Rate Calculator",
    layout="wide"
)

st.title("📊 Bundling Rate Calculator")
st.caption("by Divisi Aktuaria Askrindo")

# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data(show_spinner="Loading rate matrix...")
def load_rate_matrix(path):
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip()
    return df

df_rate = load_rate_matrix("rate_matrix_produk.xlsx")

# =====================================================
# CORE ENGINE
# =====================================================
def get_rate(df, coverage, subcover, selected_factors):

    q = (df["Coverage"] == coverage) & (df["Subcover"] == subcover)

    for col, val in selected_factors.items():
        q &= (
            (df[col].astype(str) == str(val)) |
            (df[col].isna())
        )

    result = df[q].copy()

    if result.empty:
        raise ValueError(f"Rate tidak ditemukan: {coverage} - {subcover}")

    factor_cols = [
        c for c in df.columns
        if c not in ["Coverage", "Subcover", "Rate"]
    ]

    result["priority"] = result[factor_cols].isna().sum(axis=1)

    return float(result.sort_values("priority").iloc[0]["Rate"])


# =====================================================
# SESSION STATE
# =====================================================
if "products" not in st.session_state:
    st.session_state.products = [{}]

if "results" not in st.session_state:
    st.session_state.results = None


# =====================================================
# INPUT PRODUK (1 ROW PER PRODUK)
# =====================================================
st.subheader("Input Produk")

coverage_list = sorted(df_rate["Coverage"].dropna().unique())

for i, p in enumerate(st.session_state.products):

    cols = st.columns([2, 3, 2, 2, 2, 0.5])

    # -------- Coverage --------
    with cols[0]:
        p["Coverage"] = st.selectbox(
            "Coverage" if i == 0 else "",
            coverage_list,
            key=f"coverage_{i}"
        )

    # -------- Subcover --------
    subcover_options = (
        df_rate[df_rate["Coverage"] == p["Coverage"]]["Subcover"]
        .dropna()
        .unique()
    )

    with cols[1]:
        p["Subcover"] = st.selectbox(
            "Subcover" if i == 0 else "",
            sorted(subcover_options),
            key=f"subcover_{i}"
        )

    # -------- Context-aware factors --------
    df_filt = df_rate[
        (df_rate["Coverage"] == p["Coverage"]) &
        (df_rate["Subcover"] == p["Subcover"])
    ]

    factor_cols = [
        c for c in df_filt.columns
        if c not in ["Coverage", "Subcover", "Rate"]
        and df_filt[c].dropna().nunique() > 0
    ]

    factors = {}
    df_context = df_filt.copy()

    for idx, col in enumerate(factor_cols[:3]):
        with cols[2 + idx]:

            values = (
                df_context[col]
                .dropna()
                .astype(str)
                .unique()
            )

            if len(values) == 0:
                continue

            selected = st.selectbox(
                col if i == 0 else "",
                sorted(values),
                key=f"{col}_{i}"
            )

            factors[col] = selected

            # 🔥 context filtering
            df_context = df_context[
                (df_context[col].astype(str) == str(selected)) |
                (df_context[col].isna())
            ]

    p["Factors"] = factors
    p["ExpectedFactors"] = factor_cols

    # -------- Delete button --------
    with cols[5]:
        if len(st.session_state.products) > 1:
            if st.button("❌", key=f"del_{i}"):
                st.session_state.products.pop(i)
                st.session_state.results = None
                st.rerun()


# =====================================================
# ADD PRODUCT
# =====================================================
if st.button("➕ Tambah Produk"):
    st.session_state.products.append({})
    st.session_state.results = None
    st.rerun()


# =====================================================
# VALIDATION
# =====================================================
def validate_products(products):
    for idx, p in enumerate(products, start=1):
        expected = p.get("ExpectedFactors", [])
        filled = p.get("Factors", {})

        if expected and len(filled) < len(expected):
            return False, f"Produk {idx}: Faktor risiko belum lengkap"

    return True, None


# =====================================================
# HITUNG RATE
# =====================================================
if st.button("Hitung Rate"):

    valid, msg = validate_products(st.session_state.products)

    if not valid:
        st.error(f"❌ {msg}")
    else:
        results = []
        total_rate = 0

        for p in st.session_state.products:
            rate = get_rate(
                df_rate,
                p["Coverage"],
                p["Subcover"],
                p["Factors"]
            )

            results.append({
                "Coverage": p["Coverage"],
                "Subcover": p["Subcover"],
                **p["Factors"],
                "Rate (%)": rate * 100
            })

            total_rate += rate

        st.session_state.results = (results, total_rate)


# =====================================================
# OUTPUT
# =====================================================
if st.session_state.results:

    results, total_rate = st.session_state.results

    st.subheader("Bundling Product")

    df_out = pd.DataFrame(results)
    df_out.insert(0, "No", range(1, len(df_out) + 1))

    df_out["Rate (%)"] = df_out["Rate (%)"].map(lambda x: f"{x:.4f}%")

    st.dataframe(df_out, use_container_width=True, hide_index=True)

    st.success(
        f"✅ **Total Bundling Rate: {total_rate * 100:.4f}%**"
    )

    st.warning(
        """
        **Catatan:**
        1. Maksimum akuisisi adalah **20%**, kecuali terdapat ketentuan dari **Regulator**.
        2. Untuk pemberian **rate di bawah rate acuan**, dapat dilakukan **perhitungan profitability checking**.
        """
    )
