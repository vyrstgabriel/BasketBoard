"""Basketboard: defensible customer-retention analytics for Online Retail II.

Run from the project root with: streamlit run dashboard/app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


RESULTS = Path(__file__).parent.parent / "results"

st.set_page_config(
    page_title="Basketboard | Retention Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
[data-testid="metric-container"] {
    background: #f8f9fb; border: 1px solid #e8eaed;
    border-radius: 10px; padding: 1rem 1.2rem;
}
[data-testid="metric-container"] label {
    font-size: 0.78rem; color: #6b7280;
    text-transform: uppercase; letter-spacing: 0.04em;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.7rem; font-weight: 700; color: #111827;
}
[data-testid="stSidebar"] { background: #0f172a; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
hr { border-color: #e5e7eb; margin: 1.5rem 0; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / f"{name}.csv")


def weighted_rate(df: pd.DataFrame, numerator: str, denominator: str) -> float:
    return 100 * df[numerator].sum() / df[denominator].sum()


LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="white",
    font=dict(family="Inter, system-ui, sans-serif", color="#374151", size=12),
    margin=dict(l=40, r=20, t=30, b=40),
)
TIER_ORDER = ["Champions", "Loyal", "New", "At Risk", "Lost"]
TIER_COLORS = {
    "Champions": "#6366f1",
    "Loyal": "#22c55e",
    "New": "#f59e0b",
    "At Risk": "#f97316",
    "Lost": "#ef4444",
}
ACCENT = "#6366f1"


def styled(fig, yformat=None, yrange=None):
    fig.update_layout(**LAYOUT)
    fig.update_xaxes(showgrid=False, linecolor="#e5e7eb", tickfont_size=11)
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#f3f4f6",
        linecolor="#e5e7eb",
        tickfont_size=11,
        tickformat=yformat,
        range=yrange,
    )
    return fig


st.sidebar.markdown("## 📊 Basketboard")
st.sidebar.markdown("E-commerce customer retention analytics")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Cohort Retention", "Purchasing Activity", "Behavioral Analysis"],
    label_visibility="collapsed",
)
st.sidebar.markdown("---")
st.sidebar.caption("Online Retail II · Dec 2009–Dec 2011")


if page == "Overview":
    rfm = load("01_churn_by_rfm_segment")
    anonymous = load("06_anonymous_transactions")
    sensitivity = load("08_churn_window_sensitivity")

    observation_end = pd.to_datetime(rfm["observation_end"].iloc[0])
    outcome_end = pd.to_datetime(rfm["outcome_end"].iloc[0])
    total_customers = int(rfm["total_customers"].sum())
    overall_churn = weighted_rate(rfm, "churned_customers", "total_customers")
    total_net_revenue = rfm["total_net_revenue_at_cutoff"].sum()
    identified_revenue_share = anonymous.loc[
        anonymous["customer_type"] == "Identified", "pct_revenue"
    ].iloc[0]

    st.title("Customer Retention Overview")
    st.caption(
        f"Customer features through {observation_end:%b %d, %Y}; "
        f"purchase outcomes observed through {outcome_end:%b %d, %Y}."
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Eligible customers", f"{total_customers:,}")
    k2.metric("Future 90-day churn", f"{overall_churn:.1f}%")
    k3.metric("Eligible-customer net revenue", f"£{total_net_revenue:,.0f}")
    k4.metric("Identified gross revenue share", f"{identified_revenue_share:.1f}%")

    sensitivity_text = " · ".join(
        f"{int(row.outcome_days)} days: {row.churn_rate_pct:.1f}%"
        for row in sensitivity.itertuples()
    )
    st.caption(
        f"No-purchase window sensitivity — {sensitivity_text}. "
        "The cutoffs differ, so seasonality also contributes to the change."
    )

    st.markdown("---")
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Customers by RFM Tier")
        fig = px.bar(
            rfm,
            x="rfm_tier",
            y="total_customers",
            color="rfm_tier",
            text="total_customers",
            color_discrete_map=TIER_COLORS,
            category_orders={"rfm_tier": TIER_ORDER},
        )
        fig.update_traces(textposition="outside", marker_line_width=0)
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Customers")
        st.plotly_chart(
            styled(fig, yrange=[0, rfm["total_customers"].max() * 1.2])
        )

    with col_r:
        st.subheader("Future Churn by Pre-Cutoff RFM Tier")
        fig = px.bar(
            rfm,
            x="rfm_tier",
            y="churn_rate_pct",
            color="rfm_tier",
            text="churn_rate_pct",
            color_discrete_map=TIER_COLORS,
            category_orders={"rfm_tier": TIER_ORDER},
        )
        fig.update_traces(
            texttemplate="%{text:.1f}%", textposition="outside", marker_line_width=0
        )
        fig.add_hline(
            y=overall_churn,
            line_dash="dash",
            line_color="#94a3b8",
            annotation_text=f"Overall {overall_churn:.1f}%",
            annotation_position="top right",
        )
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Churn (%)")
        st.plotly_chart(styled(fig, yrange=[0, 100]))

    st.markdown("---")
    st.subheader("Customer-ID Coverage")
    anonymous_row = anonymous.set_index("customer_type").loc["Anonymous"]
    st.caption(
        f"Anonymous sales represent {anonymous_row['pct_line_items']:.1f}% of line items, "
        f"{anonymous_row['pct_orders']:.1f}% of orders, and "
        f"{anonymous_row['pct_revenue']:.1f}% of gross revenue. "
        "Customer-level retention cannot be measured for those orders."
    )
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(
            anonymous,
            values="order_count",
            names="customer_type",
            color="customer_type",
            color_discrete_map={"Identified": ACCENT, "Anonymous": "#e5e7eb"},
            hole=0.55,
        )
        fig.update_traces(textinfo="label+percent", textfont_size=12)
        fig.update_layout(
            showlegend=False,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="white",
        )
        st.plotly_chart(fig)
        st.caption("Share of invoice-level orders")
    with col2:
        fig = px.pie(
            anonymous,
            values="gross_revenue",
            names="customer_type",
            color="customer_type",
            color_discrete_map={"Identified": ACCENT, "Anonymous": "#e5e7eb"},
            hole=0.55,
        )
        fig.update_traces(textinfo="label+percent", textfont_size=12)
        fig.update_layout(
            showlegend=False,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="white",
        )
        st.plotly_chart(fig)
        st.caption("Share of gross sales revenue")

    st.markdown("---")
    st.subheader("RFM Tier Detail")
    st.dataframe(
        rfm[
            [
                "rfm_tier",
                "total_customers",
                "churned_customers",
                "churn_rate_pct",
                "avg_net_revenue_at_cutoff",
                "avg_orders_at_cutoff",
                "risk_level",
            ]
        ].rename(
            columns={
                "rfm_tier": "Tier",
                "total_customers": "Customers",
                "churned_customers": "Churned in Outcome Window",
                "churn_rate_pct": "Future Churn (%)",
                "avg_net_revenue_at_cutoff": "Avg Net Revenue (£)",
                "avg_orders_at_cutoff": "Avg Orders",
                "risk_level": "Risk",
            }
        ),
        width="stretch",
        hide_index=True,
    )


elif page == "Cohort Retention":
    st.title("Calendar-Month Cohort Retention")
    st.caption(
        "Acquisition cohorts begin in January 2010. Only complete calendar-month "
        "cells through November 2011 are shown; future cells remain blank."
    )

    matrix = load("02_cohort_retention_matrix")
    min_size = st.slider("Minimum cohort size", 5, 100, 20, step=5)
    eligible_cohorts = matrix.groupby("cohort_month")["cohort_size"].first()
    eligible_cohorts = eligible_cohorts[eligible_cohorts >= min_size].index
    filtered = matrix[matrix["cohort_month"].isin(eligible_cohorts)]

    if filtered.empty:
        st.warning("No cohorts meet the minimum size filter.")
    else:
        pivot = filtered.pivot_table(
            index="cohort_month",
            columns="months_since_first",
            values="retention_pct",
            aggfunc="first",
        ).sort_index()
        fig = px.imshow(
            pivot.values,
            x=[f"M+{int(column)}" for column in pivot.columns],
            y=list(pivot.index),
            color_continuous_scale="Blues",
            zmin=0,
            zmax=100,
            text_auto=".0f",
            aspect="auto",
        )
        fig.update_coloraxes(colorbar_title="Retention %")
        fig.update_traces(textfont_size=9)
        fig.update_layout(
            xaxis_title="Calendar months since first observed purchase",
            yaxis_title="Acquisition cohort",
            margin=dict(l=80, r=20, t=20, b=40),
            paper_bgcolor="white",
            font=dict(family="Inter, system-ui, sans-serif", size=11),
            height=max(400, len(pivot) * 24),
        )
        st.plotly_chart(fig)
        st.caption(
            f"Showing {len(pivot)} cohorts with at least {min_size} customers. "
            "M+0 is the acquisition calendar month."
        )


elif page == "Purchasing Activity":
    st.title("Daily & Weekly Purchasing Activity")
    st.caption("Gross positive sales; refunds are reported separately from sales.")

    trend = load("03_dau_wau_trend")
    trend["period"] = pd.to_datetime(trend["period"])
    daily = trend[trend["granularity"] == "day"].copy()
    weekly = trend[trend["granularity"] == "week"].copy()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Peak daily customers", f"{daily['active_customers'].max():,.0f}")
    k2.metric("Peak weekly customers", f"{weekly['active_customers'].max():,.0f}")
    k3.metric("Total gross revenue", f"£{daily['gross_revenue'].sum():,.0f}")
    k4.metric("Avg orders / calendar day", f"{daily['orders_placed'].mean():.1f}")

    st.markdown("---")
    granularity = st.radio(
        "View",
        ["Daily", "Weekly"],
        horizontal=True,
        label_visibility="collapsed",
    )
    selected = daily if granularity == "Daily" else weekly

    tab1, tab2, tab3 = st.tabs(["Active Customers", "Orders", "Gross Revenue"])
    with tab1:
        fig = go.Figure(
            go.Scatter(
                x=selected["period"],
                y=selected["active_customers"],
                mode="lines",
                line=dict(color=ACCENT, width=1.5),
                fill="tozeroy",
                fillcolor="rgba(99,102,241,0.08)",
                hovertemplate="%{x|%b %d %Y}: %{y:,} customers<extra></extra>",
            )
        )
        fig.update_layout(xaxis_title="", yaxis_title="Purchasing customers")
        st.plotly_chart(styled(fig))
    with tab2:
        fig = go.Figure(
            go.Scatter(
                x=selected["period"],
                y=selected["orders_placed"],
                mode="lines",
                line=dict(color="#a78bfa", width=1.5),
                fill="tozeroy",
                fillcolor="rgba(167,139,250,0.08)",
                hovertemplate="%{x|%b %d %Y}: %{y:,} orders<extra></extra>",
            )
        )
        fig.update_layout(xaxis_title="", yaxis_title="Invoice-level orders")
        st.plotly_chart(styled(fig))
    with tab3:
        fig = go.Figure(
            go.Scatter(
                x=selected["period"],
                y=selected["gross_revenue"],
                mode="lines",
                line=dict(color="#22c55e", width=1.5),
                fill="tozeroy",
                fillcolor="rgba(34,197,94,0.08)",
                hovertemplate="%{x|%b %d %Y}: £%{y:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(xaxis_title="", yaxis_title="Gross revenue (£)")
        st.plotly_chart(styled(fig))


elif page == "Behavioral Analysis":
    st.title("Behavioral Analysis")
    st.caption("Every predictor is measured before its stated outcome window.")

    tab1, tab2, tab3 = st.tabs(
        ["Early Repeat Timing", "Order Milestones", "Returns by Frequency"]
    )

    with tab1:
        t2p = load("04_time_to_second_purchase")
        no_second = t2p[t2p["sort_order"] == 4].iloc[0]
        early = t2p[t2p["sort_order"] < 4]
        early_rate = weighted_rate(
            early, "later_repeat_customers", "eligible_customers"
        )
        lift = early_rate / no_second["later_repeat_rate_pct"]

        st.subheader("Early Repeat Timing vs Later-Quarter Purchasing")
        st.markdown(
            f"Customers with a second order in their first 90 days purchased again "
            f"during days 91–180 at **{early_rate:.1f}%**, versus "
            f"**{no_second['later_repeat_rate_pct']:.1f}%** without an early second "
            f"order ({lift:.1f}× association)."
        )
        fig = px.bar(
            t2p,
            x="second_purchase_timing",
            y="later_repeat_rate_pct",
            text="later_repeat_rate_pct",
            color="later_repeat_rate_pct",
            color_continuous_scale=["#dbeafe", "#1d4ed8"],
        )
        fig.update_traces(
            texttemplate="%{text:.1f}%", textposition="outside", marker_line_width=0
        )
        fig.update_coloraxes(showscale=False)
        fig.update_layout(
            xaxis_title="Second purchase timing during days 0–90",
            yaxis_title="Purchase rate during days 91–180 (%)",
        )
        st.plotly_chart(styled(fig, yrange=[0, 70]))
        st.caption(
            "Only customers with a complete 180-day observation horizon are included. "
            "This is predictive association, not a causal effect."
        )
        st.dataframe(
            t2p[
                [
                    "second_purchase_timing",
                    "eligible_customers",
                    "later_repeat_customers",
                    "later_repeat_rate_pct",
                ]
            ].rename(
                columns={
                    "second_purchase_timing": "Second Purchase Timing",
                    "eligible_customers": "Eligible Customers",
                    "later_repeat_customers": "Purchased in Days 91–180",
                    "later_repeat_rate_pct": "Later Purchase Rate (%)",
                }
            ),
            width="stretch",
            hide_index=True,
        )

    with tab2:
        milestones = load("05_order_milestone_repeat")
        first_rate = milestones.loc[
            milestones["order_milestone"] == 1, "repeat_rate_pct"
        ].iloc[0]
        fifth_rate = milestones.loc[
            milestones["order_milestone"] == 5, "repeat_rate_pct"
        ].iloc[0]

        st.subheader("90-Day Repeat Rate after Each Order Milestone")
        st.markdown(
            f"The next-90-day repeat rate rises from **{first_rate:.1f}%** after the "
            f"first observed order to **{fifth_rate:.1f}%** after order five. "
            "Higher milestones select for customers who were already more engaged."
        )
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=milestones["order_milestone"],
                y=milestones["repeat_rate_pct"],
                marker_color=ACCENT,
                text=milestones["repeat_rate_pct"],
                texttemplate="%{text:.1f}%",
                textposition="outside",
                name="90-day repeat rate",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=milestones["order_milestone"],
                y=milestones["repeat_rate_pct"],
                mode="lines+markers",
                line=dict(color="#f59e0b", width=2, dash="dot"),
                marker=dict(size=6, color="#f59e0b"),
                name="Trend",
            )
        )
        fig.update_layout(
            xaxis_title="Observed order milestone",
            yaxis_title="Next-90-day repeat rate (%)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(styled(fig, yrange=[0, 100]))
        st.caption(
            "Each milestone is included only when a complete 90-day follow-up exists. "
            "The chart describes progression; it does not identify a causal AHA threshold."
        )

    with tab3:
        returns = load("07_returns_analysis")
        pivot = returns.pivot(
            index="frequency_bucket", columns="returner_group", values="retention_pct"
        )
        differences = pivot["Made a return"] - pivot["No returns"]

        st.subheader("Pre-Cutoff Returns vs Future Retention")
        st.markdown(
            f"Within comparable order-frequency bands, the returner difference ranges "
            f"from **{differences.min():+.1f}** to **{differences.max():+.1f} percentage "
            "points**. Frequency explains much of the old aggregate gap; return behavior "
            "alone is not a clean satisfaction signal."
        )
        fig = px.bar(
            returns,
            x="frequency_bucket",
            y="retention_pct",
            color="returner_group",
            barmode="group",
            text="retention_pct",
            category_orders={
                "frequency_bucket": ["1 order", "2-3 orders", "4-7 orders", "8+ orders"]
            },
            color_discrete_map={"Made a return": "#4ade80", "No returns": "#fca5a5"},
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(
            xaxis_title="Orders before Sep 10, 2011",
            yaxis_title="Purchase rate in following 90 days (%)",
            legend_title="",
        )
        st.plotly_chart(styled(fig, yrange=[0, 100]))
        st.caption(
            "Return status and frequency are measured before the outcome window. "
            "Revenue is shown net of recorded cancellation value."
        )
        st.dataframe(
            returns[
                [
                    "frequency_bucket",
                    "returner_group",
                    "total_customers",
                    "retained_customers",
                    "retention_pct",
                    "avg_net_revenue_at_cutoff",
                ]
            ].rename(
                columns={
                    "frequency_bucket": "Frequency",
                    "returner_group": "Return Status",
                    "total_customers": "Customers",
                    "retained_customers": "Purchased in Outcome Window",
                    "retention_pct": "Future Retention (%)",
                    "avg_net_revenue_at_cutoff": "Avg Net Revenue (£)",
                }
            ),
            width="stretch",
            hide_index=True,
        )
