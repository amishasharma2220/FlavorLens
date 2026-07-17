# Agents.md

This file is for AI coding assistants (Claude, Claude Code, Cursor, Copilot, etc.) working in this repository. If you're an AI reading this before making changes — read this whole file first.

## The one rule that overrides everything else

**Code computes. The LLM explains. Never let those swap roles.**

- Never let an LLM call determine or adjust a COI score, weight, or confidence value.
- Never let deterministic code (`python/db/`, `python/analytics/`) generate final user-facing explanation text — that belongs in `python/llm/copilot.py`.
- If a task seems to require blurring this line ("just have the LLM estimate competition since the data's thin") — stop and flag it instead of implementing it. That's a data problem, not something to paper over with a plausible LLM guess.

## Project-specific context

- **Data scope is Bangalore, by locality**, not multiple cities. Don't expand this without being asked — the current dataset (Zomato Bangalore Restaurants, Kaggle) doesn't support it, and silently expanding scope would make the README's claims false.
- **Never generate or insert synthetic/fabricated data**, for sparse localities or otherwise — not even "clearly labeled." If coverage is thin, that should show up as a low confidence score, not filler rows.
- **No reliable growth/`established_year` field exists in the source data.** Don't invent one. If a growth component is needed, it must be a disclosed proxy (e.g. votes as engagement), documented as such in code comments and any user-facing copy.
- **COI weights live in `config.py` (`COIConfig`) and must stay documented.** If you change a weight, update the reasoning alongside it — an undocumented weight change is a bug.
- **Confidence scores must derive from something real** (e.g. sample size per locality/cuisine pair), never hardcoded.

## Repo conventions

- `python/db/` — schema and data loading. Cleans and loads raw data; does not compute the COI.
- `python/analytics/queries.py` — SQL retrieval and aggregation only.
- `python/analytics/coi_calculator.py` — COI math. Keep pure: same inputs → same outputs, no API calls inside this module.
- `python/llm/copilot.py` — prompt construction. Pass only already-computed numeric values into the LLM context; never hand it raw unaggregated data to "figure out" itself.
- `streamlit/app.py` — presentation only. No COI math here either.
- Don't add new dependencies to `requirements.txt` without a clear reason — an overstuffed dependency list reads as copy-pasted, not understood.

## Writing style for anything user-facing (README, app copy, LLM prompt output)

- No AI-sounding language: avoid "leverage," "seamless," "robust," "unlock," "revolutionize," "cutting-edge."
- No exaggerated claims — this is a decision-support tool on historical/static data, not a forecasting system.
- Prefer specific, checkable statements over vague ones.
- If asked to write the README or app copy, write it so it sounds like someone who understands the tradeoffs — including the limitations — not like marketing copy.

## Before making a change

1. Check which layer you're touching and keep changes inside that layer's responsibility, per `ARCHITECTURE.md`.
2. If a change affects COI calculation, check whether the weighting rationale still holds and update the docstring if not.
3. If a change touches the LLM prompt, verify it still explicitly forbids the model from introducing its own numbers.
4. Don't silently expand scope (new cities, new metrics, new data sources) — flag it as a suggestion instead of implementing it unprompted.

See `ARCHITECTURE.md` for system design and `FLOWS.md` for how data and users move through it.