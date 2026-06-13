"""Messy customer-orders generator — real-world data dirt, seeded & deterministic.

Unlike the clean synthetic generators, this one injects the kinds of defects that
appear in genuine operational data and that frontier models cannot have memorised
(the mess is seeded, not a famous dataset):

  - exact duplicate rows (double-submitted orders)
  - a monetary column stored as dirty strings ("$1,234.50", " 1,000 USD", "")
  - inconsistent categorical labels for region ("NY", "ny", " New York ", "new-york")
  - missing values (blank email, NaN amount)
  - leading/trailing whitespace on string fields

The agent must clean before it can answer — counting rows, summing revenue, or
counting regions on the raw frame gives wrong answers. Ground truths are computed
from the cleaned data and are exact for a given seed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Canonical regions and the dirty surface forms each can appear as.
_REGION_VARIANTS = {
    "new york": ["New York", "new york", "NY", " New York ", "new-york", "NEW YORK"],
    "california": ["California", "california", "CA", " CA", "Calif.", "CALIFORNIA"],
    "texas": ["Texas", "texas", "TX", "tx ", "Tex.", "TEXAS"],
    "florida": ["Florida", "florida", "FL", " FL ", "fla", "FLORIDA"],
    "illinois": ["Illinois", "illinois", "IL", "il", "Ill.", "ILLINOIS"],
}


def generate(n_rows: int = 600, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    canonical = list(_REGION_VARIANTS.keys())

    base_region = rng.choice(canonical, size=n_rows)
    # Render each canonical region as one of its dirty surface forms.
    region = np.array(
        [rng.choice(_REGION_VARIANTS[c]) for c in base_region], dtype=object
    )

    amount = np.round(rng.gamma(shape=2.0, scale=80.0, size=n_rows) + 5.0, 2)
    order_id = np.arange(100000, 100000 + n_rows)
    customer_email = np.array(
        [f" user{rng.integers(1, 4000)}@mail.com " for _ in range(n_rows)],
        dtype=object,
    )

    # Dirty money column: render the float as inconsistent strings.
    def _dirty_money(x: float) -> str:
        style = rng.integers(0, 4)
        if style == 0:
            return f"${x:,.2f}"
        if style == 1:
            return f" {x:,.2f} USD"
        if style == 2:
            return f"{x:.2f}"
        return f"$ {x:,.2f} "

    amount_str = np.array([_dirty_money(x) for x in amount], dtype=object)

    df = pd.DataFrame({
        "order_id": order_id,
        "region": region,
        "amount": amount_str,        # object: dirty currency strings
        "customer_email": customer_email,
    })

    # Inject ~6% missing amount (blank string) and ~4% missing email (None).
    amt_missing = rng.choice(n_rows, size=int(n_rows * 0.06), replace=False)
    df.loc[amt_missing, "amount"] = ""
    email_missing = rng.choice(n_rows, size=int(n_rows * 0.04), replace=False)
    df.loc[email_missing, "customer_email"] = None

    # Inject exact duplicate rows: copy a fixed set of rows and append them.
    n_dupes = 40
    dup_src = rng.choice(n_rows, size=n_dupes, replace=False)
    dupes = df.iloc[dup_src].copy()
    df = pd.concat([df, dupes], ignore_index=True)

    # Shuffle so duplicates aren't adjacent.
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df
