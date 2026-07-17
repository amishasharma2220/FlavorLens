# Architecture

This document explains how FlavorLens is put together and, more importantly, *why*. If something in the code looks like an odd choice, check here first — there's usually a reason.

## The core idea

FlavorLens turns raw restaurant data into a single, explainable number — the **Cuisine Opportunity Index (COI)** — that tells someone whether a given cuisine looks like a good bet in a given locality. Everything here supports one rule:

> **Code computes. The LLM explains. Those roles never swap.**

## System layers

```
┌─────────────────────────────────────────────────────────┐
│  Raw data — python/data/raw/ (gitignored, never committed)│
└──────────────────────────┬────────────────────────────────┘
                            │  python/notebooks/01_inspect.py
                            │  python/db/load_data.py (cleaning + load)
                            ▼
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL — restaurants, localities tables               │
└──────────────────────────┬────────────────────────────────┘
                            │  python/analytics/queries.py
                            ▼
┌─────────────────────────────────────────────────────────┐
│  python/analytics/coi_calculator.py                       │
│  normalization, weighting, COI + confidence scoring       │
└──────────────────────────┬────────────────────────────────┘
                            │  scored DataFrame / coi_results table
                            ▼
┌─────────────────────────────────────────────────────────┐
│  streamlit/app.py — charts, tables, filters                │
└──────────────────────────┬────────────────────────────────┘
                            │  computed metrics only, no raw text
                            ▼
┌─────────────────────────────────────────────────────────┐
│  python/llm/copilot.py — Expansion Copilot                │
│  explains the numbers, never calculates them               │
└─────────────────────────────────────────────────────────┘
```

## Repo layout

```
FlavorLens/
├── python/
│   ├── data/
│   │   ├── raw/            # gitignored — never committed
│   │   └── processed/      # gitignored (CSVs) — cleaned intermediates
│   ├── db/
│   │   ├── schema.sql
│   │   └── load_data.py
│   ├── analytics/
│   │   ├── queries.py          # SQL retrieval, no COI math here
│   │   └── coi_calculator.py   # normalization + weighted COI, pure functions
│   ├── llm/
│   │   └── copilot.py          # prompt construction, numbers-only context
│   └── notebooks/
│       └── 01_inspect.py       # exploration, run before writing cleaning code
├── streamlit/
│   └── app.py
├── config.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── ARCHITECTURE.md
├── FLOWS.md
└── AGENTS.md
```

## Why each piece exists

**PostgreSQL, not just CSVs in pandas.** Once you're joining restaurant data against locality data and running repeated aggregations, a database earns its keep — and it's a more honest picture of a real analytics stack than re-reading the same CSV every run.

**SQL retrieves, Python computes.** `python/analytics/queries.py` groups, filters, and joins. It never computes the COI — that logic lives in `coi_calculator.py`, where it's testable and versioned instead of buried in a query string.

**Every component score is normalized to 0–100 before combining.** A rating (0–5) and a restaurant count (0–300) can't be averaged directly. Normalize first, then apply weights.

**The LLM sits at the very end and sees only numbers.** `python/llm/copilot.py` is deliberately the last step. It receives a small, fixed set of already-computed values and is explicitly instructed not to introduce numbers of its own — this is what makes "the LLM never calculates" true in code, not just in the pitch.

## Data scope (disclosed, not hidden)

**v1 scope: Bangalore, by locality**, using the Zomato Bangalore Restaurants dataset (Kaggle). Not multiple cities — the dataset doesn't support that yet, and the README should say so plainly rather than imply broader coverage.

**No fabricated data, ever.** If a locality/cuisine combination has too little data to score confidently, the system reflects that with a low confidence score — it does not invent rows to fill gaps. If growth data (e.g. `established_year`) isn't reliably available, growth is either dropped from v1's COI or replaced with a clearly-labeled proxy (e.g. votes as an engagement signal) — never synthetic history.

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Storage | PostgreSQL | Relational joins, real SQL practice |
| Data loading | pandas + SQLAlchemy | Easy to inspect mid-pipeline |
| Analytics | pandas / numpy | Normalization, weighted scoring, reproducible |
| App | Streamlit | Fast to build, portfolio-appropriate |
| Explanation layer | Anthropic API | Turns computed metrics into plain-language reasoning |

## What this is not

Not a scraping pipeline — no live Zomato/Swiggy API calls, since neither offers public access anymore. Not a forecasting tool — the COI reflects current opportunity from current data, it doesn't predict the future. Both worth saying out loud if asked.