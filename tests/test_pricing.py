"""Pricing-table tests, including the staleness gate.

The staleness test fails the CI build once the pricing table is older than
``MAX_PRICING_AGE_DAYS``. Provider prices drift, and a stale table silently
corrupts every cost number on the leaderboard — so this forces a periodic review.
To clear a failure: re-check the official pricing pages, update
``COST_PER_M_TOKENS`` if needed, and bump ``PRICING_AS_OF`` in
``realdataagentbench/harness/pricing.py``.
"""

import importlib.util
from datetime import date
from pathlib import Path

import pytest

# Load pricing.py standalone. It has no intra-package imports, so this avoids
# pulling in harness/__init__ (which transitively imports the slow provider SDKs)
# and keeps this test fast and self-contained.
_PRICING_PATH = Path(__file__).resolve().parent.parent / "realdataagentbench" / "harness" / "pricing.py"
_spec = importlib.util.spec_from_file_location("rdab_pricing_under_test", _PRICING_PATH)
pricing = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pricing)


def test_pricing_as_of_is_a_valid_date():
    # Must parse, and must not be in the future.
    as_of = date.fromisoformat(pricing.PRICING_AS_OF)
    assert as_of <= date.today(), "PRICING_AS_OF is in the future"


def test_pricing_table_is_not_stale():
    age = pricing.pricing_age_days()
    assert not pricing.pricing_is_stale(), (
        f"Pricing table is {age} days old (> {pricing.MAX_PRICING_AGE_DAYS}). "
        "Re-verify model prices against official pricing pages, update "
        "COST_PER_M_TOKENS, then bump PRICING_AS_OF in harness/pricing.py."
    )


def test_age_helper_math():
    # 100 days after the as-of date is stale; 10 days is not.
    as_of = date.fromisoformat(pricing.PRICING_AS_OF)
    assert pricing.pricing_age_days(as_of) == 0
    far = date.fromordinal(as_of.toordinal() + 100)
    near = date.fromordinal(as_of.toordinal() + 10)
    assert pricing.pricing_is_stale(far) is True
    assert pricing.pricing_is_stale(near) is False


def test_compute_cost_uses_table():
    # gpt-4.1 = (2.00, 8.00) per M → 1M in + 1M out = $10.00
    assert pricing.compute_cost("gpt-4.1", 1_000_000, 1_000_000) == pytest.approx(10.0)


def test_compute_cost_falls_back_for_unknown_model():
    # fallback is (1.00, 3.00)
    assert pricing.compute_cost("totally-unknown-model", 1_000_000, 0) == pytest.approx(1.0)


def test_all_leaderboard_models_have_a_price():
    # Every model that appears on the leaderboard must have an explicit entry,
    # otherwise its cost silently uses the conservative fallback.
    leaderboard_models = [
        "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o", "gpt-4o-mini", "gpt-5",
        "claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001",
        "grok-3-mini", "gemini-2.5-flash", "llama-3.3-70b-versatile",
    ]
    missing = [m for m in leaderboard_models if m not in pricing.COST_PER_M_TOKENS]
    assert not missing, f"Models missing an explicit price entry: {missing}"
