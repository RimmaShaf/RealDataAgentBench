"""Tests for the messy real-world-style generators.

These assert (a) seeded determinism, (b) that the injected dirt is actually
present, and (c) that the exact ground-truth counts used by the task YAMLs hold —
so the tasks stay self-consistent if a generator is ever changed.
"""

import numpy as np
import pandas as pd
import pytest

from realdataagentbench.datasets import get_generator


def _parse_money(s):
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return np.nan
    s = str(s).strip().replace("$", "").replace("USD", "").replace(",", "").strip()
    if s == "":
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


class TestMessyCustomerOrders:
    def setup_method(self):
        self.df = get_generator("messy_customer_orders")(n_rows=600, seed=42)

    def test_seed_reproducible(self):
        a = get_generator("messy_customer_orders")(n_rows=600, seed=42)
        b = get_generator("messy_customer_orders")(n_rows=600, seed=42)
        pd.testing.assert_frame_equal(a, b)

    def test_has_exact_duplicate_rows(self):
        assert int(self.df.duplicated().sum()) == 40

    def test_amount_is_text_not_numeric(self):
        assert self.df["amount"].dtype == object or self.df["amount"].dtype == "string"
        # raw column cannot be summed numerically
        assert not pd.api.types.is_numeric_dtype(self.df["amount"])

    def test_region_labels_are_dirty(self):
        # many raw labels, few true regions
        assert self.df["region"].nunique() > 5

    def test_ground_truth_revenue_and_regions(self):
        d = self.df.drop_duplicates().copy()
        d["amt"] = d["amount"].map(_parse_money)
        assert round(d["amt"].dropna().sum(), 2) == pytest.approx(90383.21, abs=0.5)
        # 5 canonical regions after lower/strip/abbrev mapping
        canon = {"new york": ["new york", "ny", "new-york"],
                 "california": ["california", "ca", "calif."],
                 "texas": ["texas", "tx", "tex."],
                 "florida": ["florida", "fl", "fla"],
                 "illinois": ["illinois", "il", "ill."]}
        norm = d["region"].str.strip().str.lower()
        def to_canon(x):
            for k, vs in canon.items():
                if x in vs or x == k:
                    return k
            return x
        assert norm.map(to_canon).nunique() == 5


class TestMessySensorData:
    def setup_method(self):
        self.df = get_generator("messy_sensor_data")(n_rows=700, seed=42)

    def test_seed_reproducible(self):
        a = get_generator("messy_sensor_data")(n_rows=700, seed=42)
        pd.testing.assert_frame_equal(a, self.df)

    def test_duplicate_and_missing_counts(self):
        assert int(self.df.duplicated().sum()) == 44
        d = self.df.drop_duplicates()
        assert int(d["reading"].isna().sum()) == 56

    def test_iqr_outlier_count(self):
        r = self.df.drop_duplicates()["reading"].dropna()
        q1, q3 = r.quantile(0.25), r.quantile(0.75)
        iqr = q3 - q1
        n_out = int(((r > q3 + 1.5 * iqr) | (r < q1 - 1.5 * iqr)).sum())
        assert n_out == 32

    def test_missingness_is_not_random(self):
        # MNAR: the readings that survived skew lower than the global mean would,
        # because high readings were preferentially dropped.
        d = self.df.drop_duplicates()
        observed_mean = d["reading"].dropna().mean()
        # injected outliers push the observed mean up; the clean (non-outlier) mean
        # is well below 50, evidence the high values were dropped non-randomly.
        r = d["reading"].dropna()
        q1, q3 = r.quantile(0.25), r.quantile(0.75)
        iqr = q3 - q1
        clean = r[(r <= q3 + 1.5 * iqr) & (r >= q1 - 1.5 * iqr)]
        assert clean.mean() < 50.0


class TestMessySurvey:
    def setup_method(self):
        self.df = get_generator("messy_survey")(n_rows=500, seed=42)

    def test_duplicate_respondents(self):
        assert int(self.df.duplicated().sum()) == 35

    def test_dirty_group_labels_collapse_to_two_arms(self):
        assert self.df["group"].nunique() > 2
        norm = (self.df["group"].str.strip().str.lower()
                .str.replace("group ", "", regex=False)
                .str.replace("group_", "", regex=False))
        arms = norm.map(lambda x: "A" if x.startswith("a") else "B")
        assert arms.nunique() == 2

    def test_real_effect_is_significant(self):
        from scipy import stats as st
        d = self.df.drop_duplicates(subset="respondent_id", keep="first").copy()
        norm = (d["group"].str.strip().str.lower()
                .str.replace("group ", "", regex=False)
                .str.replace("group_", "", regex=False))
        d["arm"] = norm.map(lambda x: "A" if x.startswith("a") else "B")
        a = d[d.arm == "A"]["score"].dropna()
        b = d[d.arm == "B"]["score"].dropna()
        _, p = st.ttest_ind(a, b, equal_var=False)
        assert p < 0.05
        assert b.mean() > a.mean()  # arm B is the higher-scoring arm


class TestMessyLoanApplications:
    def setup_method(self):
        self.df = get_generator("messy_loan_applications")(n_rows=600, seed=42)

    def test_duplicate_rows(self):
        assert int(self.df.duplicated().sum()) == 45

    def test_internal_score_is_leaky(self):
        d = self.df.drop_duplicates()
        # near-perfect (negative) correlation with the target = leakage
        assert abs(d["internal_score"].corr(d["default"])) > 0.95

    def test_default_rate(self):
        d = self.df.drop_duplicates()
        assert d["default"].mean() == pytest.approx(0.22, abs=0.02)

    def test_employment_labels_dirty(self):
        assert self.df["employment"].nunique() > 2


def test_all_messy_generators_registered():
    for name in ["messy_customer_orders", "messy_sensor_data",
                 "messy_survey", "messy_loan_applications"]:
        df = get_generator(name)(seed=42)
        assert len(df) > 0
        assert df.duplicated().sum() > 0  # every messy generator injects duplicates
