import hashlib
import math
import re

import streamlit as st
import pandas as pd
import plotly.express as px


def calculate_sales_target(data, improvement_pct):
    try:
        improvement_pct = float(improvement_pct)
    except (TypeError, ValueError) as exc:
        raise ValueError("Improvement percentage must be a number.") from exc

    if not math.isfinite(improvement_pct) or improvement_pct < 0:
        raise ValueError(
            "Improvement percentage must be a finite, nonnegative number."
        )
    if data.empty or "sales" not in data:
        raise ValueError("Sales data must contain at least one sales value.")

    sales = pd.to_numeric(data["sales"], errors="coerce")
    if (
        sales.isna().any()
        or not sales.map(math.isfinite).all()
        or (sales < 0).any()
    ):
        raise ValueError("Sales values must be finite and nonnegative.")

    historical_average = sales.mean()
    target_average = historical_average * (1 + improvement_pct / 100)
    return {
        "historical_average": historical_average,
        "target_average": target_average,
        "additional_per_date": target_average - historical_average,
    }


def answer_sales_question(question, data, forecast=None):
    question = question.strip().lower()

    if not question:
        return "Enter a question about your sales data to get an answer."

    recommendation_terms = [
        "advice", "recommend", "suggest", "how can i", "how do i",
        "improve", "increase", "boost", "grow", "more sales",
        "ways to",
    ]
    if any(term in question for term in recommendation_terms):
        weekday_data = data.copy()
        weekday_data["day_name"] = weekday_data["date"].dt.day_name()
        weekday_average = weekday_data.groupby("day_name")["sales"].mean()

        observations = [
            f"Total historical sales were R {data['sales'].sum():,.2f} "
            f"across {len(data):,} recorded dates.",
            f"Average historical sales were R {data['sales'].mean():,.2f} "
            "per recorded date.",
        ]
        if not weekday_average.empty:
            strongest_day = weekday_average.idxmax()
            weakest_day = weekday_average.idxmin()
            observations.extend([
                f"{strongest_day} had the highest average recorded sales "
                f"(R {weekday_average[strongest_day]:,.2f}).",
                f"{weakest_day} had the lowest average recorded sales "
                f"(R {weekday_average[weakest_day]:,.2f}).",
            ])

        limitation = ""
        if any(term in question for term in [
            "product", "customer", "category", "store", "region"
        ]):
            limitation = (
                "The uploaded data does not identify products or customers, "
                "so it cannot show which items or customer groups perform "
                "best."
            )

        return (
            "**What the data shows**\n\n"
            + "\n\n".join(f"- {item}" for item in observations)
            + (f"\n\n{limitation}" if limitation else "")
            + "\n\n**Suggestions to test**\n\n"
            "**1. Test a targeted offer on the weakest weekday.** "
            "Compare that weekday's sales with the same weekday in a "
            "similar pre-test period. Track profit after the offer, where "
            "possible, to check whether extra sales are worthwhile.\n\n"
            "**2. Investigate what happens on the strongest weekday.** "
            "Check stock, opening hours, and promotions for possible ideas "
            "to trial on other days; the sales data alone does not explain "
            "why that day is stronger. Compare the trial with a baseline "
            "from the same weekdays before the change, and track profit "
            "where possible.\n\n"
            "**3. Trial one simple add-on or repeat-visit prompt.** "
            "Use a consistent test period and compare daily sales with a "
            "similar baseline period. Track the cost of the offer and profit "
            "where possible; this dataset cannot identify which products or "
            "customers to target.\n\n"
            "These are hypotheses to test, not proven causes or guaranteed "
            "results. Change one thing at a time where practical and compare "
            "against a relevant baseline."
        )

    if any(word in question for word in [
        "forecast", "predict", "prediction", "future", "expected"
    ]):
        if forecast is None or forecast.empty:
            return (
                "There isn't a forecast for this upload yet. Generate a "
                "forecast below, then ask about the forecast results."
            )

        forecast_start = forecast["ds"].min().date()
        forecast_end = forecast["ds"].max().date()
        forecast_total = forecast["yhat"].sum()
        forecast_average = forecast["yhat"].mean()
        return (
            f"**Forecast estimate ({forecast_start} to {forecast_end}):** "
            f"the predicted total is R {forecast_total:,.2f}, averaging "
            f"R {forecast_average:,.2f} per forecast day. This is a model "
            "estimate, not historical sales or a guarantee."
        )

    limited_scope_terms = [
        "month", "monthly", "weekly", "year", "yearly", "quarter",
        "product", "customer", "store", "region", "category", "hour",
        "between", "since", "during", "from ", "last month", "last week",
        "last year", "last ", "this month", "this week", "this year",
        "past month", "past week", "past year", "past ",
    ]
    month_names = (
        "january|february|march|april|may|june|july|august|september|"
        "october|november|december"
    )
    is_weekday_question = "weekday" in question or "day of week" in question
    has_limited_scope = (
        any(term in question for term in limited_scope_terms)
        or re.search(rf"\b(?:{month_names})\b", question)
        or (
            re.search(r"\bweek\b", question)
            and not is_weekday_question
        )
    )

    if is_weekday_question:
        if has_limited_scope or any(word in question for word in [
            "trend", "recent", "lately", "increasing", "declining",
            "going up", "going down"
        ]):
            return (
                "I can't answer that weekday breakdown reliably for the "
                "requested time period or trend. I can compare average sales "
                "by weekday across all recorded dates."
            )

        weekday_data = data.copy()
        weekday_data["day_name"] = weekday_data["date"].dt.day_name()
        weekday_average = weekday_data.groupby("day_name")["sales"].mean()
        if any(word in question for word in ["weakest", "lowest", "worst"]):
            weekday = weekday_average.idxmin()
            label = "weakest"
        else:
            weekday = weekday_average.idxmax()
            label = "strongest"
        return (
            f"**Historical fact:** {weekday} was the {label} weekday by "
            f"average recorded sales, at R {weekday_average[weekday]:,.2f}. "
            "This uses only recorded dates for each weekday."
        )

    if has_limited_scope:
        return (
            "I can't answer that breakdown reliably. The uploaded data is "
            "available here as overall recorded daily sales, not as a "
            "monthly, product, customer, or custom date-range breakdown."
        )

    if any(word in question for word in [
        "trend", "recent", "lately", "increasing", "declining",
        "going up", "going down"
    ]):
        if len(data) < 4:
            return (
                "There are too few recorded dates to compare recent sales "
                "reliably. At least four recorded dates are needed."
            )

        split_at = max(2, len(data) - 7)
        recent = data.iloc[split_at:]
        previous = data.iloc[max(0, split_at - 7):split_at]
        if len(previous) < 2:
            return (
                "There aren't enough earlier recorded dates to compare with "
                "the recent period reliably."
            )

        recent_average = recent["sales"].mean()
        previous_average = previous["sales"].mean()
        recent_range = (
            f"{recent['date'].min().date()} to {recent['date'].max().date()}"
        )
        previous_range = (
            f"{previous['date'].min().date()} to {previous['date'].max().date()}"
        )
        if previous_average == 0:
            if recent_average == 0:
                comparison = "Both periods averaged R 0.00 per recorded date."
            else:
                comparison = (
                    "The earlier period averaged R 0.00, so a percentage "
                    f"change isn't meaningful; the recent average was "
                    f"R {recent_average:,.2f} per recorded date."
                )
        else:
            change_pct = (
                (recent_average - previous_average) / previous_average * 100
            )
            direction = "higher" if change_pct > 0 else "lower"
            if change_pct == 0:
                comparison = "The averages were unchanged."
            else:
                comparison = (
                    f"The recent average was {abs(change_pct):.1f}% "
                    f"{direction}."
                )
        return (
            f"**Historical trend:** average sales per recorded date were "
            f"R {previous_average:,.2f} from {previous_range}, compared "
            f"with R {recent_average:,.2f} from {recent_range}. "
            f"{comparison} This compares recorded dates, not every "
            "calendar day."
        )

    if any(word in question for word in ["weakest", "lowest", "worst"]):
        weakest = data.loc[data["sales"].idxmin()]
        return (
            f"**Historical fact:** the weakest recorded sales day was "
            f"{weakest['date'].date()}, with sales of "
            f"R {weakest['sales']:,.2f}."
        )

    if any(word in question for word in ["best", "strongest", "highest"]):
        best = data.loc[data["sales"].idxmax()]
        return (
            f"**Historical fact:** the best recorded sales day was "
            f"{best['date'].date()}, with sales of "
            f"R {best['sales']:,.2f}."
        )

    if "average" in question or "per day" in question or "daily" in question:
        return (
            f"**Historical fact:** average sales were "
            f"R {data['sales'].mean():,.2f} per recorded date, based on "
            f"{len(data):,} recorded dates. Missing calendar dates are not "
            "included in this average."
        )

    if any(word in question for word in ["total", "sum", "overall", "revenue"]):
        return (
            f"**Historical fact:** total sales in the cleaned data are "
            f"R {data['sales'].sum():,.2f}, across {len(data):,} recorded "
            "dates."
        )

    return (
        "I can't answer that reliably from the available sales data. Try "
        "asking about total sales, average sales per recorded date, the best "
        "or weakest recorded day, recent trends, or forecast results."
    )


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

