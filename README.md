# FlavorLens 🍽️

### Restaurant Expansion Intelligence Platform (v2 scope: Bangalore, New Delhi, Gurgaon, Noida, by locality)

> Helping restaurant owners and food businesses evaluate cuisine opportunities by locality using data instead of guesswork.

**[Live demo](https://flavorlens-4uyeebubdu4u674bz8rtro.streamlit.app/)** · See [`ARCHITECTURE.md`](ARCHITECTURE.md) for system design and [`FLOWS.md`](FLOWS.md) for how data and users move through the app.

---

## Problem Statement

Opening a restaurant in the wrong locality or choosing an oversaturated cuisine is one of the more avoidable causes of restaurant failure. FlavorLens replaces intuition with evidence: restaurant data, SQL analytics, and an LLM layer that explains the computed numbers, to help answer:

**"Which cuisine has real opportunity in this locality, and why?"**

---

## Architecture

```
Zomato Bangalore CSV (Kaggle)      Zomato API JSON dump (Kaggle)
            │                       flattened, filtered to
            │                       New Delhi / Gurgaon / Noida
            └──────────┬────────────┘
                       ▼
   Data Cleaning Pipeline (Python/Pandas)
   dedupe, parse ratings/costs, tag city,
   collapse venue labels to their area, split cuisines
                       │
                       ▼
             PostgreSQL (Neon)
                       │
                       ▼
   SQL Analytics Layer (city/locality/cuisine aggregation)
                       │
                       ▼
   Python Processing (COI scoring within each city, confidence)
                       │
                       ▼
               Streamlit Web App
                       │  "Explain this opportunity" (opt-in)
                       ▼
               Expansion Copilot
   (Groq / Llama 3.1 — explains pre-computed metrics only, never calculates)
```

---

## Tech Stack

| Layer      | Tools                                                 |
| ---------- | ----------------------------------------------------- |
| Storage    | PostgreSQL (Neon in production, local for dev)        |
| Processing | Python, Pandas, NumPy                                 |
| Analytics  | SQL                                                   |
| Frontend   | Streamlit, Plotly                                     |
| LLM        | Groq API (Llama 3.1 8B) — free tier, no billing required |
| Testing    | pytest                                                |
| Deployment | Streamlit Community Cloud                             |

*Groq's free API is used instead of a paid provider, so anyone (including graders or interviewers) can run the project without adding billing.*

---

## Core Features

### Cuisine Opportunity Index (COI)

A composite score built from four independently calculated components:

- **Demand Score**: average customer engagement (votes) per restaurant
- **Competition Score**: restaurant count for the cuisine in a locality, inverted so lower competition scores higher
- **Affordability Score**: how much cheaper a cuisine is than the locality's own average cost
- **Rating Stability**: consistency of customer ratings (inverted standard deviation)

**Each component is scaled 0–100 within its own city**, not across all four. Bangalore holds about 62% of the restaurants; scaling globally would let its wider ranges set the scale for everyone. "Is this a good opportunity in Noida?" is a Noida-relative question.

Default weights live in `config.py` with the reasoning behind each, and are adjustable live via sliders in the app. They are starting assumptions, not derived ground truth. Every score carries a **Confidence Rating** based on rated-restaurant count and review volume.

*Growth is not a COI component: the data has no reliable historical or establishment-date field. Its configured weight is redistributed proportionally across the other four rather than faked with a proxy.*

### Evidence filter

A sidebar filter hides cuisines backed by fewer than N restaurants in a locality (default 2). Confidence alone isn't enough here: a single restaurant with many votes still reaches 55% confidence, and one restaurant tagged with five cuisines would otherwise appear as five identical rows.

### Expansion Copilot

An opt-in "Explain this opportunity" button in the cuisine drill-down. It sends only that row's pre-computed metrics to Groq (Llama 3.1) and shows a short plain-language explanation next to the numbers. **It never calculates; it only explains.** Explanations are cached per input, and if there's no API key or the call fails, the app shows a fallback message and every number and chart still works.

---

## Data

| Source | Cities | Purpose |
| --- | --- | --- |
| Zomato Bangalore Restaurants (Kaggle) | Bangalore | Restaurant metadata, ratings, cuisine, cost, locality, restaurant type |
| `shrutimehta/zomato-restaurants-data` (Kaggle) — raw Zomato API JSON | New Delhi, Gurgaon, Noida | Same fields, minus restaurant type |

After cleaning: **20,151 restaurants**, **44,283 restaurant–cuisine pairs**, **4 cities**, **367 city–locality pairs**, **114 cuisines**, **6,660 scored (city, locality, cuisine) combinations**.

| City | Restaurants | Localities |
| --- | --- | --- |
| Bangalore | 12,480 | 93 |
| New Delhi | 5,473 | 165 |
| Gurgaon | 1,118 | 45 |
| Noida | 1,080 | 64 |

No live scraping: Zomato and Swiggy no longer offer public data access, so this project uses static, disclosed snapshots.

**Locality standardization.** The API dataset often labels a restaurant by its venue ("Cyber Hub, DLF Cyber City", "DLF Mall of India, Sector 18, Noida"). Left as-is, every mall became its own locality with 1–3 restaurants. `load_data.py` collapses each label to its area (last comma-separated part, trailing city names dropped, "Greater Noida" kept whole), plus two verified spelling merges. This took the three NCR cities from 435 to 256 localities. Labels with no area in them ("Ambience Mall, Gurgaon") keep the venue name rather than a guessed area.

**Considered and excluded:** Faridabad (251 restaurants across 40 localities, too thin per locality) and the other Indian cities in the API dump (~20 rows each). Faridabad is the first candidate if coverage improves. `python/data/raw/zomato_multicity.csv` was evaluated (`02_inspect_multicity.py`) and rejected: it's a delivery-app dataset, not comparable with the other two sources.

---

## Known Limitations

- **Cross-city comparisons are indicative only.** The two sources differ in how ratings and votes were collected, in coverage and in snapshot date. NCR rows come from API search results (partial coverage, several years old). Scores are scaled within each city for this reason.
- **Snapshot, not live.** Trend claims are not supported.
- **No historical/growth data.** Growth is omitted rather than fabricated.
- **COI is unvalidated.** There's no outcome data (which restaurants succeeded) to test it against. Weights are documented assumptions, adjustable in the app. Rating stability measures spread, not rating level.
- **Restaurant type is missing for NCR cities** (the API source doesn't have it); it is left NULL, not filled.
- **No synthetic or filler data is ever used.** Low coverage shows up as low confidence or is hidden by the evidence filter.
- The Bangalore source had a duplicate-listing issue (same restaurant listed once per order type); deduplicated on name + address.

---

## Project Roadmap

- [x] Data cleaning pipeline and PostgreSQL load
- [x] SQL analytics layer and COI implementation
- [x] Streamlit dashboard with adjustable weights
- [x] Deployment (Streamlit Community Cloud + Neon)
- [x] Multi-city expansion (New Delhi, Gurgaon, Noida) with within-city scaling
- [x] Locality standardization for venue-level labels
- [x] Expansion Copilot wired into the app (opt-in, cached, graceful fallback)
- [x] Evidence filter (minimum restaurants per cuisine)
- [x] Unit tests for COI math and cleaning helpers
- [ ] Weight sensitivity analysis (how stable are the top-ranked cuisines when weights shift?)
- [ ] Fresher data source, and Faridabad if coverage allows

---

## Local Setup

Requires Python 3.12 (pandas and psycopg2 wheels don't build on 3.14 yet).

```bash
git clone https://github.com/amishasharma2220/FlavorLens.git
cd FlavorLens
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # fill in your DB credentials and GROQ_API_KEY
```

Load the data (needs `python/data/raw/zomato.csv` and the API JSON dump; see `python/notebooks/05_parse_json_and_inspect.py`):

```bash
# 1. run python/db/schema.sql against your database (psql or the Neon SQL editor)
# 2. then:
python python/db/load_data.py
```

Run the tests and the app:

```bash
pytest
streamlit run streamlit/app.py
```

A free Groq API key from [console.groq.com](https://console.groq.com) is only needed for the Expansion Copilot; the rest of the app works fully without it.

---

*Built by Amisha Sharma · B.Tech CSE · Manipal University Jaipur*
