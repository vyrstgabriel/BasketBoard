"""
Basketboard: Online Retail Analytics Dashboard
Run: streamlit run dashboard/app.py  (from project root)

Reads from results/ CSVs only. All computation happens in queries/*.sql.
"""

from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RESULTS = Path(__file__).parent.parent / "results"

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Basketboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container { padding-top: 2rem; padding-bottom: 2rem; }

[data-testid="metric-container"] {
    background: #f8f9fb;
    border: 1px solid #e8eaed;
    border-radius: 10px;
    padding: 1rem 1.2rem;
}
[data-testid="metric-container"] label {
    font-size: 0.78rem;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.7rem;
    font-weight: 700;
    color: #111827;
}
[data-testid="stSidebar"] { background: #0f172a; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
hr { border-color: #e5e7eb; margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────
st.sidebar.markdown("## 📊 Basketboard")
st.sidebar.markdown("Online Retail Analytics")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "", ["Overview", "Cohort Retention", "DAU / WAU", "Behavioral Analysis"],
    label_visibility="collapsed",
)
st.sidebar.markdown("---")
st.sidebar.caption("5,878 customers · 37,033 orders · Dec 2009 – Dec 2011")

# ── Data loaders ─────────────────────────────────────────────
@st.cache_data
def load(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / f"{name}.csv")

# ── Chart helpers ─────────────────────────────────────────────
LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="white",
    font=dict(family="Inter, system-ui, sans-serif", color="#374151", size=12),
    margin=dict(l=40, r=20, t=30, b=40),
)
TIER_COLORS = {
    "Champions":      "#6366f1",
    "Loyal":          "#22c55e",
    "New":            "#f59e0b",
    "At Risk":        "#f97316",
    "Lost":           "#ef4444",
}
ACCENT = "#6366f1"

def styled(fig, yformat=None, yrange=None):
    fig.update_layout(**LAYOUT)
    fig.update_xaxes(showgrid=False, linecolor="#e5e7eb", tickfont_size=11)
    fig.update_yaxes(
        showgrid=True, gridcolor="#f3f4f6", linecolor="#e5e7eb",
        tickfont_size=11, tickformat=yformat, range=yrange,
    )
    return fig


# ═══════════════════════════════════════════════════════════════
# PAGE: Overview
# ═══════════════════════════════════════════════════════════════
if page == "Overview":
    st.title("Overview")

    rfm   = load("01_churn_by_rfm_segment")
    anon  = load("06_anonymous_transactions")
    trend = load("03_dau_wau_trend")

    total_customers  = rfm["total_customers"].sum()
    overall_churn    = rfm["churned_customers"].sum() / total_customers * 100
    total_revenue    = rfm["avg_revenue_per_customer"].mul(rfm["total_customers"]).sum()
    identified_share = anon.loc[anon["customer_type"] == "Identified", "pct_of_revenue"].values[0]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Identified Customers", f"{total_customers:,}")
    k2.metric("Overall Churn Rate",   f"{overall_churn:.1f}%")
    k3.metric("Total Revenue (identified)", f"£{total_revenue:,.0f}")
    k4.metric("Anonymous Revenue Share", f"{100 - identified_share:.1f}%")

    st.markdown("---")

    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Customers by RFM Tier")
        fig = px.bar(
            rfm, x="rfm_tier", y="total_customers",
            color="rfm_tier", color_discrete_map=TIER_COLORS,
            text="total_customers",
            category_orders={"rfm_tier": ["Champions", "Loyal", "New", "At Risk", "Lost"]},
        )
        fig.update_traces(textposition="outside", marker_line_width=0)
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Customers")
        st.plotly_chart(styled(fig, yrange=[0, rfm["total_customers"].max() * 1.2]),
                        use_container_width=True)

    with col_r:
        st.subheader("Churn Rate by RFM Tier")
        fig = px.bar(
            rfm, x="rfm_tier", y="churn_rate_pct",
            color="rfm_tier", color_discrete_map=TIER_COLORS,
            text="churn_rate_pct",
            category_orders={"rfm_tier": ["Champions", "Loyal", "New", "At Risk", "Lost"]},
        )
        fig.update_traces(
            texttemplate="%{text:.0f}%", textposition="outside",
            marker_line_width=0,
        )
        fig.add_hline(y=overall_churn, line_dash="dash", line_color="#94a3b8",
                      annotation_text=f"Overall {overall_churn:.0f}%",
                      annotation_position="top right")
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Churn rate (%)")
        st.plotly_chart(styled(fig, yrange=[0, 115]), use_container_width=True)

    st.markdown("---")

    # Anonymous transactions callout
    st.subheader("Anonymous vs Identified Transactions")
    st.caption(
        "22.7% of transactions have no Customer ID and cannot be attributed "
        "to a known customer, representing 15.4% of total revenue."
    )
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(
            anon, values="transaction_count", names="customer_type",
            color="customer_type",
            color_discrete_map={"Identified": ACCENT, "Anonymous": "#e5e7eb"},
            hole=0.55,
        )
        fig.update_traces(textinfo="label+percent", textfont_size=12)
        fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0),
                          paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Share of transaction count")
    with col2:
        fig = px.pie(
            anon, values="total_revenue", names="customer_type",
            color="customer_type",
            color_discrete_map={"Identified": ACCENT, "Anonymous": "#e5e7eb"},
            hole=0.55,
        )
        fig.update_traces(textinfo="label+percent", textfont_size=12)
        fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0),
                          paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Share of revenue")

    st.markdown("---")
    st.subheader("RFM Tier Detail")
    st.dataframe(
        rfm.rename(columns={
            "rfm_tier": "Tier", "total_customers": "Customers",
            "churned_customers": "Churned", "churn_rate_pct": "Churn %",
            "avg_revenue_per_customer": "Avg Revenue (£)",
            "avg_orders": "Avg Orders", "risk_level": "Risk",
        }),
        use_container_width=True, hide_index=True,
    )