data_fingerprint = hashlib.sha256(
    pd.util.hash_pandas_object(data, index=False).values.tobytes()
).hexdigest()

if (
    "sales_forecast" in st.session_state
    and st.session_state.get("sales_forecast_data_key") != data_fingerprint
):
    st.session_state.pop("sales_forecast", None)
    st.session_state.pop("sales_forecast_data_key", None)
    st.session_state.pop("forecast_days", None)

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

fig.update_layout(hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

with st.expander("View cleaned sales data"):
    st.dataframe(data, use_container_width=True)

st.divider()
st.subheader("Sales Action Planner")
st.caption(
    "Set a planning target based on your cleaned historical sales. "
    "This is not a forecast or a guarantee of future results."
)
improvement_pct = st.number_input(
    "Target sales improvement (%)",
    min_value=0.0,
    value=10.0,
    step=1.0,
)

try:
    sales_target = calculate_sales_target(data, improvement_pct)
except ValueError as error:
    st.error(f"Could not calculate the planning target: {error}")
else:
    target_current, target_goal, target_gap = st.columns(3)
    target_current.metric(
        "Historical average per recorded date",
        f"R {sales_target['historical_average']:,.2f}",
    )
    target_goal.metric(
        "Target average per recorded date",
        f"R {sales_target['target_average']:,.2f}",
    )
    target_gap.metric(
        "Additional revenue needed per recorded date",
        f"R {sales_target['additional_per_date']:,.2f}",
    )

    weekday_data = data.assign(day_name=data["date"].dt.day_name())
    weekday_average = weekday_data.groupby("day_name")["sales"].mean()
    weakest_weekday = weekday_average.idxmin()

    st.markdown(
        "**Planning target:** the target average is "
        f"{improvement_pct:g}% above the historical average per recorded "
        "date. It is not a Prophet forecast or a guarantee."
    )
    if sales_target["historical_average"] == 0:
        st.info(
            "A percentage increase on a zero historical average remains "
            "zero. Set an absolute revenue goal separately if you need a "
            "positive target."
        )
    st.markdown("**Three experiments to test**")
    st.markdown(
        f"1. **Try a limited offer on {weakest_weekday}, the lowest-average "
        f"recorded weekday.** Compare sales per recorded date on that "
        f"weekday with a comparable pre-test baseline. A target to aim for "
        f"is at least R {sales_target['target_average']:,.2f} per recorded "
        "date during the test."
    )
    st.markdown(
        "2. **Test a simple add-on or bundle prompt.** Compare average sales "
        "per recorded date during the test with a comparable baseline; "
        f"measure success by reaching at least R "
        f"{sales_target['target_average']:,.2f} per recorded date."
    )
    st.markdown(
        "3. **Test a repeat-visit reminder.** Compare average sales per "
        "recorded date during the test with a comparable baseline; "
        f"measure success by reaching at least R "
        f"{sales_target['target_average']:,.2f} per recorded date."
    )
    st.caption(
        "These experiments are hypotheses, not proven explanations or "
        "guaranteed results. The uploaded data does not show product, "
        "customer, or profit details. Track costs and profit separately "
        "where possible, and compare similar recorded dates."
    )

st.divider()
st.subheader("Ask Your Sales Analyst")
st.caption(
    "Ask about the cleaned data shown above. Historical answers use recorded "
    "sales; forecast answers are clearly labeled estimates. No external AI "
    "service is used."
)

with st.form("sales_analyst_form"):
    analyst_question = st.text_input(
        "What would you like to know?",
        placeholder="For example: What were my total sales?",
    )
    ask_analyst = st.form_submit_button("Ask")

if ask_analyst:
    current_forecast = None
    if (
        st.session_state.get("sales_forecast_data_key") == data_fingerprint
    ):
        current_forecast = st.session_state.get("sales_forecast")
    st.info(answer_sales_question(analyst_question, data, current_forecast))

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
        st.session_state["sales_forecast_data_key"] = data_fingerprint
        st.session_state["forecast_days"] = forecast_days

    except Exception as e:
        st.error(f"Forecast could not be generated: {e}")
        st.info(
            "Check that Prophet is listed in requirements.txt "
            "and that your sales data contains valid dates and numbers."
        )

if (
    "sales_forecast" in st.session_state
    and st.session_state.get("sales_forecast_data_key") == data_fingerprint
):
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