"""Tests for AI helper utilities."""

from watchpath.ai import _safe_float


def test_safe_float_accepts_clean_numbers():
    assert _safe_float(0.85) == 0.85
    assert _safe_float(1) == 1.0


def test_safe_float_parses_percentages_and_annotations():
    assert _safe_float("75%") == 0.75
    assert _safe_float("0.42 (Medium)") == 0.42


def test_safe_float_clamps_and_rejects_out_of_range():
    assert _safe_float("150%") == 1.0
    assert _safe_float("-0.5") == 0.0
    assert _safe_float("429 status") is None


def test_safe_float_handles_missing_values():
    assert _safe_float(None) is None
    assert _safe_float("N/A") is None
