"""Unit tests for the COI math. No database needed: every test builds a
small DataFrame by hand and passes it straight into the functions."""

import math

import pandas as pd
import pytest

from python.analytics.coi_calculator import (
    compute_coi,
    compute_confidence,
    get_effective_weights,
    normalize_0_100,
    normalize_within_city,
)


def test_effective_weights_sum_to_one_and_drop_growth():
    w = get_effective_weights()
    assert set(w) == {"demand", "competition", "affordability", "rating_stability"}
    assert math.isclose(sum(w.values()), 1.0)


def test_normalize_0_100_scales_to_full_range():
    out = normalize_0_100(pd.Series([10, 20, 30]))
    assert list(out) == [0.0, 50.0, 100.0]


def test_normalize_0_100_degenerate_group_is_neutral_50():
    out = normalize_0_100(pd.Series([7, 7, 7]))
    assert list(out) == [50.0, 50.0, 50.0]


def test_normalize_within_city_scales_each_city_independently():
    df = pd.DataFrame({
        "city": ["A", "A", "B", "B"],
        "x": [0, 10, 1000, 2000],
    })
    out = normalize_within_city(df, "x")
    # City B's much larger values must not squash city A's range.
    assert list(out) == [0.0, 100.0, 0.0, 100.0]


def test_confidence_caps_at_100_and_averages_two_parts():
    rated = pd.Series([0, 5, 10, 40])
    votes = pd.Series([0, 25, 50, 999])
    out = compute_confidence(rated, votes)
    assert list(out) == [0.0, 50.0, 100.0, 100.0]


def test_confidence_one_restaurant_with_many_votes_is_55():
    # Documents why the app filters by restaurant count, not confidence:
    # a single well-reviewed restaurant still reaches 55%.
    out = compute_confidence(pd.Series([1]), pd.Series([500]))
    assert out.iloc[0] == pytest.approx(55.0)


def _toy_inputs():
    lc = pd.DataFrame({
        "city": ["A", "A", "A"],
        "locality": ["L", "L", "L"],
        "cuisine": ["X", "Y", "Z"],
        "restaurant_count": [1, 5, 20],
        "rated_restaurant_count": [1, 5, 20],
        "avg_votes": [100.0, 50.0, 10.0],
        "total_votes": [100, 250, 200],
        "avg_rating": [4.0, 3.8, 3.5],
        "rating_stddev": [None, 0.2, 0.6],
        "avg_cost": [400.0, None, 800.0],
    })
    la = pd.DataFrame({"city": ["A"], "locality": ["L"], "locality_avg_cost": [600.0]})
    return lc, la


def test_compute_coi_has_no_nans_and_stays_in_range():
    lc, la = _toy_inputs()
    out = compute_coi(lc, la)
    assert not out["coi"].isna().any()
    assert out["coi"].between(0, 100).all()
    for col in ["demand_score", "competition_score", "affordability_score", "rating_stability_score"]:
        assert out[col].between(0, 100).all(), col


def test_compute_coi_is_sorted_descending():
    lc, la = _toy_inputs()
    out = compute_coi(lc, la)
    assert list(out["coi"]) == sorted(out["coi"], reverse=True)


def test_custom_weights_are_renormalized():
    lc, la = _toy_inputs()
    a = compute_coi(lc.copy(), la.copy(), weights={"demand": 1, "competition": 1, "affordability": 1, "rating_stability": 1})
    b = compute_coi(lc.copy(), la.copy(), weights={"demand": 2, "competition": 2, "affordability": 2, "rating_stability": 2})
    assert list(a["coi"].round(6)) == list(b["coi"].round(6))


def test_demand_only_weight_ranks_by_votes():
    lc, la = _toy_inputs()
    out = compute_coi(lc, la, weights={"demand": 1, "competition": 0, "affordability": 0, "rating_stability": 0})
    assert list(out["cuisine"]) == ["X", "Y", "Z"]
