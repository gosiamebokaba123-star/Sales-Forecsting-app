import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Sales Forecasting",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Sales Forecasting Dashboard")
st.write("Understand your sales performance and forecast future sales.")

uploaded_file = st.file_uploader(
    "Upload your sales data (CSV)",
    type=["csv"]
)

if uploaded_file is None:
    st.info(
        "Upload a CSV containing a date column and a sales column to begin."
    )
    st.stop()

try:
    df = pd.read_csv(uploaded_file)
except Exception as e:
    st.error(f"Could not read the CSV: {e}")
    st.stop()

if df.empty or len(df.columns) < 2:
    st.error("Your CSV is empty or does not contain enough columns.")
    st.stop()

st.subheader("1. Select your data columns")

columns = list(df.columns)

date_candidates = [
    c for c in columns
    if any(word in c.lower() for word in ["date", "day", "time"])
]
sales_candidates = [
    c for c in columns
    if any(word in c.lower() for word in [
        "sales", "revenue", "amount", "total", "turnover"
    ])
]

date_default = columns.index(date_candidates[0]) if date_candidates else 0
sales_default = (
    columns.index(sales_candidates[0])
    if sales_candidates
    else min(1, len(columns) - 1)
)

col1, col2 = st.columns(2)

with col1:
    date_col = st.selectbox(
        "Date column",
        columns,
        index=date_default
    )

with col2:
    sales_col = st.selectbox(
        "Sales amount column",
        columns,
        index=sales_default
    )

if date_col == sales_col:
    st.error("Choose different columns for dates and sales.")
    st.stop()

data = pd.DataFrame({
    "date": pd.to_datetime(df[date_col], errors="coerce", dayfirst=True),
    "sales": pd.to_numeric(
        df[sales_col].astype(str).str.replace(
            r"[^0-9.\-]", "", regex=True
        ),
        errors="coerce"
    )
})

data = data.dropna(subset=["date", "sales"])
data = data[data["sales"] >= 0]
data["date"] = data["date"].dt.normalize()

data = (
    data.groupby("date", as_index=False)["sales"]
    .sum()
    .sort_values("date")
)

if data.empty:
    st.error(
        "No valid records found. Check your selected columns "
        "and make sure the dates and sales amounts are valid."
    )
    st.stop()

st.subheader("2. Sales performance")

total_sales = data["sales"].sum()
average_sales = data["sales"].mean()
best_day = data.loc[data["sales"].idxmax()]

k1, k2, k3 = st.columns(3)

k1.metric("Total sales", f"R {total_sales:,.2f}")
k2.metric("Average sales per recorded day", f"R {average_sales:,.2f}")
k3.metric(
    "Best sales day",
    f"R {best_day['sales']:,.2f}",
    help=str(best_day["date"].date())
)

st.caption(
    f"Showing {len(data):,} recorded dates, from "
    f"{data['date'].min().date()} to {data['date'].max().date()}."
)

fig = px.line(
    data,
    x="date",
    y="sales",
    title="Historical sales",
    labels={"date": "Date", "sales": "Sales (R)"},
    markers=True
)
fig.update_layout(hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

with st.expander("View cleaned sales data"):
    st.dataframe(data, use_container_width=True)

st.divider()
st.subheader("3. Forecast future sales")

forecast_days = st.selectbox(
    "Forecast period",
    [7, 30, 90],
    index=1,
    format_func=lambda n: f"{n} days"
)

if len(data) < 2:
    st.warning("At least two different dates are required to forecast.")
    st.stop()

if st.button("Generate sales forecast", type="primary"):
    try:
        from prophet import Prophet

        forecast_data = data.rename(
            columns={"date": "ds", "sales": "y"}
        )

        with st.spinner("Analysing your sales history..."):
            model = Prophet(
                yearly_seasonality="auto",
                weekly_seasonality="auto",
                daily_seasonality=False
            )
            model.fit(forecast_data)

            future = model.make_future_dataframe(
                periods=forecast_days,
                freq="D"
            )
            prediction = model.predict(future)

        future_forecast = prediction[
            prediction["ds"] > forecast_data["ds"].max()
        ].copy()

        future_forecast["yhat"] = future_forecast["yhat"].clip(lower=0)
        future_forecast["yhat_lower"] = (
            future_forecast["yhat_lower"].clip(lower=0)
        )
        future_forecast["yhat_upper"] = (
            future_forecast["yhat_upper"].clip(lower=0)
        )

        st.session_state["sales_forecast"] = future_forecast[
            ["ds", "yhat", "yhat_lower", "yhat_upper"]
        ].copy()
        st.session_state["forecast_days"] = forecast_days

    except Exception as e:
        st.error(f"Forecast could not be generated: {e}")
        st.info(
            "Check that Prophet is listed in requirements.txt "
            "and that your sales data contains valid dates and numbers."
        )

if "sales_forecast" in st.session_state:
    result = st.session_state["sales_forecast"]

    st.subheader(
        f"Your {st.session_state['forecast_days']}-day forecast"
    )

    expected_total = result["yhat"].sum()
    a, b = st.columns(2)
    a.metric("Forecast total sales", f"R {expected_total:,.2f}")
    b.metric("Average forecast per day", f"R {result['yhat'].mean():,.2f}")

    history_plot = data.rename(
        columns={"date": "Date", "sales": "Sales"}
    )
    history_plot["Type"] = "Actual sales"

    forecast_plot = result.rename(
        columns={
            "ds": "Date",
            "yhat": "Sales",
            "yhat_lower": "Lower estimate",
            "yhat_upper": "Upper estimate"
        }
    )
    forecast_plot["Type"] = "Forecast"

    chart = px.line(
        history_plot,
        x="Date",
        y="Sales",
        title="Actual sales and future forecast",
        labels={"Sales": "Sales (R)"}
    )
    chart.add_scatter(
        x=forecast_plot["Date"],
        y=forecast_plot["Sales"],
        mode="lines",
        name="Forecast"
    )
    chart.add_scatter(
        x=forecast_plot["Date"],
        y=forecast_plot["Upper estimate"],
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip"
    )
    chart.add_scatter(
        x=forecast_plot["Date"],
        y=forecast_plot["Lower estimate"],
        mode="lines",
        line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(100, 149, 237, 0.18)",
        name="Forecast range",
        hoverinfo="skip"
    )
    st.plotly_chart(chart, use_container_width=True)

    download_data = result.rename(
        columns={
            "ds": "date",
            "yhat": "forecast_sales",
            "yhat_lower": "lower_estimate",
            "yhat_upper": "upper_estimate"
        }
    )

    st.dataframe(download_data, use_container_width=True)

    st.download_button(
        "Download forecast CSV",
        data=download_data.to_csv(index=False).encode("utf-8"),
        file_name="sales_forecast.csv",
        mime="text/csv"
    )

st.caption(
    "Forecasts are estimates based on historical data, not guarantees "
    "of future sales. Results depend on data quality and seasonality."
)