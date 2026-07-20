"""
FlavorLens — Streamlit App
-----------------------------
Presentation layer only. No COI math happens here — this file reads
already-computed scores from python/analytics/coi_calculator.py and
renders them. See ARCHITECTURE.md for why that separation matters.
"""

import sys
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from python.analytics.coi_calculator import compute_coi, get_effective_weights
from python.analytics.queries import get_engine, locality_cuisine_metrics, locality_averages

st.set_page_config(page_title="FlavorLens", page_icon="🍽️", layout="wide")


# --- Data loading (cached so we don't re-hit Postgres on every interaction) ---

@st.cache_data(ttl=3600)
def load_raw_metrics():
    engine = get_engine()
    lc = locality_cuisine_metrics(engine)
    la = locality_averages(engine)
    return lc, la


def get_scored_data(weights: dict = None) -> pd.DataFrame:
    lc, la = load_raw_metrics()
    return compute_coi(lc.copy(), la.copy(), weights=weights)


# --- Sidebar: locality selection + weight sliders ---

st.sidebar.title("FlavorLens 🍽️")
st.sidebar.caption("Restaurant Expansion Intelligence — Bangalore, by locality")

default_weights = get_effective_weights()

st.sidebar.subheader("Cuisine Opportunity Index weights")
st.sidebar.caption(
    "These are starting assumptions, not derived ground truth. "
    "Adjust them to reflect what matters most for your decision."
)

demand_w = st.sidebar.slider("Demand", 0.0, 1.0, round(default_weights["demand"], 2), 0.05)
competition_w = st.sidebar.slider("Competition (inverted)", 0.0, 1.0, round(default_weights["competition"], 2), 0.05)
affordability_w = st.sidebar.slider("Affordability", 0.0, 1.0, round(default_weights["affordability"], 2), 0.05)
rating_stability_w = st.sidebar.slider("Rating Stability", 0.0, 1.0, round(default_weights["rating_stability"], 2), 0.05)

custom_weights = {
    "demand": demand_w,
    "competition": competition_w,
    "affordability": affordability_w,
    "rating_stability": rating_stability_w,
}

if sum(custom_weights.values()) == 0:
    st.sidebar.warning("At least one weight must be above zero — using defaults instead.")
    custom_weights = None

with st.spinner("Scoring cuisines..."):
    scored = get_scored_data(custom_weights)

localities = sorted(scored["locality"].unique())
selected_locality = st.sidebar.selectbox("Locality", localities, index=localities.index("Indiranagar") if "Indiranagar" in localities else 0)


# --- Main content ---

st.title("FlavorLens 🍽️")
st.caption("Bangalore, by locality — v1 scope. See README.md for known limitations.")

locality_data = scored[scored["locality"] == selected_locality].copy()

if locality_data.empty:
    st.warning(f"No data available for {selected_locality}.")
else:
    st.subheader(f"Top cuisine opportunities in {selected_locality}")

    display_cols = ["cuisine", "coi", "confidence", "restaurant_count", "avg_rating", "avg_cost"]
    display_df = locality_data[display_cols].rename(columns={
        "cuisine": "Cuisine",
        "coi": "COI",
        "confidence": "Confidence %",
        "restaurant_count": "Restaurant Count",
        "avg_rating": "Avg Rating",
        "avg_cost": "Avg Cost (₹ for two)",
    }).round(1)

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.caption(
        "Confidence reflects how much data backs each score (rated restaurant "
        "count and review volume) — a high COI with low confidence means a "
        "real gap, but one with less evidence behind it than a high-confidence score."
    )

    st.divider()

    # --- Drill-down into a specific cuisine ---
    cuisine_options = locality_data["cuisine"].tolist()
    selected_cuisine = st.selectbox("Drill into a cuisine", cuisine_options)

    row = locality_data[locality_data["cuisine"] == selected_cuisine].iloc[0]

    col1, col2 = st.columns([1, 1])

    with col1:
        st.metric("Cuisine Opportunity Index", f"{row['coi']:.1f}")
        st.metric("Confidence", f"{row['confidence']:.0f}%")
        st.metric("Restaurants in this locality", int(row["restaurant_count"]))
        st.metric("Average cost for two", f"₹{row['avg_cost']:.0f}")

    with col2:
        radar_categories = ["Demand", "Competition (inverted)", "Affordability", "Rating Stability"]
        radar_values = [
            row["demand_score"], row["competition_score"],
            row["affordability_score"], row["rating_stability_score"],
        ]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=radar_values + [radar_values[0]],
            theta=radar_categories + [radar_categories[0]],
            fill="toself",
            name=selected_cuisine,
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
            margin=dict(t=60, b=60, l=80, r=80),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- City-wide comparison for context ---
    st.subheader(f"How does {selected_cuisine} compare across Bangalore?")
    cuisine_citywide = scored[scored["cuisine"] == selected_cuisine].sort_values("coi", ascending=False).head(15)

    bar_fig = px.bar(
        cuisine_citywide,
        x="locality", y="coi",
        color="confidence",
        color_continuous_scale="Blues",
        labels={"coi": "COI", "locality": "Locality", "confidence": "Confidence %"},
        title=f"Top 15 localities for {selected_cuisine} by COI",
    )
    bar_fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(bar_fig, use_container_width=True)

st.divider()
st.caption(
    "FlavorLens v1 — Bangalore, by locality. Data: Zomato Bangalore Restaurants "
    "(Kaggle), static snapshot. No synthetic data is used; sparse combinations "
    "show reduced confidence rather than filler values. See README.md for full "
    "methodology and known limitations."
)