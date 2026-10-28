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

# set_page_config MUST be the very first Streamlit command in the script —
# even accessing st.secrets before this point counts as an earlier command
# and breaks it. See the comment below for why the secrets bridge comes
# after this line, not before.
st.set_page_config(page_title="FlavorLens", page_icon="🍽️", layout="wide")

# Streamlit Community Cloud provides secrets via st.secrets, not a .env file.
# Bridge them into environment variables here, before any local module
# (config.py, coi_calculator.py, queries.py) is imported — those modules
# read os.getenv() at import time, so this must run before those imports.
# Locally, .env is loaded first and already provides DB_HOST, so st.secrets
# is never touched — touching it without a secrets.toml makes Streamlit
# render a red "No secrets files found" banner even inside a try/except.
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("DB_HOST"):
    try:
        for key, value in st.secrets.items():
            os.environ[key] = str(value)
    except Exception:
        pass

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from python.analytics.coi_calculator import compute_coi, get_effective_weights
from python.analytics.queries import get_engine, locality_cuisine_metrics, locality_averages
from python.llm.copilot import explain_opportunity


# --- Data loading (cached so we don't re-hit Postgres on every interaction) ---

@st.cache_data(ttl=3600)
def load_raw_metrics():
    engine = get_engine()
    lc = locality_cuisine_metrics(engine)
    la = locality_averages(engine)
    return lc, la


@st.cache_data(ttl=3600, show_spinner=False)
def get_explanation(city: str, locality: str, cuisine: str, metrics: dict) -> str:
    # Cached on the exact inputs, so re-clicking the same row (same weights)
    # doesn't spend another Groq call.
    return explain_opportunity(locality, cuisine, metrics, city=city)


def get_scored_data(weights: dict = None) -> pd.DataFrame:
    lc, la = load_raw_metrics()
    return compute_coi(lc.copy(), la.copy(), weights=weights)


# --- Sidebar: locality selection + weight sliders ---

st.sidebar.title("FlavorLens 🍽️")
st.sidebar.caption("Restaurant Expansion Intelligence — Bangalore, New Delhi, Gurgaon, Noida, by locality")

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

localities_by_city = scored.groupby("city")["locality"].unique().apply(sorted).to_dict()
cities = sorted(localities_by_city.keys())
selected_city = st.sidebar.selectbox("City", cities, index=cities.index("Bangalore") if "Bangalore" in cities else 0)

localities = localities_by_city[selected_city]
selected_locality = st.sidebar.selectbox(
    "Locality", localities,
    index=localities.index("Indiranagar") if selected_city == "Bangalore" and "Indiranagar" in localities else 0
)

st.sidebar.subheader("Evidence filter")
min_restaurants = st.sidebar.slider(
    "Minimum restaurants per cuisine", 1, 10, 2, 1,
    help=(
        "Hides cuisines backed by fewer restaurants than this in the locality. "
        "A single restaurant can rank high on its own votes alone, and one "
        "restaurant tagged with several cuisines shows up as several identical rows. "
        "Set to 1 to see everything."
    ),
)


# --- Main content ---

st.title("FlavorLens 🍽️")
st.caption("Bangalore, New Delhi, Gurgaon, Noida — v2 scope. See README.md for known limitations.")

locality_all = scored[(scored["city"] == selected_city) & (scored["locality"] == selected_locality)].copy()
locality_data = locality_all[locality_all["restaurant_count"] >= min_restaurants].copy()
hidden_count = len(locality_all) - len(locality_data)

if locality_all.empty:
    st.warning(f"No data available for {selected_locality}.")
elif locality_data.empty:
    st.warning(
        f"All {len(locality_all)} cuisines in {selected_locality} have fewer than "
        f"{min_restaurants} restaurants, so there isn't enough evidence to rank them. "
        "Lower the 'Minimum restaurants per cuisine' filter in the sidebar to see them anyway."
    )
else:
    st.subheader(f"Top cuisine opportunities in {selected_locality}, {selected_city}")

    display_cols = ["cuisine", "coi", "confidence", "restaurant_count", "avg_rating", "avg_cost"]
    display_df = locality_data[display_cols].rename(columns={
        "cuisine": "Cuisine",
        "coi": "COI",
        "confidence": "Confidence %",
        "restaurant_count": "Restaurant Count",
        "avg_rating": "Avg Rating",
        "avg_cost": "Avg Cost (₹ for two)",
    }).round(1)
    # Unrated cuisines are stored as NULL; show a dash instead of "None".
    display_df["Avg Rating"] = display_df["Avg Rating"].apply(
        lambda v: "—" if pd.isna(v) else f"{v:.1f}"
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)
    if hidden_count:
        st.caption(
            f"{hidden_count} cuisine(s) hidden for having fewer than {min_restaurants} "
            "restaurants here — adjust the evidence filter in the sidebar to include them."
        )

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
            paper_bgcolor="rgba(0,0,0,0)",
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(128,128,128,0.35)"),
                angularaxis=dict(gridcolor="rgba(128,128,128,0.35)"),
            ),
            showlegend=False,
            margin=dict(t=60, b=60, l=80, r=80),
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- Expansion Copilot: explains the numbers above, never calculates ---
    st.markdown("#### Expansion Copilot")
    st.caption(
        "Plain-language summary of the scores above, written by Llama 3.1 via Groq. "
        "It only sees the numbers shown here and is instructed not to add any of its own."
    )
    if st.button("Explain this opportunity", key="explain_btn"):
        copilot_metrics = {
            k: float(row[k]) for k in [
                "coi", "confidence", "demand_score", "competition_score",
                "affordability_score", "rating_stability_score",
                "restaurant_count", "avg_rating", "avg_cost",
            ]
        }
        with st.spinner("Writing explanation..."):
            explanation = get_explanation(
                selected_city, selected_locality, selected_cuisine, copilot_metrics
            )
        st.info(explanation)

    st.divider()

    # --- Cross-city comparison for context ---
    st.subheader(f"How does {selected_cuisine} compare across all cities?")
    cuisine_citywide = scored[
        (scored["cuisine"] == selected_cuisine) & (scored["restaurant_count"] >= min_restaurants)
    ].sort_values("coi", ascending=False).head(15)
    cuisine_citywide["locality_label"] = cuisine_citywide["locality"] + " (" + cuisine_citywide["city"] + ")"

    bar_fig = px.bar(
        cuisine_citywide,
        x="locality_label", y="coi",
        color="confidence",
        color_continuous_scale="Blues",
        labels={"coi": "COI", "locality_label": "Locality (City)", "confidence": "Confidence %"},
        title=f"Top 15 localities for {selected_cuisine} by COI, across all cities (min. {min_restaurants} restaurants)",
    )
    bar_fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(bar_fig, use_container_width=True)

st.divider()
st.caption(
    "FlavorLens v2 — Bangalore, New Delhi, Gurgaon, Noida, by locality. "
    "20,151 restaurants across 545 city-locality pairs and 114 cuisines. "
    "Data: Zomato Bangalore Restaurants (Kaggle) + Zomato API global dataset "
    "(Kaggle), static snapshots. No synthetic data is used; sparse combinations "
    "show reduced confidence rather than filler values. See README.md for full "
    "methodology and known limitations."
)