"""Token pricing — single source of truth for all model costs.

Prices are USD per 1 million tokens (input / output).

``PRICING_AS_OF`` records when these numbers were last verified against official
pricing pages. Provider prices change often, so ``tests/test_pricing.py`` fails
the build once this table is older than ``MAX_PRICING_AGE_DAYS``, forcing a
periodic review. The date is surfaced on the leaderboard via ``build_leaderboard``.

Both ``harness/providers.py`` and ``scripts/build_leaderboard.py`` import from
here so the numbers never drift out of sync.
"""

from __future__ import annotations

from datetime import date

# Last time the prices below were checked against official pricing pages (YYYY-MM-DD).
# Bump this whenever you review/update the table — the CI staleness check keys off it.
PRICING_AS_OF = "2026-06-15"
# CI fails if the table is older than this (forces a roughly quarterly price review).
MAX_PRICING_AGE_DAYS = 90

# (input_$/M, output_$/M)
COST_PER_M_TOKENS: dict[str, tuple[float, float]] = {
    # ── Anthropic ─────────────────────────────────────────────────────────────
    "claude-opus-4-8":           (5.00,  25.00),
    "claude-sonnet-4-6":         (3.00,  15.00),
    "claude-opus-4-6":           (5.00,  25.00),
    "claude-haiku-4-5-20251001": (1.00,   5.00),
    # short aliases kept for backwards-compat with old output files
    "haiku":                     (1.00,   5.00),
    # ── OpenAI ────────────────────────────────────────────────────────────────
    "gpt-5":                     (15.00, 60.00),
    "gpt-5-mini":                (1.10,   4.40),
    "gpt-4.1":                   (2.00,   8.00),
    "gpt-4.1-mini":              (0.40,   1.60),
    "gpt-4.1-nano":              (0.10,   0.40),
    "gpt-4o":                    (2.50,  10.00),
    "gpt-4o-mini":               (0.15,   0.60),
    "gpt-4-turbo":               (10.00, 30.00),
    "gpt-4":                     (30.00, 60.00),
    "gpt-3.5-turbo":             (0.50,   1.50),
    # ── Groq (Llama / Mixtral / Gemma) — paid-tier prices ────────────────────
    "llama-3.3-70b-versatile":   (0.59,   0.79),
    "llama-3.1-70b-versatile":   (0.59,   0.79),
    "llama-3.1-8b-instant":      (0.05,   0.08),
    "llama3-70b-8192":           (0.59,   0.79),
    "llama3-8b-8192":            (0.05,   0.08),
    "mixtral-8x7b-32768":        (0.24,   0.24),
    "gemma2-9b-it":              (0.20,   0.20),
    # ── xAI Grok ──────────────────────────────────────────────────────────────
    "grok-3":                    (3.00,  15.00),
    "grok-3-mini":               (0.30,   0.50),
    "grok-3-fast":               (5.00,  25.00),
    "grok-2-1212":               (2.00,  10.00),
    # ── Google Gemini ─────────────────────────────────────────────────────────
    "gemini-2.5-pro":            (1.25,  10.00),
    "gemini-2.5-flash":          (0.15,   0.60),
    "gemini-2.0-flash":          (0.10,   0.40),
    "gemini-2.0-flash-lite":     (0.075,  0.30),
    # ── Ollama (local — no API cost) ──────────────────────────────────────────
    "gemma4":                    (0.00,   0.00),
    "gemma4:27b":                (0.00,   0.00),
    "gemma4:12b":                (0.00,   0.00),
    "gemma3":                    (0.00,   0.00),
    "gemma3:27b":                (0.00,   0.00),
    "llama3.2":                  (0.00,   0.00),
    "llama3.1":                  (0.00,   0.00),
    "mistral":                   (0.00,   0.00),
    "qwen2.5":                   (0.00,   0.00),
    "phi4":                      (0.00,   0.00),
}

# Used when a model isn't in the table — conservative over-estimate.
_FALLBACK_COST: tuple[float, float] = (1.00, 3.00)


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return estimated cost in USD for a given token usage."""
    in_per_m, out_per_m = COST_PER_M_TOKENS.get(model, _FALLBACK_COST)
    return round(
        (input_tokens / 1_000_000) * in_per_m
        + (output_tokens / 1_000_000) * out_per_m,
        6,
    )


def pricing_age_days(today: date | None = None) -> int:
    """Days since the pricing table was last verified (see ``PRICING_AS_OF``)."""
    today = today or date.today()
    as_of = date.fromisoformat(PRICING_AS_OF)
    return (today - as_of).days


def pricing_is_stale(today: date | None = None) -> bool:
    """True if the pricing table is older than ``MAX_PRICING_AGE_DAYS``."""
    return pricing_age_days(today) > MAX_PRICING_AGE_DAYS