# ═══════════════════════════════════════════════════════════════
# PAGE: Cohort Retention
# ═══════════════════════════════════════════════════════════════
elif page == "Cohort Retention":
    st.title("Cohort Retention")
    st.caption("Monthly cohorts: each row is a group of customers by their first purchase month.")

    matrix    = load("02_cohort_retention_matrix")
    min_size  = st.slider("Minimum cohort size", 5, 100, 20, step=5)

    big       = matrix.groupby("cohort_month")["cohort_size"].first()
    big       = big[big >= min_size].index
    filtered  = matrix[matrix["cohort_month"].isin(big)]

    if filtered.empty:
        st.warning("No cohorts meet the minimum size filter.")
    else:
        pivot = filtered.pivot_table(
            index="cohort_month", columns="months_since_first",
            values="retention_pct", aggfunc="first",
        ).sort_index()

        fig = px.imshow(
            pivot.values,
            x=[f"M+{int(c)}" for c in pivot.columns],
            y=list(pivot.index),
            color_continuous_scale="Blues",
            zmin=0, zmax=100,
            text_auto=".0f",
            aspect="auto",
        )
        fig.update_coloraxes(colorbar_title="Retention %")
        fig.update_traces(textfont_size=9)
        fig.update_layout(
            xaxis_title="Months since first purchase",
            yaxis_title="Cohort (first purchase month)",
            margin=dict(l=80, r=20, t=20, b=40),
            paper_bgcolor="white",
            font=dict(family="Inter, system-ui, sans-serif", size=11),
            height=max(400, len(pivot) * 22),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Showing {len(pivot)} cohorts with at least {min_size} customers.")


# ═══════════════════════════════════════════════════════════════
# PAGE: DAU / WAU
# ═══════════════════════════════════════════════════════════════
elif page == "DAU / WAU":
    st.title("Daily & Weekly Purchasing Activity")

    trend = load("03_dau_wau_trend")
    dau   = trend[trend["granularity"] == "day"].copy()
    wau   = trend[trend["granularity"] == "week"].copy()
    dau["period"] = pd.to_datetime(dau["period"])

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Peak DAU (customers)",  f"{dau['active_customers'].max():,}")
    k2.metric("Peak WAU (customers)",  f"{wau['active_customers'].max():,}")
    k3.metric("Peak Daily Revenue",    f"£{dau['revenue'].max():,.0f}")
    k4.metric("Avg Daily Orders",      f"{dau['orders_placed'].mean():.0f}")

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["Active Customers", "Orders Placed", "Daily Revenue"])

    with tab1:
        fig = go.Figure(go.Scatter(
            x=dau["period"], y=dau["active_customers"],
            mode="lines", line=dict(color=ACCENT, width=1.5),
            fill="tozeroy", fillcolor="rgba(99,102,241,0.08)",
            hovertemplate="%{x|%b %d %Y}: %{y:,} customers<extra></extra>",
        ))
        fig.update_layout(xaxis_title="", yaxis_title="Purchasing customers", showlegend=False)
        st.plotly_chart(styled(fig), use_container_width=True)

    with tab2:
        fig = go.Figure(go.Scatter(
            x=dau["period"], y=dau["orders_placed"],
            mode="lines", line=dict(color="#a78bfa", width=1.5),
            fill="tozeroy", fillcolor="rgba(167,139,250,0.08)",
            hovertemplate="%{x|%b %d %Y}: %{y:,} orders<extra></extra>",
        ))
        fig.update_layout(xaxis_title="", yaxis_title="Orders placed", showlegend=False)
        st.plotly_chart(styled(fig), use_container_width=True)

    with tab3:
        fig = go.Figure(go.Scatter(
            x=dau["period"], y=dau["revenue"],
            mode="lines", line=dict(color="#22c55e", width=1.5),
            fill="tozeroy", fillcolor="rgba(34,197,94,0.08)",
            hovertemplate="%{x|%b %d %Y}: £%{y:,.0f}<extra></extra>",
        ))
        fig.update_layout(xaxis_title="", yaxis_title="Revenue (£)", showlegend=False)
        st.plotly_chart(styled(fig), use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: Behavioral Analysis
# ═══════════════════════════════════════════════════════════════
elif page == "Behavioral Analysis":
    st.title("Behavioral Analysis")

    tab1, tab2, tab3 = st.tabs(
        ["Time to Second Purchase", "Order Frequency AHA", "Returns Behavior"]
    )

    # ── Time to second purchase ───────────────────────────────
    with tab1:
        st.subheader("Time to Second Purchase vs Long-Term Retention")
        st.markdown(
            "Customers who make a second purchase within **30 days** retain at "
            "nearly **3x the rate** of one-time buyers. The second purchase is "
            "the moment a customer converts from 'tried us once' to 'has a habit.'"
        )

        t2p = load("04_time_to_second_purchase")

        fig = px.bar(
            t2p, x="repeat_bucket", y="retention_pct",
            text="retention_pct",
            color="retention_pct",
            color_continuous_scale=["#dbeafe", "#1d4ed8"],
        )
        fig.update_traces(
            texttemplate="%{text:.1f}%", textposition="outside",
            marker_line_width=0,
        )
        fig.update_coloraxes(showscale=False)
        fig.update_layout(xaxis_title="Time to second purchase", yaxis_title="Retention (%)",
                          showlegend=False)
        st.plotly_chart(styled(fig, yrange=[0, 80]), use_container_width=True)

        st.dataframe(
            t2p[["repeat_bucket","total_customers","retained_customers","retention_pct"]].rename(columns={
                "repeat_bucket": "Time to Second Purchase",
                "total_customers": "Customers",
                "retained_customers": "Retained",
                "retention_pct": "Retention (%)",
            }),
            use_container_width=True, hide_index=True,
        )

    # ── Order frequency AHA ───────────────────────────────────
    with tab2:
        st.subheader("Order Frequency AHA Moment")
        st.markdown(
            "Retention climbs steeply from order 1 through order 5, then "
            "levels off. The steepest gains happen between orders 2 and 4 — "
            "the window where CRM intervention has the most impact."
        )

        aha = load("05_order_frequency_aha")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=aha["lifetime_orders"], y=aha["retention_pct"],
            marker_color=ACCENT, marker_line_width=0,
            text=aha["retention_pct"],
            texttemplate="%{text:.0f}%", textposition="outside",
            name="Retention %",
        ))
        fig.add_trace(go.Scatter(
            x=aha["lifetime_orders"], y=aha["retention_pct"],
            mode="lines+markers",
            line=dict(color="#f59e0b", width=2, dash="dot"),
            marker=dict(size=6, color="#f59e0b"),
            name="Trend",
            yaxis="y",
        ))
        fig.update_layout(
            xaxis_title="Lifetime orders placed",
            yaxis_title="Retention (%)",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(styled(fig, yrange=[0, 100]), use_container_width=True)

    # ── Returns behavior ──────────────────────────────────────
    with tab3:
        st.subheader("Returns Behavior vs Retention")
        st.markdown(
            "Customers who made at least one return retain at **61.9%** vs "
            "**39.6%** for those who never returned. They also spend 6x more "
            "and place 4x as many orders — returners are the most engaged "
            "customers, not the most dissatisfied."
        )

        ret = load("07_returns_analysis")

        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                ret, x="returner_group", y="retention_pct",
                color="returner_group",
                color_discrete_map={
                    "Made a return": "#4ade80",
                    "No returns":    "#fca5a5",
                },
                text="retention_pct",
            )
            fig.update_traces(
                texttemplate="%{text:.1f}%", textposition="outside",
                marker_line_width=0, width=0.4,
            )
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Retention (%)")
            st.plotly_chart(styled(fig, yrange=[0, 80]), use_container_width=True)

        with col2:
            fig = px.bar(
                ret, x="returner_group", y="avg_lifetime_revenue",
                color="returner_group",
                color_discrete_map={
                    "Made a return": "#4ade80",
                    "No returns":    "#fca5a5",
                },
                text="avg_lifetime_revenue",
            )
            fig.update_traces(
                texttemplate="£%{text:,.0f}", textposition="outside",
                marker_line_width=0, width=0.4,
            )
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Avg lifetime revenue (£)")
            st.plotly_chart(styled(fig, yrange=[0, ret["avg_lifetime_revenue"].max() * 1.2]),
                            use_container_width=True)

        st.dataframe(
            ret.rename(columns={
                "returner_group": "Group",
                "total_customers": "Customers",
                "retained_customers": "Retained",
                "retention_pct": "Retention (%)",
                "avg_lifetime_revenue": "Avg Revenue (£)",
                "avg_orders": "Avg Orders",
            }),
            use_container_width=True, hide_index=True,
        )
        st.caption(
            "Returners are high-engagement customers who order frequently enough "
            "to occasionally be disappointed. Lower-engagement customers don't "
            "order enough to bother returning."
        )
