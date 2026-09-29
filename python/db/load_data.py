"""
FlavorLens — Data Cleaning + Load (v2 — multi-city)
------------------------------------------------------
Combines two source datasets, cleaned into a common schema, then loaded
into PostgreSQL:
  1. Bangalore — Zomato Bangalore Restaurants (Kaggle), single-city CSV
  2. New Delhi / Gurgaon / Noida — flattened from the global Zomato API
     JSON dump (python/notebooks/05_parse_json_and_inspect.py produces
     python/data/processed/zomato_global_flat.csv — run that script first)

Every restaurant is tagged with its `city` explicitly — see schema.sql
for why this matters (locality names collide across cities, e.g.
"Sector 15" exists in both Noida and Faridabad).

Run schema.sql against your database first, then:
    python python/db/load_data.py
"""

import pandas as pd
from sqlalchemy import create_engine

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config import db_config

BANGALORE_RAW_PATH = "python/data/raw/zomato.csv"
MULTICITY_FLAT_PATH = "python/data/processed/zomato_global_flat.csv"

# Cities included from the global dataset — chosen based on actual
# locality diversity, not just raw restaurant count. Faridabad (251
# restaurants, 40 localities) was considered and excluded: thinner
# coverage per locality than these three. See ARCHITECTURE.md.
MULTICITY_CITIES = ["New Delhi", "Gurgaon", "Noida"]


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
    """'Yes'/'No' -> True/False (Bangalore source)."""
    if pd.isna(value):
        return None
    return str(value).strip().lower() == "yes"


def clean_multicity_rating(value):
    """
    aggregate_rating of 0 means unrated (no reviews yet) in this source,
    same principle as Bangalore's 'NEW' — missing, not a bad score.
    """
    try:
        val = float(value)
    except (ValueError, TypeError):
        return None
    return None if val == 0 else val


def load_and_clean_bangalore(raw_path: str) -> pd.DataFrame:
    """Cleans the original Bangalore CSV into the common intermediate schema."""
    df = pd.read_csv(raw_path)

    df = df.drop(
        columns=["url", "phone", "dish_liked", "reviews_list", "menu_item", "listed_in(city)"],
        errors="ignore",
    )

    before = len(df)
    df = df.drop_duplicates(subset=["name", "address"], keep="first")
    print(f"[Bangalore] Deduplicated: {before} -> {len(df)} rows "
          f"({before - len(df)} duplicate listings removed)")

    df["rating"] = df["rate"].apply(clean_rate)
    df["approx_cost_for_two"] = df["approx_cost(for two people)"].apply(clean_cost)
    df["online_order"] = df["online_order"].apply(clean_boolean_yes_no)
    df["book_table"] = df["book_table"].apply(clean_boolean_yes_no)
    df["city"] = "Bangalore"

    df = df.dropna(subset=["location", "cuisines"])

    return df[[
        "name", "address", "city", "location", "rest_type",
        "approx_cost_for_two", "rating", "votes",
        "online_order", "book_table", "cuisines",
    ]]


def load_and_clean_multicity(flat_path: str, cities: list) -> pd.DataFrame:
    """Cleans the flattened global-JSON dataset, filtered to the chosen cities."""
    df = pd.read_csv(flat_path)
    df = df[df["city"].isin(cities)].copy()

    before = len(df)
    df = df.drop_duplicates(subset=["name", "address"], keep="first")
    print(f"[Multi-city] Deduplicated: {before} -> {len(df)} rows "
          f"({before - len(df)} duplicate listings removed)")

    df["rating"] = df["aggregate_rating"].apply(clean_multicity_rating)
    df["approx_cost_for_two"] = df["average_cost_for_two"].apply(clean_cost)
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
    df["online_order"] = df["has_online_delivery"].apply(lambda v: bool(v) if pd.notna(v) else None)
    df["book_table"] = df["has_table_booking"].apply(lambda v: bool(v) if pd.notna(v) else None)
    df["location"] = df["locality"]
    # rest_type isn't available in this source — left as None (disclosed
    # in schema.sql's column comment), never fabricated.
    df["rest_type"] = None

    df = df.dropna(subset=["location", "cuisines"])

    return df[[
        "name", "address", "city", "location", "rest_type",
        "approx_cost_for_two", "rating", "votes",
        "online_order", "book_table", "cuisines",
    ]]


def explode_cuisines(df: pd.DataFrame):
    """Splits the combined cleaned DataFrame into restaurants + restaurant_cuisines."""
    df = df.reset_index(drop=True)
    restaurants = df.drop(columns=["cuisines"]).reset_index()
    restaurants = restaurants.rename(columns={"index": "restaurant_id"})

    cuisines_df = df[["cuisines"]].reset_index()
    cuisines_df = cuisines_df.rename(columns={"index": "restaurant_id"})
    cuisines_df["cuisine"] = cuisines_df["cuisines"].str.split(",")
    cuisines_exploded = cuisines_df.explode("cuisine")
    cuisines_exploded["cuisine"] = cuisines_exploded["cuisine"].str.strip()
    cuisines_exploded = cuisines_exploded[["restaurant_id", "cuisine"]]

    before = len(cuisines_exploded)
    cuisines_exploded = cuisines_exploded.drop_duplicates(subset=["restaurant_id", "cuisine"])
    if before != len(cuisines_exploded):
        print(f"Dropped {before - len(cuisines_exploded)} duplicate "
              f"(restaurant, cuisine) pairs from source data.")

    return restaurants, cuisines_exploded


def load_to_postgres(restaurants: pd.DataFrame, cuisines: pd.DataFrame):
    engine = create_engine(db_config.url)

    restaurants_to_load = restaurants.copy()
    restaurants_to_load["restaurant_id"] = restaurants_to_load["restaurant_id"] + 1
    cuisines_to_load = cuisines.copy()
    cuisines_to_load["restaurant_id"] = cuisines_to_load["restaurant_id"] + 1

    restaurants_to_load.to_sql(
        "restaurants", engine, if_exists="append", index=False, method="multi", chunksize=500
    )
    cuisines_to_load.to_sql(
        "restaurant_cuisines", engine, if_exists="append", index=False, method="multi", chunksize=500
    )
    print(f"\nLoaded {len(restaurants_to_load)} restaurants and "
          f"{len(cuisines_to_load)} restaurant-cuisine pairs into PostgreSQL.")


if __name__ == "__main__":
    bangalore = load_and_clean_bangalore(BANGALORE_RAW_PATH)
    multicity = load_and_clean_multicity(MULTICITY_FLAT_PATH, MULTICITY_CITIES)

    print(f"\nBangalore: {len(bangalore)} restaurants")
    print(f"Multi-city ({', '.join(MULTICITY_CITIES)}): {len(multicity)} restaurants")

    combined = pd.concat([bangalore, multicity], ignore_index=True)
    print(f"\nCombined total: {len(combined)} restaurants")
    print("\nRestaurants per city:")
    print(combined["city"].value_counts())

    restaurants_df, cuisines_df = explode_cuisines(combined)
    load_to_postgres(restaurants_df, cuisines_df)