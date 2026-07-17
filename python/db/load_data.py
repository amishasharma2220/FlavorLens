"""
FlavorLens — Data Cleaning + Load
-----------------------------------
Cleans the raw Zomato Bangalore export and loads it into PostgreSQL as two
tables: restaurants (one row per unique restaurant) and restaurant_cuisines
(one row per restaurant-cuisine pair, since restaurants often serve multiple
cuisines and the raw column stores them as a single comma-separated string).

Run schema.sql against your database first:
    psql -U your_user -d flavorlens -f python/db/schema.sql

Then:
    python python/db/load_data.py
"""

import re
import pandas as pd
from sqlalchemy import create_engine

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config import db_config

RAW_PATH = "python/data/raw/zomato.csv"


def clean_rate(value):
    """'4.1/5' -> 4.1 ; 'NEW' or NaN -> None (missing, not zero)."""
    if pd.isna(value) or value == "NEW" or value == "-":
        return None
    try:
        return float(str(value).split("/")[0].strip())
    except (ValueError, IndexError):
        return None


def clean_cost(value):
    """'1,200' -> 1200.0 ; handles missing values."""
    if pd.isna(value):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def clean_boolean_yes_no(value):
    """'Yes'/'No' -> True/False."""
    if pd.isna(value):
        return None
    return str(value).strip().lower() == "yes"


def load_and_clean(raw_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(raw_path)

    # Drop columns not needed for COI — mostly-null or irrelevant to scoring.
    df = df.drop(
        columns=[
            "url", "phone", "dish_liked", "reviews_list", "menu_item",
            "listed_in(city)",  # this is the scrape-target area, not the restaurant's
                                 # actual locality — "location" is the correct field to use
        ],
        errors="ignore",
    )

    # --- Deduplicate restaurants ---
    # This dataset lists the same physical restaurant multiple times, once per
    # listed_in(type) (Delivery / Dine-out / Buffet / etc.). Without collapsing
    # these, restaurant counts per locality+cuisine are inflated, which directly
    # corrupts the Competition Score. Name + address is a reasonable unique key.
    before = len(df)
    df = df.drop_duplicates(subset=["name", "address"], keep="first")
    print(f"Deduplicated restaurants: {before} -> {len(df)} rows "
          f"({before - len(df)} duplicate listings removed)")

    # --- Clean individual columns ---
    df["rating"] = df["rate"].apply(clean_rate)
    df["approx_cost_for_two"] = df["approx_cost(for two people)"].apply(clean_cost)
    df["online_order"] = df["online_order"].apply(clean_boolean_yes_no)
    df["book_table"] = df["book_table"].apply(clean_boolean_yes_no)

    # Drop rows with no location or no cuisine at all — unusable for COI either way.
    df = df.dropna(subset=["location", "cuisines"])

    restaurants = df[[
        "name", "address", "location", "rest_type",
        "approx_cost_for_two", "rating", "votes",
        "online_order", "book_table",
    ]].reset_index(drop=True)
    restaurants.index.name = "restaurant_id"

    # --- Explode cuisines into one row per (restaurant, cuisine) ---
    cuisines_df = df[["cuisines"]].reset_index(drop=True)
    cuisines_df.index.name = "restaurant_id"
    cuisines_df["cuisine"] = cuisines_df["cuisines"].str.split(",")
    cuisines_exploded = cuisines_df.explode("cuisine")
    cuisines_exploded["cuisine"] = cuisines_exploded["cuisine"].str.strip()
    cuisines_exploded = cuisines_exploded[["cuisine"]].reset_index()

    # Some source rows list the same cuisine twice within one restaurant's
    # cuisines string (e.g. "North Indian, Fast Food, Fast Food") — this is
    # a source data quality issue, not a bug in our splitting logic. Drop
    # exact duplicate (restaurant, cuisine) pairs before loading, since the
    # DB's primary key correctly rejects them otherwise.
    before = len(cuisines_exploded)
    cuisines_exploded = cuisines_exploded.drop_duplicates(subset=["restaurant_id", "cuisine"])
    if before != len(cuisines_exploded):
        print(f"Dropped {before - len(cuisines_exploded)} duplicate "
              f"(restaurant, cuisine) pairs from source data.")

    return restaurants.reset_index(), cuisines_exploded


def load_to_postgres(restaurants: pd.DataFrame, cuisines: pd.DataFrame):
    engine = create_engine(db_config.url)

    # restaurant_id here is the pandas index+1 to match SERIAL starting at 1
    restaurants_to_load = restaurants.rename(columns={"restaurant_id": "restaurant_id"})
    restaurants_to_load["restaurant_id"] = restaurants_to_load["restaurant_id"] + 1
    cuisines_to_load = cuisines.copy()
    cuisines_to_load["restaurant_id"] = cuisines_to_load["restaurant_id"] + 1

    restaurants_to_load.to_sql(
        "restaurants", engine, if_exists="append", index=False, method="multi", chunksize=500
    )
    cuisines_to_load.to_sql(
        "restaurant_cuisines", engine, if_exists="append", index=False, method="multi", chunksize=500
    )
    print(f"Loaded {len(restaurants_to_load)} restaurants and "
          f"{len(cuisines_to_load)} restaurant-cuisine pairs into PostgreSQL.")


if __name__ == "__main__":
    restaurants_df, cuisines_df = load_and_clean(RAW_PATH)
    print(restaurants_df.head())
    print(cuisines_df.head())
    load_to_postgres(restaurants_df, cuisines_df)