# Flows

Architecture describes the pieces. This describes how things actually move through them — the data's journey and the user's journey, kept separate on purpose since conflating them is where "dashboard" projects quietly become unmaintainable.

## 1. Data pipeline flow (offline, runs before the app exists)

```
python/data/raw/zomato.csv
   │
   ▼
Inspect — python/notebooks/01_inspect.py
   │  nulls, dtypes, distinct values, sample rows
   ▼
Clean — python/db/load_data.py
   │  - parse "4.1/5" style ratings into floats
   │  - treat "NEW" and "-" as missing, not zero
   │  - split multi-cuisine strings ("North Indian, Chinese") into rows
   │  - strip currency formatting from cost column ("1,200" → 1200)
   │  - standardize locality names (dedupe near-duplicates like "BTM" / "BTM Layout")
   ▼
Load into PostgreSQL
   │  restaurants table, localities table
   ▼
Aggregate — python/analytics/queries.py
   │  per (locality, cuisine): count, avg rating, avg cost, votes sum
   ▼
Normalize + score — python/analytics/coi_calculator.py
   │  scale each metric 0–100, apply weights, compute COI + confidence
   ▼
Persist scored results
   │  coi_results table, or cached DataFrame/parquet
   ▼
Ready for streamlit/app.py to read
```

This flow is deterministic — same input always produces the same COI numbers. No LLM call belongs anywhere in this half of the pipeline.

## 2. User flow (what someone experiences in the app)

```
User opens streamlit/app.py
   │
   ▼
Selects a locality (e.g. "Indiranagar")
   │
   ▼
App loads precomputed COI results for that locality
   │  (already scored — no live computation on page load)
   │
   ▼
User sees:
   - ranked list of cuisines by COI for that locality
   - component score breakdown (demand / competition / affordability / rating stability)
   - a chart per selected cuisine
   │
   ▼
User picks a specific cuisine to drill into
   │
   ▼
"Explain this" button (opt-in, not automatic)
   │
   ▼
App sends ONLY the computed numbers to python/llm/copilot.py
   │  e.g. {coi: 88, demand: 85, competition: 20, affordability: 75, rating_stability: 90}
   ▼
LLM returns a short plain-language explanation
   │  instructed not to introduce new figures
   ▼
Explanation shown alongside the numbers, never replacing them
```

Notes worth keeping in mind while building:

- **LLM call is opt-in.** Don't fire it on every page load — unnecessary cost, and more chances for the prose to drift from the numbers.
- **Numbers stay visible next to the explanation**, always — that's what makes the tool checkable rather than a black box.
- **No flow lets free text change the COI.** The Copilot answers questions by routing to already-computed metrics; it doesn't calculate on the fly.

## 3. Edge cases to design for early

- **Sparse data**: a locality with 2 restaurants of a cuisine shouldn't produce a confident-looking COI — confidence score should visibly drop with low sample size.
- **Missing combination**: if a locality has zero restaurants of a cuisine, say "no data for this combination," not a misleading zero score.
- **LLM call fails**: numbers and charts still render. The explanation is an enhancement, not a dependency.