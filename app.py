import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from prophet import Prophet

st.set_page_config(
    page_title="Sales Intelligence",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Sales Intelligence")
st.caption("Understand your sales. Forecast what comes next.")
uploaded_file = st.file_uploader(
    "Upload your sales CSV",
    type=["csv"]
)

if uploaded_file is None:
    st.info("Upload a CSV containing a date column and a sales column to begin.")
    st.stop()

<<<<<<< HEAD
    st.write("Available columns:")
=======
try:
    df = pd.read_csv(uploaded_file)
except Exception as e:
    st.error(f"Could not read the CSV: {e}")
    st.stop()

if df.empty:
    st.error("Your CSV is empty.")
    st.stop()

st.subheader("1. Prepare your data")

columns = df.columns.tolist()

# Automatically detect common column names
date_candidates = [
    "date", "ds", "day", "order_date", "transaction_date"
]
sales_candidates = [
    "sales_zar", "sales", "revenue", "total_sales",
    "amount", "y"
]

def find_column(candidates):
    for candidate in candidates:
        for column in columns:
            if column.lower().strip() == candidate:
                return column
    return columns[0]

default_date = find_column(date_candidates)
default_sales = find_column(sales_candidates)

left, right = st.columns(2)

with left:
    date_col = st.selectbox(
        "Date column",
        columns,
        index=columns.index(default_date)
    )

with right:
    sales_col = st.selectbox(
        "Sales / revenue column",
        columns,
        index=columns.index(default_sales)
    )

# Convert selected fields to the correct data types
data = df[[date_col, sales_col]].copy()
data.columns = ["ds", "y"]

data["ds"] = pd.to_datetime(data["ds"], errors="coerce")

# Support currency symbols and comma-separated numbers
data["y"] = pd.to_numeric(
    data["y"].astype(str)
    .str.replace(",", "", regex=False)
    .str.replace("R", "", regex=False)
    .str.replace(" ", "", regex=False),
    errors="coerce"
)

data = data.dropna(subset=["ds", "y"])
data = data[data["y"] >= 0]

# Combine multiple transactions on the same date
daily = (
    data.groupby("ds", as_index=False)["y"]
    .sum()
    .sort_values("ds")
)

if len(daily) < 2:
    st.error("We need at least two valid dates with sales data.")
    st.stop()

st.success(
    f"Loaded {len(daily):,} sales days, "
    f"from {daily['ds'].min().date()} "
    f"to {daily['ds'].max().date()}."
)

st.subheader("2. Business overview")

total_sales = daily["y"].sum()
average_sales = daily["y"].mean()
best_idx = daily["y"].idxmax()
best_day = daily.loc[best_idx]

m1, m2, m3 = st.columns(3)

m1.metric("Total sales", f"R{total_sales:,.2f}")
m2.metric("Average sales per recorded day", f"R{average_sales:,.2f}")
m3.metric(
    "Best sales day",
    f"R{best_day['y']:,.2f}",
    help=str(best_day["ds"].date())
)

# Actual sales trend
actual_fig = go.Figure()
actual_fig.add_trace(
    go.Scatter(
        x=daily["ds"],
        y=daily["y"],
        mode="lines",
        name="Actual sales",
        line=dict(width=2)
    )
)
actual_fig.update_layout(
    title="Historical sales trend",
    xaxis_title="Date",
    yaxis_title="Sales (R)",
    hovermode="x unified"
)
st.plotly_chart(actual_fig, use_container_width=True)

st.subheader("3. Forecast future sales")

if len(daily) < 30:
    st.warning(
        "You have fewer than 30 recorded sales days. "
        "The forecast may be unreliable. More history is recommended."
    )

horizon = st.selectbox(
    "How far ahead should we forecast?",
    [7, 30, 90],
    index=1,
    format_func=lambda days: f"{days} days"
)

if st.button("Generate sales forecast", type="primary"):
    if daily["ds"].nunique() < 2:
        st.error("There are not enough distinct dates to forecast.")
        st.stop()

    try:
        with st.spinner("Training Prophet and generating predictions..."):
            model_data = daily.rename(
                columns={"ds": "ds", "y": "y"}
            )

            model = Prophet(
                yearly_seasonality="auto",
                weekly_seasonality=(
                    len(daily) >= 14
                ),
                daily_seasonality=False
            )

            model.fit(model_data)

            future = model.make_future_dataframe(
                periods=horizon,
                freq="D"
            )

            forecast = model.predict(future)

            # Keep only dates after the final recorded sale
            last_date = daily["ds"].max()
            future_forecast = forecast[
                forecast["ds"] > last_date
            ].head(horizon).copy()

            if future_forecast.empty:
                st.error("Prophet did not return future predictions.")
                st.stop()

            future_forecast["yhat"] = (
                future_forecast["yhat"].clip(lower=0)
            )
            future_forecast["yhat_lower"] = (
                future_forecast["yhat_lower"].clip(lower=0)
            )
            future_forecast["yhat_upper"] = (
                future_forecast["yhat_upper"].clip(lower=0)
            )

            st.session_state["forecast_results"] = (
                future_forecast
            )
            st.session_state["forecast_horizon"] = horizon

    except Exception as e:
        st.error(f"Forecast failed: {e}")

if "forecast_results" in st.session_state:
    result = st.session_state["forecast_results"]
    chosen_horizon = st.session_state["forecast_horizon"]

    st.markdown("### Your forecast results")

    expected_total = result["yhat"].sum()
    average_forecast = result["yhat"].mean()

    a, b = st.columns(2)
    a.metric(
        f"Forecast sales over {chosen_horizon} days",
        f"R{expected_total:,.2f}"
    )
    b.metric(
        "Average predicted daily sales",
        f"R{average_forecast:,.2f}"
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=daily["ds"],
            y=daily["y"],
            mode="lines",
            name="Historical sales"
        )
    )

    # Confidence interval band
    fig.add_trace(
        go.Scatter(
            x=result["ds"].tolist()
            + result["ds"].tolist()[::-1],
            y=result["yhat_upper"].tolist()
            + result["yhat_lower"].tolist()[::-1],
            fill="toself",
            fillcolor="rgba(80, 140, 220, 0.18)",
            line=dict(color="rgba(255,255,255,0)"),
            name="Uncertainty range",
            hoverinfo="skip"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=result["ds"],
            y=result["yhat"],
            mode="lines",
            name="Predicted sales",
            line=dict(width=3, dash="dash")
        )
    )

    fig.update_layout(
        title="Historical sales and future forecast",
        xaxis_title="Date",
        yaxis_title="Sales (R)",
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    export = result[
        ["ds", "yhat", "yhat_lower", "yhat_upper"]
    ].rename(
        columns={
            "ds": "date",
            "yhat": "predicted_sales_zar",
            "yhat_lower": "lower_estimate_zar",
            "yhat_upper": "upper_estimate_zar"
        }
    )

    st.markdown("### Forecast details")
    st.dataframe(export, use_container_width=True)

    st.download_button(
        "Download forecast CSV",
        data=export.to_csv(index=False).encode("utf-8"),
        file_name="sales_forecast.csv",
        mime="text/csv"
    )

    st.caption(
        "Forecasts are estimates based on historical patterns, "
        "not guaranteed sales. Results depend on data quality "
        "and the amount of history available."
    )
>>>>>>> 8f0931a (requrements.txt)
