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
       (LLM explains pre-computed metrics only — never calculates)
```

---

## Tech Stack

| Layer | Tools |
|---|---|
| Storage | PostgreSQL |
| Processing | Python, Pandas, NumPy |
| Analytics | SQL |
| Frontend | Streamlit, Plotly |
| LLM | Claude API (Anthropic) |
| Deployment | Streamlit Community Cloud |

---

## Core Features

### Cuisine Opportunity Index (COI)

A composite score built from independently calculated components:

- **Demand Score** — review volume and rating signals
- **Competition Score** — restaurant density for the cuisine in a locality
- **Rating Stability** — consistency of customer ratings
- **Affordability Index** — price positioning vs. locality average

Default weights live in `config.py` and are documented there with the reasoning behind each. Every score includes a **Confidence Rating** that drops when data is sparse — it does not get papered over with filler data.

*Growth is not currently included as a COI component — the dataset doesn't include reliable historical/establishment-date data. If a growth signal is added later, it will be clearly labeled as a proxy (e.g. votes as an engagement signal), not framed as true trend data.*

### Expansion Copilot

An LLM-assisted explanation layer, not a chatbot. The model receives only pre-calculated metrics and generates a plain-language explanation. **It never calculates — it only explains.**

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
- No historical/growth data — growth is omitted or explicitly proxied, never fabricated
- COI weights are documented business assumptions, not derived ground truth — open to revision as the methodology matures
- No synthetic or filler data is ever used for sparse localities; low coverage shows up as low confidence instead

---

## Project Roadmap

- [x] Project structure and configuration
- [ ] Data cleaning pipeline
- [ ] PostgreSQL schema and data load
- [x] SQL analytics layer
- [x] COI implementation
- [ ] Streamlit dashboard
- [ ] Expansion Copilot
- [ ] Deployment

---

## Local Setup

```bash
git clone https://github.com/amishasharma2220/FlavorLens.git
cd FlavorLens
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # fill in your credentials
streamlit run streamlit/app.py
```

---

*Built by Amisha Sharma · B.Tech CSE · Manipal University Jaipur*