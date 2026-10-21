import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Sales Forecasting",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Sales Forecasting")
st.write(
    "Upload your historical sales data to get started."
)

uploaded_file = st.file_uploader(
    "Upload sales data (CSV)",
    type=["csv"]
)

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.subheader("Your sales data")
    st.dataframe(df, use_container_width=True)

    st.write("Available columns:")