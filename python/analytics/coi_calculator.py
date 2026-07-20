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

    df = df.merge(locality_avg[["locality", "locality_avg_cost"]], on="locality", how="left")

    # --- Demand: average engagement (votes) per restaurant ---
    df["demand_score"] = normalize_0_100(df["avg_votes"])

    # --- Competition: restaurant density, inverted so LOW competition = HIGH opportunity ---
    raw_competition = normalize_0_100(df["restaurant_count"])
    df["competition_score"] = 100 - raw_competition

    # --- Affordability: how much cheaper than the locality's own average ---
    # Positive value = cheaper than locality average = more affordable = higher score.
    # Some (locality, cuisine) pairs have every restaurant missing cost data
    # (approx_cost_for_two had 346 nulls in the raw dataset) — in that case
    # avg_cost is NaN for the whole group. Rather than let that NaN cascade
    # into a NaN COI for the row, fill with the dataset median (neutral
    # assumption) before normalizing, matching the stddev handling below.
    relative_affordability = df["locality_avg_cost"] - df["avg_cost"]
    relative_affordability_filled = relative_affordability.fillna(relative_affordability.median())
    df["affordability_score"] = normalize_0_100(relative_affordability_filled)

    # --- Rating stability: inverted normalized stddev (lower spread = more stable) ---
    # Groups with a single rated restaurant have NaN stddev (undefined) —
    # treat as neutral (50) rather than dropping the row or assuming perfect stability.
    stddev_filled = df["rating_stddev"].fillna(df["rating_stddev"].median())
    raw_stability = normalize_0_100(stddev_filled)
    df["rating_stability_score"] = 100 - raw_stability

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

    print(f"\nTotal (locality, cuisine) pairs scored: {len(result)}")
    print("\nTop 10 opportunities overall (by COI):")
    print(result[[
        "locality", "cuisine", "coi", "confidence",
        "demand_score", "competition_score", "affordability_score", "rating_stability_score"
    ]].head(10).to_string(index=False))

    print("\nBottom 10 (lowest COI):")
    print(result[[
        "locality", "cuisine", "coi", "confidence"
    ]].tail(10).to_string(index=False))