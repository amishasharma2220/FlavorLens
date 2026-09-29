"""
FlavorLens — Cuisine Opportunity Index (COI) Calculator
----------------------------------------------------------
Pure computation module. Takes the raw per-(locality, cuisine) metrics from
analytics/queries.py and turns them into normalized component scores, a
final COI, and a confidence rating.

No API calls, no database writes here — same input always produces the
same output. This is deliberate (see ARCHITECTURE.md): the LLM explains
these numbers later, it never touches this module.

Components (v1 — growth is NOT included, see note below):
  - Demand Score        : normalized average votes per restaurant (engagement)
  - Competition Score    : normalized restaurant count, INVERTED (fewer = more opportunity)
  - Affordability Score  : how much cheaper than the locality average
  - Rating Stability     : normalized rating spread (stddev), INVERTED (lower spread = more stable)

Growth is omitted because the source dataset has no reliable establishment-
date or historical field (see ARCHITECTURE.md / AGENTS.md). Rather than
fabricate a growth signal, its configured weight is redistributed
proportionally across the four real components below.
"""

import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config import coi_config
from python.analytics.queries import locality_cuisine_metrics, locality_averages, get_engine


# --- Weight handling ---------------------------------------------------

def get_effective_weights() -> dict:
    """
    Pulls weights from config.py's COIConfig and drops growth_weight,
    redistributing it proportionally across the remaining four components.

    Example: if config has demand=0.30, competition=0.20, growth=0.20,
    rating_stability=0.15, affordability=0.15 — growth's 0.20 is
    distributed proportionally to the other four based on their existing
    share, so the four weights still sum to 1.0 and their *relative*
    balance is preserved.
    """
    raw = {
        "demand": getattr(coi_config, "demand_weight", 0.30),
        "competition": getattr(coi_config, "competition_weight", 0.25),
        "affordability": getattr(coi_config, "affordability_weight", 0.20),
        "rating_stability": getattr(coi_config, "rating_stability_weight", 0.25),
    }
    growth = getattr(coi_config, "growth_weight", 0.0)

    total_without_growth = sum(raw.values())
    if growth > 0 and total_without_growth > 0:
        # redistribute growth's share proportionally
        scale = (total_without_growth + growth) / total_without_growth
        raw = {k: v * scale for k, v in raw.items()}

    # normalize to guarantee exact sum of 1.0 regardless of rounding
    total = sum(raw.values())
    return {k: v / total for k, v in raw.items()}


# --- Normalization -------------------------------------------------------

def normalize_0_100(series: pd.Series) -> pd.Series:
    """
    Min-max scale a series to 0-100.

    Edge case: if min == max (e.g. every value in the series is identical,
    which happens with very small groups), scaling is undefined — return
    a neutral 50 for every row rather than dividing by zero or silently
    producing NaN/inf.
    """
    min_val, max_val = series.min(), series.max()
    if pd.isna(min_val) or pd.isna(max_val) or min_val == max_val:
        return pd.Series([50.0] * len(series), index=series.index)
    return ((series - min_val) / (max_val - min_val)) * 100


def normalize_within_city(df: pd.DataFrame, column: str) -> pd.Series:
    """
    Same min-max scaling as normalize_0_100, but computed separately WITHIN
    each city rather than across the whole combined dataset.

    This matters once you have multiple cities of very different sizes:
    Bangalore has ~12,500 restaurants vs. ~1,000-5,500 for the other
    cities. Normalizing globally would mean Bangalore's much wider range
    of raw values (restaurant counts, votes, etc.) dominates the 0-100
    scale, making it structurally harder for a genuinely strong opportunity
    in a smaller city to score as highly as one in Bangalore — not because
    it's a worse opportunity, but because it's being measured against a
    different city's scale. Scoring within each city's own distribution is
    the fair comparison, since "is this a good opportunity in Noida" is
    inherently a Noida-relative question, not a Bangalore-relative one.
    """
    return df.groupby("city")[column].transform(lambda s: normalize_0_100(s))


# --- Confidence ------------------------------------------------------------

def compute_confidence(rated_count: pd.Series, total_votes: pd.Series) -> pd.Series:
    """
    Confidence is NOT a vibe number — it's derived from how much real
    evidence backs each (locality, cuisine) pair. Two components, each
    capped at 1.0 against a configured threshold, averaged:
      - rated_restaurant_count vs min_restaurants_for_full_confidence
      - total_votes vs min_reviews_for_full_confidence
    A pair with plenty of restaurants but few reviews (or vice versa)
    still gets a moderate, not high, confidence score.
    """
    min_restaurants = getattr(coi_config, "min_restaurants_for_full_confidence", 10)
    min_reviews = getattr(coi_config, "min_reviews_for_full_confidence", 50)

    restaurant_ratio = (rated_count / min_restaurants).clip(upper=1.0)
    votes_ratio = (total_votes / min_reviews).clip(upper=1.0)

    return ((restaurant_ratio + votes_ratio) / 2) * 100


