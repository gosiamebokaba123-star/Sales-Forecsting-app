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
st.subheader("1. Detecting your sales data")

columns = list(df.columns)

# Find the date column automatically
date_candidates = [
    c for c in columns
    if any(word in c.lower() for word in ["date", "day", "time"])
]

date_col = date_candidates[0] if date_candidates else None

if date_col is None:
    for c in columns:
        parsed_dates = pd.to_datetime(df[c], errors="coerce", dayfirst=True)
        if parsed_dates.notna().mean() >= 0.7:
            date_col = c
            break

# Find the sales column automatically
sales_candidates = [
    c for c in columns
    if any(word in c.lower() for word in [
        "sales", "revenue", "turnover", "total_sales",
        "sales_zar", "amount"
    ])
]

sales_col = sales_candidates[0] if sales_candidates else None

if sales_col is None:
    numeric_candidates = [
        c for c in columns
        if c != date_col and
        pd.to_numeric(
            df[c].astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
            errors="coerce"
        ).notna().mean() >= 0.7
    ]
    if numeric_candidates:
        sales_col = numeric_candidates[0]

if date_col is None or sales_col is None or date_col == sales_col:
    st.error(
        "I couldn't reliably identify your date and sales columns. "
        "Please check that your CSV contains dates and sales amounts."
    )
    st.write("Columns found:", columns)
    st.stop()

st.success(
    f"Automatically detected — Date: **{date_col}** | "
    f"Sales: **{sales_col}**"
)

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
# Sales Analyst: plain-English insights
st.subheader("Sales Analyst")
st.write("Here is what your sales data tells us.")

if len(data) >= 2:
    midpoint = max(1, len(data) // 2)
    first_half_avg = data["sales"].iloc[:midpoint].mean()
    second_half_avg = data["sales"].iloc[midpoint:].mean()

    if first_half_avg > 0:
        change_pct = (
            (second_half_avg - first_half_avg) / first_half_avg
        ) * 100
    else:
        change_pct = 0

    if change_pct > 5:
        st.success(
            f"Sales are trending upward. The later period averages "
            f"{change_pct:.1f}% higher than the earlier period."
        )
    elif change_pct < -5:
        st.warning(
            f"Sales are trending downward. The later period averages "
            f"{abs(change_pct):.1f}% lower than the earlier period."
        )
    else:
        st.info("Sales are broadly stable between the two periods.")

    weekday_data = data.copy()
    weekday_data["day_name"] = weekday_data["date"].dt.day_name()
    weekday_avg = weekday_data.groupby("day_name")["sales"].mean()

    best_weekday = weekday_avg.idxmax()
    weakest_weekday = weekday_avg.idxmin()

    st.write(
        f"**Strongest weekday:** {best_weekday} "
        f"(average R {weekday_avg.max():,.2f})."
    )
    st.write(
        f"**Weakest weekday:** {weakest_weekday} "
        f"(average R {weekday_avg.min():,.2f})."
    )

    st.caption(
        "Suggestion: compare weaker days with staffing, stock availability "
        "and promotions before deciding what to change."
    )
else:
    st.info("Upload at least two dates to generate sales insights.")

st.write("TEST: Growth sectionreached")
# Sales growth comparison
st.subheader("Sales Growth Comparison")

if len(data) >= 4:
    split_point = len(data) // 2
    earlier_period = data.iloc[:split_point]
    later_period = data.iloc[split_point:]

    earlier_total = earlier_period["sales"].sum()
    later_total = later_period["sales"].sum()

    earlier_avg = earlier_period["sales"].mean()
    later_avg = later_period["sales"].mean()

    c1, c2, c3 = st.columns(3)
    c1.metric("Earlier period sales", f"R {earlier_total:,.2f}")
    c2.metric("Later period sales", f"R {later_total:,.2f}")

    if earlier_avg > 0:
        growth = ((later_avg - earlier_avg) / earlier_avg) * 100
        c3.metric("Average daily sales change", f"{growth:+.1f}%")

        if growth > 5:
            st.success(
                "Average daily sales are higher in the later period. "
                "Check which products, days or promotions may have helped."
            )
        elif growth < -5:
            st.warning(
                "Average daily sales are lower in the later period. "
                "Review stock availability, customer traffic and recent changes."
            )
        else:
            st.info(
                "Average daily sales are relatively stable between the periods."
            )
    else:
        st.info(
            "A percentage comparison isn't available because the earlier "
            "period's average sales are zero."
        )
else:
    st.info("Upload at least four recorded dates to compare sales periods.")

fig = px.line(
    data,
    x="date",
    y="sales",
    title="Historical sales",
    labels={"date": "Date", "sales": "Sales (R)"},
    markers=True
)
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