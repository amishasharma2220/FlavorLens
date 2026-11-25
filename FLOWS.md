# Flows

Architecture describes the pieces. This describes how things actually move through them — the data's journey and the user's journey, kept separate on purpose since conflating them is where "dashboard" projects quietly become unmaintainable.

## 1. Data pipeline flow (offline, runs before the app exists)

```
python/data/raw/zomato.csv              raw Zomato API JSON files
(Bangalore)                             (global dump)
   │                                       │
   │  01_inspect.py                        │  04_inspect_json_structure.py
   │                                       │  05_parse_json_and_inspect.py
   │                                       ▼
   │                         python/data/processed/zomato_global_flat.csv
   │                                       │  filter to New Delhi, Gurgaon, Noida
   └──────────────┬────────────────────────┘
                  ▼
Clean — python/db/load_data.py
   │  - dedupe on name + address (Bangalore lists each restaurant once per order type)
   │  - parse "4.1/5" ratings into floats; "NEW", "-" and API rating 0 → missing, not zero
   │  - strip commas from cost ("1,200" → 1200)
   │  - Yes/No and 1/0 → booleans
   │  - tag every row with its city
   │  - NCR only: collapse venue labels to their area
   │      "DLF Mall of India, Sector 18, Noida" → "Sector 18"
   │  - drop rows missing locality or cuisine
   │  - split multi-cuisine strings ("North Indian, Chinese") into rows
   ▼
Load into PostgreSQL
   │  restaurants, restaurant_cuisines
   ▼
Aggregate — python/analytics/queries.py
   │  per (city, locality, cuisine): count, rated count, avg rating, rating stddev,
   │  avg cost, avg votes, total votes; per (city, locality): avg cost
   ▼
Normalize + score — python/analytics/coi_calculator.py
   │  scale each component 0–100 within its city, apply weights,
   │  compute COI + confidence
   ▼
Ready for streamlit/app.py (results cached for 1 hour)
```

This flow is deterministic — same input always produces the same COI numbers. No LLM call belongs anywhere in this half of the pipeline.

**Reloading data:** drop both tables, run `schema.sql`, then `python python/db/load_data.py`. A reload is needed whenever cleaning rules change, because the app reads the cleaned values straight from the database.

## 2. User flow (what someone experiences in the app)

```
User opens the app
   │
   ▼
Sidebar: adjusts COI weights (optional), picks a city, then a locality,
         sets the evidence filter (minimum restaurants per cuisine, default 2)
   │
   ▼
App scores all combinations with the chosen weights (cached)
   │
   ▼
User sees:
   - ranked cuisines by COI for that locality, with confidence, count, rating, cost
   - a note saying how many cuisines the evidence filter hid
   │
   ▼
User picks a cuisine to drill into
   │
   ├─► metrics + radar chart of the four component scores
   ├─► "How does this cuisine compare across all cities?" bar chart
   │
   ▼
"Explain this opportunity" button (opt-in, not automatic)
   │
   ▼
App sends ONLY that row's computed numbers + city/locality/cuisine names
to python/llm/copilot.py
   │  e.g. {coi: 58.1, confidence: 70, demand_score: 41.2, competition_score: 96.0, ...}
   ▼
Groq (Llama 3.1) returns 3–5 sentences
   │  instructed not to introduce new figures; cached per input
   ▼
Explanation shown under the numbers, never replacing them
```

Notes worth keeping in mind while building:

- **LLM call is opt-in.** It never fires on page load — unnecessary cost, and more chances for the prose to drift from the numbers.
- **Numbers stay visible next to the explanation**, always — that's what makes the tool checkable rather than a black box.
- **No flow lets free text change the COI.** The Copilot only explains values that were already computed.

## 3. Edge cases and how they're handled

- **Sparse data:** confidence drops with low sample size, and the evidence filter hides cuisines with too few restaurants. If every cuisine in a locality is below the filter, the app says so and suggests lowering it, instead of showing an empty table.
- **One restaurant, many cuisines:** without the filter, a single restaurant tagged with five cuisines shows up as five identical rows. The default filter of 2 removes these.
- **Missing rating:** shown as "—" in the table; the Copilot prompt says "not available" rather than passing NaN.
- **Degenerate groups:** when every value in a city's group is identical, the component scores a neutral 50.
- **Missing combination:** a cuisine with no restaurants in a locality isn't listed — no misleading zero score.
- **LLM call fails** (no key, timeout after 20 s, API error): numbers and charts still render, and a short fallback message replaces the explanation.
