"""Messy A/B survey generator — dirty grouping labels + duplicate respondents.

Injected defects (deterministic per seed):
  - inconsistent group labels for the same two arms ("A", "a", " A ", "group_a"
    vs "B", "b", "group_b") — grouping on the raw column splits each arm into
    several phantom groups.
  - duplicate respondent_id rows (a respondent submitted twice) — the analysis
    must keep one row per respondent or the test is pseudo-replicated.
  - missing scores (blank responses).

The two true arms have a genuine mean difference, so a correct clean → dedup →
two-sample test recovers a real, significant effect. Ground truths (the p-value,
the higher-mean arm) are exact for a given seed once cleaning is done correctly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_A_VARIANTS = ["A", "a", " A ", "group_a", "GROUP A"]
_B_VARIANTS = ["B", "b", " B ", "group_b", "GROUP B"]


def generate(n_rows: int = 500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    true_arm = rng.choice(["A", "B"], size=n_rows)
    # Arm B scores ~6 points higher on average (the real effect).
    score = np.where(
        true_arm == "A",
        rng.normal(70, 12, size=n_rows),
        rng.normal(76, 12, size=n_rows),
    ).round(1)

    group = np.array(
        [rng.choice(_A_VARIANTS if a == "A" else _B_VARIANTS) for a in true_arm],
        dtype=object,
    )
    respondent_id = np.arange(1, n_rows + 1)

    df = pd.DataFrame({
        "respondent_id": respondent_id,
        "group": group,
        "score": score,
    })

    # ~5% missing scores (blank responses).
    miss = rng.choice(n_rows, size=int(n_rows * 0.05), replace=False)
    df.loc[miss, "score"] = np.nan

    # Duplicate respondents: re-submit a fixed set of rows (same respondent_id).
    n_dupes = 35
    dup_src = rng.choice(n_rows, size=n_dupes, replace=False)
    df = pd.concat([df, df.iloc[dup_src]], ignore_index=True)

    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df
