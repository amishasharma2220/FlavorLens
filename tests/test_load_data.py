"""Tests for the cleaning helpers in load_data.py (no database needed)."""

import pytest

from python.db.load_data import (
    clean_cost,
    clean_multicity_rating,
    clean_rate,
    normalize_locality,
)


@pytest.mark.parametrize("raw, expected", [
    ("DLF Mall of India, Sector 18,  Noida", "Sector 18"),
    ("Gardens Galleria, Sector 38 Noida", "Sector 38"),
    ("Mosaic Hotels, Sector 18, Noida ", "Sector 18"),
    ("Cyber Hub, DLF Cyber City", "DLF Cyber City"),
    ("Huda City Centre Metro Station, Sector 29, Gurgaon", "Sector 29"),
    ("ARSS Mall, Paschim Vihar", "Paschim Vihar"),
    ("Select Citywalk Mall, Saket", "Saket"),
    # Greater Noida is an area in its own right, not "Greater" + city name.
    ("Ansal Plaza Mall, Greater Noida", "Greater Noida"),
    ("Jaypee Greens, Greater Noida, Noida", "Greater Noida"),
    ("Greater Noida", "Greater Noida"),
    # Verified spelling variants of the same area.
    ("Gourmet Hub, Pashim Vihar", "Paschim Vihar"),
    ("West End Mall, Janak Puri", "Janakpuri"),
    # Plain area labels pass through unchanged.
    ("Connaught Place", "Connaught Place"),
    ("Sector 62", "Sector 62"),
    # No area in the label: keep the venue rather than invent one.
    ("Ambience Mall, Gurgaon", "Ambience Mall"),
])
def test_normalize_locality(raw, expected):
    assert normalize_locality(raw) == expected


def test_normalize_locality_passes_missing_through():
    assert normalize_locality(None) is None


@pytest.mark.parametrize("raw, expected", [
    ("4.1/5", 4.1), ("3.9 /5", 3.9), ("NEW", None), ("-", None), (None, None),
])
def test_clean_rate(raw, expected):
    assert clean_rate(raw) == expected


def test_clean_cost_strips_commas():
    assert clean_cost("1,200") == 1200.0
    assert clean_cost(None) is None


def test_multicity_rating_zero_means_unrated():
    assert clean_multicity_rating(0) is None
    assert clean_multicity_rating("4.2") == 4.2
