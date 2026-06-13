"""Messy IoT sensor-reading generator — seeded real-world dirt for cleaning tasks.

Injected defects (deterministic per seed):
  - MNAR missingness: readings are dropped *because* they were high (the sensor
    saturates), so the missingness is informative, not random — naive mean
    imputation biases the result downward.
  - outliers: a small fraction of spurious spikes far outside the IQR fence.
  - inconsistent unit labels for the same unit ("C", "c", "celsius", "Celsius ").
  - exact duplicate rows (a logger re-emitting the same packet).

The agent must detect the outliers (IQR rule), recognise the missingness is not
random, and clean before summarising. Ground truths are exact for a given seed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_UNIT_VARIANTS = ["C", "c", "celsius", "Celsius ", " C", "CELSIUS"]


def generate(n_rows: int = 700, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    sensor_id = rng.integers(1, 25, size=n_rows)
    reading = rng.normal(50.0, 8.0, size=n_rows).round(2)

    # Inject ~4% high-side outliers (sensor spikes well past the IQR fence).
    n_out = int(n_rows * 0.04)
    out_idx = rng.choice(n_rows, size=n_out, replace=False)
    reading[out_idx] = rng.uniform(120, 160, size=n_out).round(2)

    unit = np.array([rng.choice(_UNIT_VARIANTS) for _ in range(n_rows)], dtype=object)

    df = pd.DataFrame({
        "sensor_id": sensor_id,
        "reading": reading,
        "unit": unit,
    })

    # MNAR: drop ~the top slice of *non-outlier* readings (saturation), so
    # missingness is correlated with magnitude rather than random.
    non_outlier = np.setdiff1d(np.arange(n_rows), out_idx)
    high = non_outlier[np.argsort(reading[non_outlier])[-int(n_rows * 0.10):]]
    df.loc[high, "reading"] = np.nan

    # Exact duplicate rows (re-emitted packets).
    n_dupes = 30
    dup_src = rng.choice(n_rows, size=n_dupes, replace=False)
    df = pd.concat([df, df.iloc[dup_src]], ignore_index=True)

    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df
