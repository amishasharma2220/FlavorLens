# FlavorLens 🍽️

### Restaurant Expansion Intelligence Platform (v1 scope: Bangalore, by locality)

> Helping restaurant owners and food businesses evaluate cuisine opportunities in Bangalore using data instead of guesswork.

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for system design and [`FLOWS.md`](./FLOWS.md) for how data and users move through the app.

---

## Problem Statement

Opening a restaurant in the wrong locality or choosing an oversaturated cuisine is one of the more avoidable causes of restaurant failure. FlavorLens replaces intuition with evidence — combining restaurant data, SQL analytics, and LLM-assisted explanations to help answer:

**"Which cuisine has real opportunity in this locality, and why?"**

---

## Architecture

```
Zomato Bangalore Restaurants dataset (Kaggle)
            │
            ▼
    Data Cleaning Pipeline (Python/Pandas)
            │
            ▼
      PostgreSQL Database
            │
            ▼
    SQL Analytics Layer (locality/cuisine aggregation)
            │
            ▼
   Python Processing (COI scoring, confidence)
            │
            ▼
      Streamlit Web App
            │
            ▼
       Expansion Copilot
       (Groq / Llama 3.1 — explains pre-computed metrics only, never calculates)
```

---

## Tech Stack

| Layer | Tools |
|---|---|
| Storage | PostgreSQL |
| Processing | Python, Pandas, NumPy |
| Analytics | SQL |
| Frontend | Streamlit, Plotly |
| LLM | Groq API (Llama 3.1) — free tier, no billing required |
| Deployment | Streamlit Community Cloud |

*Note: Groq's free API (Llama 3.1) is used instead of a paid provider — it keeps the project fully reproducible without requiring anyone (including graders or interviewers testing it) to add billing to run it.*

---

## Core Features

### Cuisine Opportunity Index (COI)

A composite score built from four independently calculated components:

- **Demand Score** — average customer engagement (votes) per restaurant
- **Competition Score** — restaurant density for the cuisine in a locality, inverted so lower competition scores higher
- **Affordability Score** — how much cheaper a cuisine is than the locality's own average cost
- **Rating Stability** — consistency of customer ratings (inverted standard deviation)

Default weights live in `config.py` and are documented there with the reasoning behind each. They're also adjustable live via sliders in the Streamlit app — the defaults are starting assumptions, not derived ground truth. Every score includes a **Confidence Rating** based on rated-restaurant count and review volume, so a high COI backed by little data reads differently than one backed by a lot.

*Growth is not included as a COI component — the dataset doesn't include reliable historical/establishment-date data. Its configured weight is redistributed proportionally across the other four components rather than left as a gap or faked with a proxy metric. See `ARCHITECTURE.md` for details.*

### Expansion Copilot

An LLM-assisted explanation layer, not a chatbot, powered by Groq (Llama 3.1). The model receives only pre-calculated metrics and generates a plain-language explanation. **It never calculates — it only explains.**

---

## Data Sources

| Source | Purpose |
|---|---|
| Zomato Bangalore Restaurants dataset (Kaggle) | Restaurant metadata, ratings, cuisine, cost, locality |

No live scraping — Zomato and Swiggy no longer offer public data access, so this project uses a static, disclosed snapshot rather than pretending otherwise.

---

## Known Limitations

- Single city (Bangalore), by locality — not a multi-city platform yet
- Dataset is a snapshot, not live — trend claims are not supported by v1
- No historical/growth data — growth is omitted rather than fabricated or proxied
- COI weights are documented business assumptions, not derived ground truth — adjustable in the app, open to revision as the methodology matures
- No synthetic or filler data is ever used for sparse localities; low coverage shows up as low confidence instead
- The source dataset had a known duplicate-listing issue (same restaurant listed once per order type); this was deduplicated during cleaning — see `python/db/load_data.py`

---

## Project Roadmap

- [x] Project structure and configuration
- [x] Data cleaning pipeline
- [x] PostgreSQL schema and data load
- [x] SQL analytics layer
- [x] COI implementation
- [x] Streamlit dashboard
- [x] Expansion Copilot
- [ ] Deployment

---

## Local Setup

```bash
git clone https://github.com/amishasharma2220/FlavorLens.git
cd FlavorLens
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # fill in your DB credentials and GROQ_API_KEY
streamlit run streamlit/app.py
```

Requires a running PostgreSQL instance (see `python/db/schema.sql` for the schema) and a free Groq API key from [console.groq.com](https://console.groq.com) for the Expansion Copilot feature — the rest of the app works fully without it.

---

*Built by Amisha Sharma · B.Tech CSE · Manipal University Jaipur*