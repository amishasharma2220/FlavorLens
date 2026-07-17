"""
Phase 1 — Data Inspection
--------------------------
Run this before writing ANY cleaning code. The goal is to actually look at
what's in the dataset — nulls, weird values, distinct counts — rather than
assume it's clean. Zomato's raw export is known to be messy (ratings like
"4.1/5", "NEW", "-"; costs formatted as "1,200" strings; multi-cuisine
strings that need splitting).

Usage:
    python python/notebooks/01_inspect.py
"""

import pandas as pd

RAW_PATH = "python/data/raw/zomato.csv"  # adjust to your actual filename


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

    # --- Column-specific checks worth doing by hand ---

    if "rate" in df.columns:
        print("\n" + "=" * 60)
        print("RATE COLUMN — distinct raw values (first 20)")
        print("=" * 60)
        print(df["rate"].unique()[:20])
        # Expect junk like "NEW", "-", "4.1/5" here.

    if "cuisines" in df.columns:
        print("\n" + "=" * 60)
        print("CUISINES — distinct count and sample")
        print("=" * 60)
        print(f"Distinct raw cuisine strings: {df['cuisines'].nunique()}")
        print(df["cuisines"].dropna().unique()[:15])
        # These are typically comma-separated multi-cuisine strings.
        # e.g. "North Indian, Chinese" — will need splitting into rows
        # before you can group by a single cuisine.

    if "location" in df.columns:
        print("\n" + "=" * 60)
        print("LOCATION — distinct localities")
        print("=" * 60)
        print(f"Distinct localities: {df['location'].nunique()}")
        print(df["location"].value_counts().head(15))
        # Watch for near-duplicates like "BTM" vs "BTM Layout" —
        # these need standardizing or your locality-level grouping
        # will silently split real localities into fake separate ones.

    cost_col = "approx_cost(for two people)"
    if cost_col in df.columns:
        print("\n" + "=" * 60)
        print("COST COLUMN — sample raw values")
        print("=" * 60)
        print(df[cost_col].dropna().unique()[:15])
        # Expect comma-formatted strings like "1,200" — needs stripping
        # before it can be cast to numeric.

    print("\n" + "=" * 60)
    print("DONE — read the output above before writing any cleaning code.")
    print("=" * 60)


if __name__ == "__main__":
    main()