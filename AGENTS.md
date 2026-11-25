# Agents.md

This file is for AI coding assistants (Claude, Claude Code, Cursor, Copilot, etc.) working in this repository. If you're an AI reading this before making changes — read this whole file first.

## The one rule that overrides everything else

**Code computes. The LLM explains. Never let those swap roles.**

- Never let an LLM call determine or adjust a COI score, weight, or confidence value.
- Never let deterministic code (`python/db/`, `python/analytics/`) generate final user-facing explanation text — that belongs in `python/llm/copilot.py`.
- If a task seems to require blurring this line ("just have the LLM estimate competition since the data's thin") — stop and flag it instead of implementing it. That's a data problem, not something to paper over with a plausible LLM guess.

## Project-specific context

- **Data scope is Bangalore, New Delhi, Gurgaon and Noida, by locality.** Don't add cities or data sources without being asked — scope changes make the README's numbers false. Faridabad was considered and excluded (too thin); it's a candidate, not a TODO.
- **Every query groups by `(city, locality)`**, never locality alone — locality names collide across cities.
- **Component scores are normalized within each city** (`normalize_within_city`). Don't switch to a global scale; Bangalore would dominate it.
- **Locality standardization lives in `load_data.py` (`normalize_locality`) and applies to the NCR source only.** Keep it rule-based and tested. Add to `LOCALITY_ALIASES` only after confirming in the data that two spellings are the same area — no fuzzy matching. Any change to cleaning needs a data reload to take effect.
- **Never generate or insert synthetic/fabricated data**, for sparse localities or otherwise — not even "clearly labeled." Thin coverage shows up as low confidence or is hidden by the app's evidence filter, not filled with rows.
- **No reliable growth/`established_year` field exists in the source data.** Don't invent one. Growth is dropped from the COI and its weight redistributed.
- **COI weights live in `config.py` (`COIConfig`) and must stay documented.** If you change a weight, update the reasoning alongside it — an undocumented weight change is a bug.
- **Confidence scores must derive from something real** (rated restaurant count and total votes), never hardcoded.
- **The LLM is Groq (Llama 3.1 8B) through the `openai` SDK**, not Anthropic or OpenAI. Keys come from `.env` locally and `st.secrets` on Streamlit Cloud; never commit a key, and `.env.example` holds placeholders only.

## Repo conventions

- `python/db/` — schema and data loading. Cleans and loads raw data; does not compute the COI.
- `python/analytics/queries.py` — SQL retrieval and aggregation only.
- `python/analytics/coi_calculator.py` — COI math. Keep pure: same inputs → same outputs, no API calls inside this module.
- `python/llm/copilot.py` — prompt construction. Pass only already-computed numeric values into the LLM context; never hand it raw unaggregated data to "figure out" itself.
- `streamlit/app.py` — presentation only. No COI math here either; filters like the evidence filter hide rows, they don't change scores.
- `tests/` — pytest, no database needed. Run `pytest` before committing changes to `python/analytics/` or `python/db/load_data.py`.
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
4. Run `pytest` and make sure it passes.
5. Don't silently expand scope (new cities, new metrics, new data sources) — flag it as a suggestion instead of implementing it unprompted.

See `ARCHITECTURE.md` for system design and `FLOWS.md` for how data and users move through it.