# --- Main COI computation ---------------------------------------------------

def compute_coi(df: pd.DataFrame = None, locality_avg: pd.DataFrame = None,
                 weights: dict = None) -> pd.DataFrame:
    """
    Computes normalized component scores, final COI, and confidence for
    every (locality, cuisine) pair.

    weights: optional override dict with keys demand/competition/
    affordability/rating_stability (must sum to 1.0, or will be
    renormalized to do so). If not provided, falls back to
    get_effective_weights() (config.py defaults, growth redistributed).
    """
    if df is None or locality_avg is None:
        engine = get_engine()
        df = df if df is not None else locality_cuisine_metrics(engine)
        locality_avg = locality_avg if locality_avg is not None else locality_averages(engine)

    df = df.merge(locality_avg[["city", "locality", "locality_avg_cost"]], on=["city", "locality"], how="left")

    # --- Demand: average engagement (votes) per restaurant, normalized WITHIN each city ---
    df["demand_score"] = normalize_within_city(df, "avg_votes")

    # --- Competition: restaurant density, inverted so LOW competition = HIGH opportunity ---
    # Normalized within each city — density of 300 restaurants means something
    # different in Bangalore (12,480 total) than in Noida (1,080 total).
    df["_raw_competition"] = df["restaurant_count"]
    raw_competition = normalize_within_city(df, "_raw_competition")
    df["competition_score"] = 100 - raw_competition
    df = df.drop(columns=["_raw_competition"])

    # --- Affordability: how much cheaper than the locality's own average ---
    # Positive value = cheaper than locality average = more affordable = higher score.
    # Missing cost data (346 nulls in the original Bangalore source, and
    # similar gaps possible in other cities) is filled with that CITY's own
    # median relative-affordability, not a single dataset-wide median —
    # a Bangalore price gap and a Gurgaon price gap aren't on the same scale.
    df["_relative_affordability"] = df["locality_avg_cost"] - df["avg_cost"]
    df["_relative_affordability"] = df.groupby("city")["_relative_affordability"].transform(
        lambda s: s.fillna(s.median())
    )
    df["affordability_score"] = normalize_within_city(df, "_relative_affordability")
    df = df.drop(columns=["_relative_affordability"])

    # --- Rating stability: inverted normalized stddev (lower spread = more stable) ---
    # Groups with a single rated restaurant have NaN stddev (undefined) —
    # treat as neutral (that city's median) rather than dropping the row
    # or assuming perfect stability.
    df["_stddev_filled"] = df.groupby("city")["rating_stddev"].transform(
        lambda s: s.fillna(s.median())
    )
    raw_stability = normalize_within_city(df, "_stddev_filled")
    df["rating_stability_score"] = 100 - raw_stability
    df = df.drop(columns=["_stddev_filled"])

    # --- Confidence ---
    df["confidence"] = compute_confidence(df["rated_restaurant_count"], df["total_votes"])

    # --- Final weighted COI ---
    if weights is None:
        weights = get_effective_weights()
    else:
        # Defensive: renormalize any custom weights (e.g. from Streamlit
        # sliders) to guarantee they sum to 1.0, regardless of what the
        # UI passes in.
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}

    df["coi"] = (
        weights["demand"] * df["demand_score"]
        + weights["competition"] * df["competition_score"]
        + weights["affordability"] * df["affordability_score"]
        + weights["rating_stability"] * df["rating_stability_score"]
    )

    # Safety net: after handling the known NaN sources above (missing cost
    # data, single-restaurant stddev), no row should have a NaN COI. If one
    # shows up anyway, surface it loudly rather than silently ranking a
    # broken row — this is a signal something new in the data wasn't
    # accounted for, not something to filter out quietly.
    remaining_nan = df["coi"].isna().sum()
    if remaining_nan > 0:
        print(f"WARNING: {remaining_nan} rows still have NaN COI after "
              f"known-issue handling — investigate before trusting output.")
        print(df[df["coi"].isna()][["locality", "cuisine"]])

    return df.sort_values("coi", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    print("Effective weights (growth redistributed):")
    for k, v in get_effective_weights().items():
        print(f"  {k}: {v:.3f}")

    result = compute_coi()

    print(f"\nTotal (city, locality, cuisine) triples scored: {len(result)}")
    print("\nTop 10 opportunities overall (by COI):")
    print(result[[
        "city", "locality", "cuisine", "coi", "confidence",
        "demand_score", "competition_score", "affordability_score", "rating_stability_score"
    ]].head(10).to_string(index=False))

    print("\nBottom 10 (lowest COI):")
    print(result[[
        "city", "locality", "cuisine", "coi", "confidence"
    ]].tail(10).to_string(index=False))