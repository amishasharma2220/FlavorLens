"""
FlavorLens — Analytics Queries
--------------------------------
SQL retrieval and aggregation only. This module does NOT compute the COI —
it produces the raw per-(locality, cuisine) metrics that coi_calculator.py
will normalize and weight. Keeping this separation means the SQL stays
simple (GROUP BY + aggregates) and the scoring logic stays testable in pure
Python, per ARCHITECTURE.md.
"""

import pandas as pd
from sqlalchemy import create_engine, text

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config import db_config


def get_engine():
    return create_engine(db_config.url)


def locality_cuisine_metrics(engine=None) -> pd.DataFrame:
    """
    Core aggregation: one row per (locality, cuisine) pair with the raw
    metrics needed to compute demand, competition, affordability, and
    rating stability. No normalization or scoring happens here — that's
    coi_calculator.py's job.
    """
    engine = engine or get_engine()

    query = text("""
        SELECT
            r.location AS locality,
            rc.cuisine,
            COUNT(*)                       AS restaurant_count,
            AVG(r.rating)                  AS avg_rating,
            STDDEV(r.rating)               AS rating_stddev,
            AVG(r.approx_cost_for_two)     AS avg_cost,
            SUM(r.votes)                   AS total_votes,
            AVG(r.votes)                   AS avg_votes,
            COUNT(r.rating)                AS rated_restaurant_count
        FROM restaurants r
        JOIN restaurant_cuisines rc ON r.restaurant_id = rc.restaurant_id
        GROUP BY r.location, rc.cuisine
        ORDER BY r.location, restaurant_count DESC;
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    return df


def locality_averages(engine=None) -> pd.DataFrame:
    """
    Locality-wide baselines (across all cuisines) — needed to compute
    affordability relative to the locality's overall price level, e.g.
    "this cuisine is cheaper than the Indiranagar average" rather than
    comparing against a fixed absolute number.
    """
    engine = engine or get_engine()

    query = text("""
        SELECT
            location AS locality,
            AVG(approx_cost_for_two) AS locality_avg_cost,
            AVG(rating)              AS locality_avg_rating,
            COUNT(*)                 AS locality_restaurant_count
        FROM restaurants
        GROUP BY location
        ORDER BY locality_restaurant_count DESC;
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    return df


def cuisine_totals(engine=None) -> pd.DataFrame:
    """
    City-wide (all-locality) totals per cuisine. Useful as a sanity check
    and for locality-comparison charts in the Streamlit app later.
    """
    engine = engine or get_engine()

    query = text("""
        SELECT
            rc.cuisine,
            COUNT(*)                   AS restaurant_count,
            AVG(r.rating)               AS avg_rating,
            AVG(r.approx_cost_for_two)  AS avg_cost,
            SUM(r.votes)                 AS total_votes
        FROM restaurants r
        JOIN restaurant_cuisines rc ON r.restaurant_id = rc.restaurant_id
        GROUP BY rc.cuisine
        ORDER BY restaurant_count DESC;
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    return df


if __name__ == "__main__":
    # Quick sanity check when run directly — not the production entry point.
    engine = get_engine()

    print("=" * 60)
    print("LOCALITY x CUISINE METRICS (sample)")
    print("=" * 60)
    lc = locality_cuisine_metrics(engine)
    print(f"Total (locality, cuisine) pairs: {len(lc)}")
    print(lc.head(10))

    print("\n" + "=" * 60)
    print("LOCALITY AVERAGES (sample)")
    print("=" * 60)
    la = locality_averages(engine)
    print(f"Total localities: {len(la)}")
    print(la.head(10))

    print("\n" + "=" * 60)
    print("CUISINE TOTALS (top 10 by restaurant count)")
    print("=" * 60)
    ct = cuisine_totals(engine)
    print(ct.head(10))