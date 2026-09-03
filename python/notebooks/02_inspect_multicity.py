"""
Phase 1b — Multi-City Dataset Inspection
-------------------------------------------
Run this before writing any cleaning/merge code for the multi-city
expansion. We don't know this dataset's exact column names or per-city
data quality yet — same discipline as the original Bangalore inspection.

Usage:
    python python/notebooks/02_inspect_multicity.py
"""

import pandas as pd

RAW_PATH = "python/data/raw/zomato_multicity.csv"  # adjust to your actual filename


def main():
    df = pd.read_csv(RAW_PATH)

    print("=" * 60)
    print("SHAPE")
    print("=" * 60)
    print(df.shape)

    print("\n" + "=" * 60)
    print("COLUMNS & DTYPES")
    print("=" * 60)
    print(df.dtypes)

    print("\n" + "=" * 60)
    print("NULL COUNTS")
    print("=" * 60)
    print(df.isnull().sum().sort_values(ascending=False))

    print("\n" + "=" * 60)
    print("SAMPLE ROWS")
    print("=" * 60)
    print(df.sample(5, random_state=42))

    # --- City coverage — the key question for scoping v2 ---
    city_col_candidates = [c for c in df.columns if "city" in c.lower()]
    print("\n" + "=" * 60)
    print(f"CANDIDATE CITY COLUMNS: {city_col_candidates}")
    print("=" * 60)

    for col in city_col_candidates:
        print(f"\n--- Restaurant count by '{col}' (top 20) ---")
        print(df[col].value_counts().head(20))

    # --- Check for a Bangalore entry, since we need to compare against
    #     the existing single-city dataset for consistency ---
    if city_col_candidates:
        city_col = city_col_candidates[0]
        print("\n" + "=" * 60)
        print(f"Rows matching 'Bangalore' or 'Bengaluru' in '{city_col}'")
        print("=" * 60)
        mask = df[city_col].astype(str).str.contains("bangalore|bengaluru", case=False, na=False)
        print(f"Count: {mask.sum()}")

    # --- Same checks as the original inspection, since cleaning needs
    #     to handle whatever format this dataset actually uses ---
    for candidate in ["rate", "rating", "aggregate_rating"]:
        if candidate in df.columns:
            print(f"\n--- '{candidate}' column — distinct raw values (first 20) ---")
            print(df[candidate].unique()[:20])

    for candidate in ["cuisines", "cuisine"]:
        if candidate in df.columns:
            print(f"\n--- '{candidate}' — distinct count and sample ---")
            print(f"Distinct raw strings: {df[candidate].nunique()}")
            print(df[candidate].dropna().unique()[:15])

    for candidate in ["cost", "approx_cost(for two people)", "average_cost_for_two", "avg_cost"]:
        if candidate in df.columns:
            print(f"\n--- '{candidate}' — sample raw values ---")
            print(df[candidate].dropna().unique()[:15])

    print("\n" + "=" * 60)
    print("DONE — read the output above before writing any cleaning/merge code.")
    print("=" * 60)


if __name__ == "__main__":
    main()