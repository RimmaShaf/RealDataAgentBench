"""Messy loan-applications generator — target leakage + duplicate records.

Injected defects (deterministic per seed):
  - a leaky feature: ``internal_score`` is a near-perfect function of the target
    ``default`` (it is assigned *from* the label), so any model using it scores a
    suspiciously perfect AUC. The agent must flag it as leakage, not celebrate it.
  - duplicate application rows (same app_id resubmitted) — if not removed before a
    train/test split, the same record leaks across the split.
  - inconsistent employment labels ("Employed", "employed", "FT", "full-time")
    that collapse to two real states.
  - missing income values.

Ground truths (duplicate count, the leaky column, default rate) are exact per seed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_EMPLOYED = ["Employed", "employed", "FT", "full-time", "FULL TIME"]
_UNEMPLOYED = ["Unemployed", "unemployed", "none", "not employed"]


def generate(n_rows: int = 600, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    income = rng.gamma(shape=3.0, scale=18000, size=n_rows).round(0)
    loan_amount = rng.gamma(shape=2.0, scale=9000, size=n_rows).round(0)
    employed = rng.random(n_rows) < 0.7

    # True default depends weakly on income/loan ratio (a realistic, noisy signal).
    risk = (loan_amount / (income + 1.0)) + rng.normal(0, 0.15, size=n_rows)
    default = (risk > np.quantile(risk, 0.78)).astype(int)

    # LEAKY feature: assigned from the label, so it perfectly separates classes.
    internal_score = np.where(
        default == 1,
        rng.uniform(0.0, 0.18, size=n_rows),
        rng.uniform(0.82, 1.0, size=n_rows),
    ).round(3)

    employment = np.array(
        [rng.choice(_EMPLOYED) if e else rng.choice(_UNEMPLOYED) for e in employed],
        dtype=object,
    )

    df = pd.DataFrame({
        "app_id": np.arange(1, n_rows + 1),
        "income": income,
        "loan_amount": loan_amount,
        "employment": employment,
        "internal_score": internal_score,
        "default": default,
    })

    # ~7% missing income.
    miss = rng.choice(n_rows, size=int(n_rows * 0.07), replace=False)
    df.loc[miss, "income"] = np.nan

    # Duplicate application rows (same app_id).
    n_dupes = 45
    dup_src = rng.choice(n_rows, size=n_dupes, replace=False)
    df = pd.concat([df, df.iloc[dup_src]], ignore_index=True)

    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df
