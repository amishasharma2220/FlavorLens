"""
Phase 1c — Flatten raw Zomato JSON dump + inspect city coverage
--------------------------------------------------------------------
Parses file1.json through file5.json (raw Zomato API dumps), flattens
the nested restaurant records into a flat table matching (as closely as
possible) the shape of the original Bangalore CSV, filters to India, and
reports restaurant counts per city so we can pick 2-3 cities with real
depth for the multi-city expansion.

Saves the flattened result to python/data/processed/zomato_global_flat.csv
so we don't have to re-parse the raw JSON every time.

Usage:
    python python/notebooks/05_parse_json_and_inspect.py
"""

import json
import glob
import pandas as pd

RAW_DIR = "python/data/raw/archive"
OUTPUT_PATH = "python/data/processed/zomato_global_flat.csv"
INDIA_COUNTRY_ID = 1  # confirmed from inspected JSON structure


def parse_file(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = []
    for entry in data:
        for r in entry.get("restaurants", []):
            rest = r.get("restaurant", {})
            loc = rest.get("location", {})
            rating = rest.get("user_rating", {})

            records.append({
                "name": rest.get("name"),
                "cuisines": rest.get("cuisines"),
                "average_cost_for_two": rest.get("average_cost_for_two"),
                "price_range": rest.get("price_range"),
                "has_online_delivery": rest.get("has_online_delivery"),
                "has_table_booking": rest.get("has_table_booking"),
                "votes": rating.get("votes"),
                "aggregate_rating": rating.get("aggregate_rating"),
                "city": loc.get("city"),
                "locality": loc.get("locality"),
                "address": loc.get("address"),
                "country_id": loc.get("country_id"),
            })
    return records


def main():
    all_records = []
    files = sorted(glob.glob(f"{RAW_DIR}/file*.json"))
    print(f"Found {len(files)} JSON files: {files}")

    for path in files:
        recs = parse_file(path)
        print(f"  {path}: {len(recs)} restaurant records")
        all_records.extend(recs)

    df = pd.DataFrame(all_records)
    print(f"\nTotal records across all files (all countries): {len(df)}")

    before = len(df)
    df = df.drop_duplicates(subset=["name", "address"])
    print(f"After deduplication: {len(df)} ({before - len(df)} duplicates removed)")

    india_df = df[df["country_id"] == INDIA_COUNTRY_ID].copy()
    print(f"\nIndia-only records: {len(india_df)}")

    print("\n" + "=" * 60)
    print("RESTAURANT COUNT BY CITY (India, top 20)")
    print("=" * 60)
    print(india_df["city"].value_counts().head(20))

    print("\n" + "=" * 60)
    print("NULL COUNTS (India only)")
    print("=" * 60)
    print(india_df.isnull().sum().sort_values(ascending=False))

    print("\n" + "=" * 60)
    print("SAMPLE ROWS")
    print("=" * 60)
    print(india_df.sample(min(5, len(india_df)), random_state=42))

    print("\n" + "=" * 60)
    print("LOCALITY DIVERSITY — TOP CANDIDATE CITIES")
    print("=" * 60)
    for city in ["New Delhi", "Gurgaon", "Noida", "Faridabad"]:
        city_df = india_df[india_df["city"] == city]
        if len(city_df) == 0:
            continue
        n_localities = city_df["locality"].nunique()
        print(f"\n{city}: {len(city_df)} restaurants across {n_localities} distinct localities")
        print(city_df["locality"].value_counts().head(10))

    india_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved flattened India-only data to {OUTPUT_PATH}")
    print("\n" + "=" * 60)
    print("DONE — pick 2-3 cities with strong counts above before proceeding.")
    print("=" * 60)


if __name__ == "__main__":
    main()