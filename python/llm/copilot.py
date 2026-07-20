"""
FlavorLens — Expansion Copilot
---------------------------------
The only module in this project that talks to an LLM. Its job is narrow
and deliberately constrained: take already-computed COI numbers for one
(locality, cuisine) pair and turn them into a short, plain-language
explanation. It NEVER calculates anything — every number in the prompt
comes from coi_calculator.py, and the model is explicitly instructed not
to introduce figures of its own. See ARCHITECTURE.md / AGENTS.md for why
this boundary is the core design principle of the whole project.

Uses Groq's free API (OpenAI-compatible protocol, no billing required)
rather than a paid provider.
"""

import os
import sys
from openai import OpenAI, APIError
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.1-8b-instant"


SYSTEM_PROMPT = """You are an explanation layer for a restaurant expansion \
analytics tool. You will be given a fixed set of pre-computed metrics for \
one cuisine in one locality of Bangalore. Your ONLY job is to explain what \
these numbers mean in plain, business-friendly language for a restaurant \
owner or investor.

Strict rules:
- Use ONLY the numbers provided to you. Do not introduce any number, \
statistic, or figure that was not given to you in the input.
- Do not perform any calculation, estimation, or projection of your own.
- Do not invent facts about the locality, restaurants, or market beyond \
what the numbers imply.
- If confidence is low, say so plainly and explain why (small sample size) \
rather than downplaying it.
- Write 3-5 sentences, no bullet points, no headers.
- Avoid hype language ("amazing opportunity", "can't miss") — be measured \
and specific, the way a careful analyst would talk to a client.
"""


def _build_user_prompt(locality: str, cuisine: str, metrics: dict) -> str:
    return f"""Locality: {locality}
Cuisine: {cuisine}

Cuisine Opportunity Index (COI): {metrics['coi']:.1f} / 100
Confidence: {metrics['confidence']:.0f}%
Demand score: {metrics['demand_score']:.1f} / 100
Competition score (already inverted — higher means LESS competition): {metrics['competition_score']:.1f} / 100
Affordability score: {metrics['affordability_score']:.1f} / 100
Rating stability score: {metrics['rating_stability_score']:.1f} / 100
Restaurant count in this locality for this cuisine: {int(metrics['restaurant_count'])}
Average rating: {metrics['avg_rating']:.1f} / 5
Average cost for two: ₹{metrics['avg_cost']:.0f}

Explain what this means for someone considering opening a {cuisine} \
restaurant in {locality}."""


def explain_opportunity(locality: str, cuisine: str, metrics: dict) -> str:
    """
    metrics must be a dict/row containing at minimum: coi, confidence,
    demand_score, competition_score, affordability_score,
    rating_stability_score, restaurant_count, avg_rating, avg_cost.
    (This matches the columns produced by coi_calculator.compute_coi().)

    Returns the explanation text, or a graceful fallback message if the
    API call fails — the app's numbers and charts should never depend on
    this succeeding.
    """
    if not GROQ_API_KEY:
        return ("Explanation unavailable: no GROQ_API_KEY configured. "
                "The numbers above are still fully valid — this only affects "
                "the plain-language summary.")

    client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    user_prompt = _build_user_prompt(locality, cuisine, metrics)

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=400,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content
    except APIError as e:
        # Degrade gracefully — the app's numbers and charts must still work
        # even if the explanation layer fails. See FLOWS.md, edge cases.
        return f"Explanation temporarily unavailable ({e.__class__.__name__}). The scores above are unaffected."
    except Exception as e:
        return f"Explanation temporarily unavailable. The scores above are unaffected. ({e})"


if __name__ == "__main__":
    # Quick manual test — run this directly after setting GROQ_API_KEY
    # in .env to sanity-check the prompt and response before wiring it into
    # the Streamlit app.
    sample_metrics = {
        "coi": 71.7,
        "confidence": 55.0,
        "demand_score": 54.9,
        "competition_score": 100.0,
        "affordability_score": 61.2,
        "rating_stability_score": 78.0,
        "restaurant_count": 2,
        "avg_rating": 4.1,
        "avg_cost": 1100,
    }
    print(explain_opportunity("Whitefield", "Tex-Mex", sample_metrics))