import hashlib
import io
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
    page_title="Sales Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --navy: #10233f;
        --navy-soft: #1b3556;
        --blue: #3878f6;
        --blue-soft: #eaf1ff;
        --ink: #172b45;
        --muted: #718096;
        --line: #e5eaf1;
        --canvas: #f5f7fa;
        --white: #ffffff;
    }

    [data-testid="stAppViewContainer"] {
        background: var(--canvas);
        color: var(--ink);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stSidebar"] {
        background: var(--navy);
        border-right: 1px solid #263d5a;
    }

    [data-testid="stSidebar"] * {
        color: #e7eef8;
    }

    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #aab9cc;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        border-radius: 9px;
        padding: 0.38rem 0.5rem;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: rgba(255, 255, 255, 0.08);
    }

    .block-container {
        max-width: 100%;
        padding: 1.4rem 2.2rem 3rem;
    }

    h1, h2, h3 {
        color: var(--navy);
        letter-spacing: -0.025em;
    }

    h1 {
        font-size: 1.65rem;
        font-weight: 720;
        margin: 0;
    }

    h2 {
        font-size: 1.35rem;
        font-weight: 680;
        margin: 0.4rem 0;
    }

    h3 {
        font-size: 1rem;
        font-weight: 650;
    }

    p, [data-testid="stMarkdownContainer"] {
        line-height: 1.55;
    }

    [data-testid="stMetric"] {
        min-height: 116px;
        background: var(--white);
        border: 1px solid var(--line);
        border-radius: 13px;
        padding: 1rem 1.1rem;
        box-shadow: 0 3px 12px rgba(16, 35, 63, 0.035);
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted);
        font-size: 0.82rem;
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        color: var(--navy);
        font-size: 1.45rem;
        font-weight: 720;
    }

    [data-testid="stPlotlyChart"] {
        overflow: hidden;
        background: var(--white);
        border: 1px solid var(--line);
        border-radius: 13px;
        padding: 0.35rem;
        box-shadow: 0 3px 12px rgba(16, 35, 63, 0.035);
    }

    [data-testid="stForm"],
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        border-color: var(--line);
        border-radius: 13px;
    }

    [data-testid="stFileUploader"] section {
        background: rgba(255, 255, 255, 0.06);
        border: 1px dashed #6e8199;
        border-radius: 10px;
    }

    [data-testid="stSidebar"] [data-testid="stFileUploader"] section {
        background: rgba(255, 255, 255, 0.06);
    }

    div[data-testid="stButton"] button[kind="primary"],
    [data-testid="stFormSubmitButton"] button {
        background: var(--blue);
        border: 1px solid var(--blue);
        border-radius: 8px;
        font-weight: 650;
    }

    [data-testid="stSidebar"] hr {
        border-color: #334965;
    }

    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
        color: var(--navy);
    }

    .workspace-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        padding: 0.25rem 0 1.25rem;
        border-bottom: 1px solid var(--line);
        margin-bottom: 1.4rem;
    }

    .workspace-eyebrow {
        color: var(--muted);
        font-size: 0.78rem;
        font-weight: 650;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        color: #176247;
        background: #e7f5ef;
        border: 1px solid #cce9dc;
        border-radius: 99px;
        padding: 0.45rem 0.75rem;
        font-size: 0.8rem;
        font-weight: 650;
        white-space: nowrap;
    }

    .panel-heading {
        color: var(--navy);
        font-size: 1rem;
        font-weight: 680;
        margin-bottom: 0.2rem;
    }

    .panel-subtitle {
        color: var(--muted);
        font-size: 0.84rem;
        margin-bottom: 0.8rem;
    }

    .insight-card {
        background: var(--white);
        border: 1px solid var(--line);
        border-radius: 13px;
        padding: 1.1rem;
        box-shadow: 0 3px 12px rgba(16, 35, 63, 0.035);
        margin-bottom: 0.8rem;
    }

    .insight-label {
        color: var(--muted);
        font-size: 0.77rem;
        font-weight: 620;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .insight-value {
        color: var(--navy);
        font-size: 1.08rem;
        font-weight: 680;
        margin-top: 0.3rem;
    }

    .callout {
        background: var(--blue-soft);
        border-left: 3px solid var(--blue);
        border-radius: 0 9px 9px 0;
        padding: 0.85rem 1rem;
        color: var(--navy);
        font-size: 0.9rem;
    }

    .empty-state {
        background: var(--white);
        border: 1px dashed #cbd5e1;
        border-radius: 15px;
        padding: 2rem;
        color: var(--muted);
    }

    @media (max-width: 760px) {
        .block-container {
            padding: 1rem 1rem 2rem;
        }

        .workspace-header {
            align-items: flex-start;
            flex-direction: column;
            padding-bottom: 1rem;
        }

        [data-testid="stMetric"] {
            min-height: 96px;
            padding: 0.75rem;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.15rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

PAGES = ["Overview", "Sales Analytics", "Forecasting", "Action Planner", "Sales Analyst"]
PAGE_MARKS = {
    "Overview": "◉",
    "Sales Analytics": "▥",
    "Forecasting": "↗",
    "Action Planner": "◎",
    "Sales Analyst": "✳",
}

with st.sidebar:
    st.markdown(
        "<div style='font-size:1.04rem;font-weight:750;letter-spacing:-.02em'>"
        "SI <span style='color:#9dbfff'>/</span> Sales Intelligence</div>",
        unsafe_allow_html=True,
    )
    st.caption("SALES PERFORMANCE WORKSPACE")
    st.markdown("---")
    selected_page = st.radio(
        "Workspace",
        PAGES,
        format_func=lambda page: f"{PAGE_MARKS[page]}   {page}",
        label_visibility="collapsed",
        key="sales_navigation",
    )
    st.markdown("---")
    st.markdown("**Dataset**")
    st.caption("Upload a CSV with a date field and sales amounts.")
    uploaded_file = st.file_uploader(
        "Upload or replace CSV",
        type=["csv"],
        key="sales_csv_uploader",
        help="Your uploaded dataset remains available as you navigate.",
    )
    if uploaded_file is not None:
        incoming_bytes = uploaded_file.getvalue()
        incoming_key = hashlib.sha256(incoming_bytes).hexdigest()
        if (
            st.session_state.get("sales_csv_fingerprint") != incoming_key
            or st.session_state.get("sales_csv_filename") != uploaded_file.name
        ):
            st.session_state["sales_csv_bytes"] = incoming_bytes
            st.session_state["sales_csv_filename"] = uploaded_file.name
            st.session_state["sales_csv_fingerprint"] = incoming_key
    if st.session_state.get("sales_csv_filename"):
        st.caption(f"Loaded: {st.session_state['sales_csv_filename']}")
    else:
        st.caption("No dataset loaded")

st.markdown(
    "<div class='workspace-header'>"
    "<div><div class='workspace-eyebrow'>Sales intelligence</div>"
    f"<h1>{selected_page}</h1></div>"
    + (
        "<div class='status-pill'>● Dataset ready</div>"
        if st.session_state.get("sales_csv_bytes") is not None
        else "<div class='status-pill' style='color:#8a5b16;background:#fff6e5;"
        "border-color:#f0dfb8'>● Upload required</div>"
    )
    + "</div>",
    unsafe_allow_html=True,
)

if st.session_state.get("sales_csv_bytes") is None:
    st.markdown(
        "<div class='empty-state'><strong>No sales dataset loaded</strong><br>"
        "Upload a CSV from the sidebar to unlock the dashboard. The file should "
        "contain a date column and a sales amount column; likely columns are "
        "detected automatically.</div>",
        unsafe_allow_html=True,
    )
    st.stop()

try:
    df = pd.read_csv(io.BytesIO(st.session_state["sales_csv_bytes"]))
except Exception as error:
    st.error(f"Could not read the CSV: {error}")
    st.stop()

if df.empty or len(df.columns) < 2:
    st.error("Your CSV is empty or does not contain enough columns.")
    st.stop()

columns = list(df.columns)
date_candidates = [
    column for column in columns
    if any(word in column.lower() for word in ["date", "day", "time"])
]
date_col = date_candidates[0] if date_candidates else None

if date_col is None:
    for column in columns:
        parsed_dates = pd.to_datetime(df[column], errors="coerce", dayfirst=True)
        if parsed_dates.notna().mean() >= 0.7:
            date_col = column
            break

sales_candidates = [
    column for column in columns
    if any(word in column.lower() for word in [
        "sales", "revenue", "turnover", "total_sales", "sales_zar", "amount"
    ])
]
sales_col = sales_candidates[0] if sales_candidates else None

if sales_col is None:
    numeric_candidates = [
        column for column in columns
        if column != date_col and pd.to_numeric(
            df[column].astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
            errors="coerce",
        ).notna().mean() >= 0.7
    ]
    if numeric_candidates:
        sales_col = numeric_candidates[0]

if date_col is None or sales_col is None or date_col == sales_col:
    st.error(
        "I couldn't reliably identify your date and sales columns. "
        "Check that your CSV contains valid dates and sales amounts."
    )
    st.caption(f"Columns found: {', '.join(map(str, columns))}")
    st.stop()

st.caption(f"Detected columns · Date: {date_col} · Sales: {sales_col}")

data = pd.DataFrame({
    "date": pd.to_datetime(df[date_col], errors="coerce", dayfirst=True),
    "sales": pd.to_numeric(
        df[sales_col].astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
        errors="coerce",
    ),
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
        "No valid records found. Check the detected columns and make sure "
        "the dates and sales amounts are valid."
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


def make_sales_chart(chart_data, title, x_column="date", y_column="sales"):
    chart = px.line(
        chart_data,
        x=x_column,
        y=y_column,
        title=title,
        labels={x_column: "Date", y_column: "Sales (R)"},
        markers=True,
        color_discrete_sequence=["#3878f6"],
    )
    chart.update_layout(
        template="plotly_white",
        hovermode="x unified",
        font=dict(family="Arial, sans-serif", color="#172b45"),
        margin=dict(l=12, r=18, t=55, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
        height=365,
    )
    chart.update_traces(
        hovertemplate="%{x|%d %b %Y}<br>Sales: R %{y:,.2f}<extra></extra>"
    )
    chart.update_xaxes(title_text="Date", tickformat="%d %b %Y", showgrid=False)
    chart.update_yaxes(title_text="Sales (R)", tickprefix="R ", gridcolor="#e9eef4")
    return chart


total_sales = data["sales"].sum()
average_sales = data["sales"].mean()
best_day = data.loc[data["sales"].idxmax()]
weekday_data = data.assign(day_name=data["date"].dt.day_name())
weekday_average = weekday_data.groupby("day_name")["sales"].mean()
weekday_order = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]
weekday_chart_data = (
    weekday_average.reindex(weekday_order).dropna().rename("Average sales").reset_index()
)

if selected_page == "Overview":
    st.caption(
        f"{st.session_state['sales_csv_filename']} · "
        f"{len(data):,} recorded dates · "
        f"{data['date'].min().date()} – {data['date'].max().date()} · "
        "Use the sidebar to upload or refresh your dataset."
    )
    metric_columns = st.columns(4)
    metric_columns[0].metric("Total sales", f"R {total_sales:,.2f}")
    metric_columns[1].metric(
        "Average per recorded date", f"R {average_sales:,.2f}"
    )
    metric_columns[2].metric(
        f"Best sales day · {best_day['date'].date()}",
        f"R {best_day['sales']:,.2f}",
        help=str(best_day["date"].date()),
    )
    metric_columns[3].metric("Recorded dates", f"{len(data):,}")

    st.markdown("### Performance at a glance")
    chart_column, insight_column = st.columns([1.85, 1], gap="large")
    with chart_column:
        st.plotly_chart(
            make_sales_chart(data, "Historical sales"),
            width="stretch",
            config={"displayModeBar": False, "responsive": True},
        )
    with insight_column:
        st.markdown("<div class='panel-heading'>Weekday performance</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='panel-subtitle'>Average sales across recorded dates</div>",
            unsafe_allow_html=True,
        )
        if not weekday_average.empty:
            strongest_day = weekday_average.idxmax()
            weakest_day = weekday_average.idxmin()
            st.markdown(
                f"<div class='insight-card'><div class='insight-label'>Strongest weekday</div>"
                f"<div class='insight-value'>{strongest_day} · R {weekday_average[strongest_day]:,.2f}</div></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='insight-card'><div class='insight-label'>Weakest weekday</div>"
                f"<div class='insight-value'>{weakest_day} · R {weekday_average[weakest_day]:,.2f}</div></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='callout'><strong>Experiment to consider</strong><br>"
                f"Test one small, measurable change on {weakest_day}. Compare its sales "
                "with a similar baseline before drawing conclusions.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("Weekday comparisons are not available for this dataset.")

elif selected_page == "Sales Analytics":
    st.caption("Explore recorded daily sales patterns and period comparisons.")
    st.plotly_chart(
        make_sales_chart(data, "Daily sales trend"),
        width="stretch",
        config={"displayModeBar": False, "responsive": True},
    )
    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown("### Weekday performance")
        if not weekday_chart_data.empty:
            if not weekday_average.empty:
                st.caption(
                    f"Strongest: {weekday_average.idxmax()} · "
                    f"R {weekday_average.max():,.2f}  |  "
                    f"Weakest: {weekday_average.idxmin()} · "
                    f"R {weekday_average.min():,.2f}"
                )
            weekday_fig = px.bar(
                weekday_chart_data,
                x="day_name",
                y="Average sales",
                labels={"day_name": "Weekday", "Average sales": "Average sales (R)"},
                color_discrete_sequence=["#3878f6"],
            )
            weekday_fig.update_layout(
                template="plotly_white", height=315,
                margin=dict(l=10, r=10, t=15, b=10),
                font=dict(family="Arial, sans-serif", color="#172b45"),
                yaxis=dict(tickprefix="R ", gridcolor="#e9eef4"),
            )
            weekday_fig.update_traces(
                hovertemplate="%{x}<br>Average: R %{y:,.2f}<extra></extra>"
            )
            st.plotly_chart(
                weekday_fig,
                width="stretch",
                config={"displayModeBar": False, "responsive": True},
            )
            st.caption(
                "A weekday average uses only dates present in the uploaded data; "
                "missing dates are not treated as zero-sales days."
            )
    with right:
        st.markdown("### Sales growth comparison")
        if len(data) >= 4:
            split_point = len(data) // 2
            earlier_period = data.iloc[:split_point]
            later_period = data.iloc[split_point:]
            earlier_total = earlier_period["sales"].sum()
            later_total = later_period["sales"].sum()
            earlier_avg = earlier_period["sales"].mean()
            later_avg = later_period["sales"].mean()
            growth_columns = st.columns(3)
            growth_columns[0].metric("Earlier total", f"R {earlier_total:,.2f}")
            growth_columns[1].metric("Later total", f"R {later_total:,.2f}")
            if earlier_avg > 0:
                growth = (later_avg - earlier_avg) / earlier_avg * 100
                growth_columns[2].metric("Average change", f"{growth:+.1f}%")
                if growth > 5:
                    st.success(
                        "Average sales per recorded date were higher in the later period. "
                        "This comparison does not identify what caused the change."
                    )
                elif growth < -5:
                    st.warning(
                        "Average sales per recorded date were lower in the later period. "
                        "Review the underlying business context before acting."
                    )
                else:
                    st.info("Average sales per recorded date were broadly stable.")
            else:
                st.info(
                    "A percentage comparison is unavailable because earlier-period "
                    "average sales are zero."
                )
        else:
            st.info("Upload at least four recorded dates to compare sales periods.")
    with st.expander("Preview cleaned daily data"):
        st.dataframe(data, width="stretch", hide_index=True)

elif selected_page == "Forecasting":
    st.caption(
        "Build a Prophet estimate from recorded sales history. Forecasts are "
        "estimates, not guarantees."
    )
    control_column, note_column = st.columns([1, 2])
    with control_column:
        forecast_days = st.selectbox(
            "Forecast horizon", [7, 30, 90], index=1,
            format_func=lambda days: f"{days} days",
            key="forecast_horizon",
        )
        generate_forecast = st.button(
            "Generate forecast", type="primary", disabled=len(data) < 2,
            width="stretch",
        )
    with note_column:
        st.info(
            "The model needs at least two recorded dates. Longer and more "
            "consistent history can help provide context, but does not assure accuracy."
        )
    if len(data) < 2:
        st.warning("At least two different dates are required to forecast.")

    if generate_forecast:
        try:
            from prophet import Prophet

            forecast_data = data.rename(columns={"date": "ds", "sales": "y"})
            with st.spinner("Fitting the forecasting model to your sales history…"):
                model = Prophet(
                    yearly_seasonality="auto",
                    weekly_seasonality="auto",
                    daily_seasonality=False,
                )
                model.fit(forecast_data)
                future = model.make_future_dataframe(periods=forecast_days, freq="D")
                prediction = model.predict(future)
            future_forecast = prediction[
                prediction["ds"] > forecast_data["ds"].max()
            ].copy()
            future_forecast["yhat"] = future_forecast["yhat"].clip(lower=0)
            future_forecast["yhat_lower"] = future_forecast["yhat_lower"].clip(lower=0)
            future_forecast["yhat_upper"] = future_forecast["yhat_upper"].clip(lower=0)
            st.session_state["sales_forecast"] = future_forecast[
                ["ds", "yhat", "yhat_lower", "yhat_upper"]
            ].copy()
            st.session_state["sales_forecast_data_key"] = data_fingerprint
            st.session_state["forecast_days"] = forecast_days
        except Exception as error:
            st.error(f"Forecast could not be generated: {error}")
            st.info(
                "Check that Prophet is installed and the uploaded dates and sales "
                "values are valid. Your historical analysis is still available."
            )

    if (
        "sales_forecast" in st.session_state
        and st.session_state.get("sales_forecast_data_key") == data_fingerprint
    ):
        result = st.session_state["sales_forecast"]
        forecast_days = st.session_state["forecast_days"]
        st.markdown(f"### {forecast_days}-day forecast")
        forecast_kpis = st.columns(3)
        forecast_kpis[0].metric("Forecast total", f"R {result['yhat'].sum():,.2f}")
        forecast_kpis[1].metric("Average forecast per day", f"R {result['yhat'].mean():,.2f}")
        forecast_kpis[2].metric(
            "Forecast range total",
            f"R {result['yhat_lower'].sum():,.2f} – R {result['yhat_upper'].sum():,.2f}",
            help="Sum of the model's lower and upper daily uncertainty estimates.",
        )

        history_plot = data.rename(columns={"date": "Date", "sales": "Sales"})
        forecast_plot = result.rename(columns={
            "ds": "Date", "yhat": "Sales",
            "yhat_lower": "Lower estimate", "yhat_upper": "Upper estimate",
        })
        chart = px.line(
            history_plot, x="Date", y="Sales",
            title="Recorded sales and forecast estimate",
            labels={"Date": "Date", "Sales": "Sales (R)"},
            color_discrete_sequence=["#10233f"],
        )
        chart.add_scatter(
            x=forecast_plot["Date"], y=forecast_plot["Sales"],
            mode="lines", name="Forecast",
            line=dict(color="#3878f6", width=3),
            hovertemplate="%{x|%d %b %Y}<br>Forecast: R %{y:,.2f}<extra></extra>",
        )
        chart.add_scatter(
            x=forecast_plot["Date"], y=forecast_plot["Upper estimate"],
            mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
        )
        chart.add_scatter(
            x=forecast_plot["Date"], y=forecast_plot["Lower estimate"],
            mode="lines", line=dict(width=0), fill="tonexty",
            fillcolor="rgba(56, 120, 246, 0.15)", name="Uncertainty range",
            hoverinfo="skip",
        )
        chart.update_layout(
            template="plotly_white", hovermode="x unified", height=420,
            font=dict(family="Arial, sans-serif", color="#172b45"),
            margin=dict(l=12, r=18, t=55, b=12),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
        )
        chart.update_xaxes(title_text="Date", tickformat="%d %b %Y", showgrid=False)
        chart.update_yaxes(title_text="Sales (R)", tickprefix="R ", gridcolor="#e9eef4")
        st.plotly_chart(
            chart, width="stretch",
            config={"displayModeBar": False, "responsive": True},
        )
        st.caption(
            "The shaded band shows the model's uncertainty interval. It is not a "
            "guaranteed minimum or maximum."
        )
        download_data = result.rename(columns={
            "ds": "date", "yhat": "forecast_sales",
            "yhat_lower": "lower_estimate", "yhat_upper": "upper_estimate",
        })
        st.dataframe(download_data, width="stretch", hide_index=True)
        st.download_button(
            "Download forecast CSV",
            data=download_data.to_csv(index=False).encode("utf-8"),
            file_name="sales_forecast.csv",
            mime="text/csv",
        )
    else:
        st.markdown(
            "<div class='empty-state'><strong>No forecast generated for this dataset</strong><br>"
            "Choose a horizon above and generate a forecast. The results will appear here.</div>",
            unsafe_allow_html=True,
        )

elif selected_page == "Action Planner":
    st.caption(
        "Translate a chosen improvement goal into a measurable daily sales target. "
        "This is a planning exercise, not a forecast or guarantee."
    )
    improvement_pct = st.number_input(
        "Target sales improvement (%)",
        min_value=0.0,
        value=10.0,
        step=1.0,
        key="sales_improvement_pct",
    )
    try:
        sales_target = calculate_sales_target(data, improvement_pct)
    except ValueError as error:
        st.error(f"Could not calculate the planning target: {error}")
    else:
        target_columns = st.columns(3)
        target_columns[0].metric(
            "Historical average per recorded date",
            f"R {sales_target['historical_average']:,.2f}",
        )
        target_columns[1].metric(
            "Target average per recorded date",
            f"R {sales_target['target_average']:,.2f}",
        )
        target_columns[2].metric(
            "Additional revenue needed per date",
            f"R {sales_target['additional_per_date']:,.2f}",
        )
        st.caption(
            f"Planning target: {improvement_pct:.0f}% above the historical average. "
            "It is not a Prophet forecast or a promise of future sales."
        )
        if sales_target["historical_average"] == 0:
            st.info(
                "A percentage increase on a zero historical average remains zero. "
                "Choose a separate absolute revenue goal if you need a positive target."
            )

        st.markdown("### Improvement scenarios")
        scenario_columns = st.columns(3)
        for column, scenario in zip(scenario_columns, [5, 10, 15]):
            scenario_target = sales_target["historical_average"] * (1 + scenario / 100)
            column.metric(f"+{scenario}% scenario", f"R {scenario_target:,.2f}")
            column.caption("Target average per recorded date")

        weakest_weekday = weekday_average.idxmin()
        st.markdown("### Experiments to test")
        experiments = st.columns(3)
        experiments[0].markdown(
            f"**01 · Test a limited offer on {weakest_weekday}.** Compare sales "
            "per recorded date for that weekday with a comparable pre-test baseline. "
            f"Aim for at least R {sales_target['target_average']:,.2f} per recorded date."
        )
        experiments[1].markdown(
            "**02 · Test a simple add-on or bundle prompt.** Compare average sales "
            "per recorded date during the test against a comparable baseline; measure "
            f"whether it reaches R {sales_target['target_average']:,.2f}."
        )
        experiments[2].markdown(
            "**03 · Test a repeat-visit reminder.** Compare average sales per recorded "
            "date during the test against a comparable baseline; measure whether it "
            f"reaches R {sales_target['target_average']:,.2f}."
        )
        st.info(
            "These experiments are hypotheses, not proven explanations or guaranteed "
            "results. This dataset does not identify products, customers, or profit. "
            "Track costs and profit separately where possible."
        )

elif selected_page == "Sales Analyst":
    st.caption(
        "Ask a question about this dataset. Answers are generated locally from "
        "recorded sales and any forecast already generated; no external AI service is used."
    )
    st.markdown("### Sales Intelligence Assistant")
    st.markdown(
        "Understand your performance, discover trends, and decide "
        "what to do next using your recorded sales data."
    )

    st.markdown("#### What would you like to understand?")

    example_questions = [
        ("How is my business performing?", "performance"),
        ("When are my sales weakest?", "weakest"),
        ("Are my sales growing or declining?", "trend"),
        ("Which days perform best?", "weekday"),
        ("What is my forecast telling me?", "forecast"),
        ("How can I improve sales?", "improve"),
    ]

    if "analyst_question_input" not in st.session_state:
        st.session_state["analyst_question_input"] = ""

    for row_start in range(0, len(example_questions), 2):
        question_columns = st.columns(2)

        for offset, (question, question_id) in enumerate(
            example_questions[row_start:row_start + 2]
        ):
            if question_columns[offset].button(
                question,
                key=f"analyst_example_{question_id}",
                use_container_width=True,
            ):
                st.session_state["analyst_question_input"] = question

    st.markdown("#### Ask your own question")

    example_columns = st.columns(3)
    example_columns[0].markdown("- What were my total sales?\n- Which day was weakest?")
    example_columns[1].markdown("- What is my recent trend?\n- Which weekday is strongest?")
    example_columns[2].markdown("- What does my forecast show?\n- How can I improve sales?")
    st.markdown("### Ask about your sales")
    with st.form("sales_analyst_form"):
        analyst_question = st.text_input(
            "Your question",
            placeholder="For example: What were my total sales?",
            label_visibility="collapsed",
        )
        ask_analyst = st.form_submit_button("Ask Sales Analyst", type="primary")
    if ask_analyst:
        current_forecast = None
        if st.session_state.get("sales_forecast_data_key") == data_fingerprint:
            current_forecast = st.session_state.get("sales_forecast")
        response = answer_sales_question(analyst_question, data, current_forecast)
        with st.container(border=True):
            st.markdown("**Answer**")
            st.markdown(response)
