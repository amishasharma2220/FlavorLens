# FlavorLens 🍽️
### Restaurant Expansion Intelligence Platform

> Helping restaurant owners, investors, and food businesses make data-driven expansion decisions across Indian cities.

---

## Problem Statement

Opening a restaurant in the wrong city or choosing an oversaturated cuisine is one of the most common causes of restaurant failure. FlavorLens replaces intuition with evidence — combining multi-source restaurant data, SQL analytics, and LLM-assisted explanations to answer the question every restaurateur asks:

**"Where should I open, what should I serve, and why?"**

---

## Architecture

```
Public Datasets (Zomato, Swiggy, Census)
            │
            ▼
    Data Cleaning Pipeline (Python/Pandas)
            │
            ▼
      PostgreSQL Database
            │
            ▼
    SQL Analytics Layer (domain-grouped queries)
            │
            ▼
   Python Processing (COI scoring, confidence)
            │
         ┌──┴──┐
         ▼     ▼
     Power BI  Streamlit Web App
               │
               ▼
       Expansion Copilot
       (LLM explains SQL-derived metrics only)
```

---

## Tech Stack

| Layer | Tools |
|---|---|
| Storage | PostgreSQL |
| Processing | Python, Pandas, NumPy |
| Analytics | SQL |
| Frontend | Streamlit, Plotly |
| BI Dashboard | Power BI |
| LLM | Claude API (Anthropic) |
| Deployment | Streamlit Cloud |

---

## Core Features

### Cuisine Opportunity Index (COI)
A composite score built from five independently calculated components:
- **Demand Score** — review volume and growth signals
- **Competition Score** — restaurant density for the cuisine
- **Growth Score** — rating trajectory over time
- **Rating Stability** — consistency of customer satisfaction
- **Affordability Index** — price positioning vs. city average

Weights are configurable via Streamlit sliders. Every score includes a **Confidence Rating** that drops when data is sparse.

### Expansion Copilot
An LLM-assisted explanation engine (not a chatbot). The model is given only pre-calculated metrics and generates natural-language business recommendations. **The LLM never calculates — it only explains.**

### Restaurant Launch Simulator
Input: City + Cuisine + Price Segment → Output: Full COI breakdown, competitor analysis, recommended locality, and evidence cards.

---

## Data Sources

| Source | Purpose |
|---|---|
| Zomato Kaggle Dataset | Restaurant metadata, ratings, cuisine |
| Swiggy Dataset | Delivery coverage, additional restaurants |
| Census of India | City population for density normalization |

*Architecture supports additional sources without schema redesign.*

---

## COI Methodology

See the **Methodology** page in the Streamlit app for a full explanation of each component, the confidence scoring system, and known limitations.

---

## Known Limitations

- Dataset is a snapshot, not live data — trend analysis is indicative, not real-time
- Review text availability varies by source
- Synthetic data used for cities with sparse coverage (clearly labeled)
- COI weights are business assumptions — users are encouraged to adjust them

---

## Project Roadmap

- [x] Project structure and configuration
- [ ] Data cleaning pipeline
- [ ] PostgreSQL schema and data load
- [ ] SQL analytics layer
- [ ] COI implementation
- [ ] Streamlit dashboard
- [ ] Expansion Copilot
- [ ] Power BI dashboard
- [ ] Deployment

---

## Local Setup

```bash
git clone https://github.com/yourusername/FlavorLens.git
cd FlavorLens
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Fill in your credentials
streamlit run streamlit/app.py
```

---

*Built by Amisha Sharma · B.Tech CSE · Manipal University Jaipur*
