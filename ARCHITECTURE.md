# Architecture

This document explains how FlavorLens is put together and, more importantly, *why*. If something in the code looks like an odd choice, check here first — there's usually a reason.

## The core idea

FlavorLens turns raw restaurant data into a single, explainable number — the **Cuisine Opportunity Index (COI)** — that tells someone whether a given cuisine looks like a good bet in a given locality of a given city. Everything here supports one rule:

> **Code computes. The LLM explains. Those roles never swap.**

## System layers

```
┌──────────────────────────────────────────────────────────────┐
│  Raw data — python/data/raw/ (gitignored, never committed)    │
│  zomato.csv (Bangalore) + Zomato API JSON dump (NCR cities)   │
└───────────────────────────┬──────────────────────────────────┘
                            │  python/notebooks/04, 05 — flatten JSON
                            │    → python/data/processed/zomato_global_flat.csv
                            │  python/db/load_data.py — clean, tag city,
                            │    standardize localities, split cuisines
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  PostgreSQL — restaurants, restaurant_cuisines                │
└───────────────────────────┬──────────────────────────────────┘
                            │  python/analytics/queries.py (SQL aggregates only)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  python/analytics/coi_calculator.py                           │
│  within-city normalization, weighting, COI + confidence       │
└───────────────────────────┬──────────────────────────────────┘
                            │  scored DataFrame (cached in the app for 1 hour)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  streamlit/app.py — filters, tables, charts, evidence filter  │
└───────────────────────────┬──────────────────────────────────┘
                            │  one row's computed metrics, on button click
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  python/llm/copilot.py — Expansion Copilot (Groq, Llama 3.1)  │
│  explains the numbers, never calculates them                  │
└──────────────────────────────────────────────────────────────┘
```

## Repo layout

```
FlavorLens/
├── python/
│   ├── data/
│   │   ├── raw/            # gitignored — never committed
│   │   └── processed/      # gitignored — flattened API data
│   ├── db/
│   │   ├── schema.sql          # restaurants + restaurant_cuisines, city-tagged
│   │   └── load_data.py        # cleaning + locality standardization + load
│   ├── analytics/
│   │   ├── queries.py          # SQL retrieval, no COI math here
│   │   └── coi_calculator.py   # normalization + weighted COI, pure functions
│   ├── llm/
│   │   └── copilot.py          # prompt construction, numbers-only context
│   └── notebooks/
│       ├── 01_inspect.py                 # Bangalore source exploration
│       ├── 02_inspect_multicity.py       # evaluated and rejected delivery dataset
│       ├── 04_inspect_json_structure.py  # Zomato API JSON structure
│       └── 05_parse_json_and_inspect.py  # flattens JSON → processed CSV
├── streamlit/
│   └── app.py
├── tests/
│   ├── test_coi_calculator.py
│   └── test_load_data.py
├── config.py
├── requirements.txt
├── .env.example
├── README.md
├── ARCHITECTURE.md
├── FLOWS.md
└── AGENTS.md
```

## Why each piece exists

**PostgreSQL, not just CSVs in pandas.** Once you're joining restaurants to cuisines and running repeated aggregations per city and locality, a database earns its keep, and it's a more honest picture of a real analytics stack than re-reading the same CSV every run. Production runs on Neon; local development can use any Postgres.

**Every row is tagged with its city.** Locality names collide across cities ("Sector 15" exists in Noida and Faridabad; "MG Road" in Bangalore and Gurgaon). Every query groups by `(city, locality)`, never by locality alone.

**Venue labels are collapsed to their area at load time.** The API source often names a mall or hotel instead of an area. Doing this in `load_data.py` (not in SQL or the app) keeps one cleaned truth in the database. The rule is deliberately simple and tested: last comma-separated part, trailing city names dropped, "Greater Noida" protected, plus a short explicit list of verified spelling merges. No fuzzy matching: a wrong merge is harder to notice than a missed one.

**SQL retrieves, Python computes.** `queries.py` groups, filters and joins. It never computes the COI — that lives in `coi_calculator.py`, where it is unit-tested and versioned instead of buried in a query string.

**Every component is normalized to 0–100 within its own city before combining.** A rating (0–5) and a restaurant count (0–300) can't be averaged directly, so each is scaled first. Scaling happens per city because the cities are very different sizes (Bangalore ~12,500 restaurants, Noida ~1,100). A global scale would make a strong Noida opportunity structurally harder to score highly.

**Missing values get a neutral fill, never zero.** Missing cost and single-restaurant rating spread are filled with that city's median. A group where every value is identical scores a neutral 50 rather than dividing by zero.

**Confidence is derived, not asserted.** It averages two capped ratios: rated restaurants vs. 10, and total votes vs. 50 (thresholds in `config.py`).

**The app adds an evidence filter on top of confidence.** Confidence alone lets a single well-reviewed restaurant reach 55%, so the app also hides cuisines with fewer than N restaurants in the locality (default 2, adjustable). The data isn't changed — the filter is presentation only, and the table says how many rows it hid.

**The LLM sits at the very end, is opt-in, and sees only numbers.** `copilot.py` receives one row's already-computed values plus city, locality and cuisine names, and is instructed not to introduce numbers of its own. It runs only when the user clicks "Explain this opportunity", results are cached per input, and any failure (no key, timeout, API error) returns a fallback message instead of breaking the page.

## Data scope (disclosed, not hidden)

**v2 scope: Bangalore, New Delhi, Gurgaon, Noida, by locality.** Bangalore comes from the Zomato Bangalore Kaggle dataset; the NCR cities from a Kaggle dump of raw Zomato API responses. The two sources were collected differently and at different times, so cross-city comparisons are indicative only — another reason scores are scaled within each city.

**No fabricated data, ever.** If a locality/cuisine combination has too little data, the system shows low confidence or hides it behind the evidence filter — it does not invent rows. There is no reliable growth or establishment-date field, so growth is dropped from the COI and its weight redistributed rather than replaced by a synthetic history.

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Storage | PostgreSQL (Neon) | Relational joins, real SQL practice, free hosted tier |
| Data loading | pandas + SQLAlchemy | Easy to inspect mid-pipeline |
| Analytics | pandas / numpy | Normalization, weighted scoring, reproducible |
| App | Streamlit + Plotly | Fast to build, free hosting on Community Cloud |
| Explanation layer | Groq API (Llama 3.1 8B, via the `openai` SDK) | Free tier, no billing needed to reproduce |
| Tests | pytest | COI math and cleaning helpers, no database needed |

## What this is not

Not a scraping pipeline — no live Zomato/Swiggy API calls, since neither offers public access anymore. Not a forecasting tool — the COI reflects opportunity in a static snapshot; it doesn't predict the future. Not validated against outcomes — there's no data on which restaurants succeeded. All worth saying out loud if asked.
