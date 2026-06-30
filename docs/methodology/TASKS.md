# RealDataAgentBench Tasks

43 tasks across 5 categories. Each task is a YAML file under `tasks/<category>/`.

**Difficulty breakdown:** 9 easy · 22 medium · 12 hard.

Three tasks (`eda_011`, `feat_011`, `mod_011`, `stat_011`) are "messy" variants with intentionally dirty input data that must be cleaned before analysis.

---

## EDA (8 tasks)

| ID | Difficulty | Title | What it asks |
|----|-----------|-------|--------------|
| eda_001 | easy | Income Distribution Analysis | Compute mean/median/std, identify skew direction, recommend transformation |
| eda_002 | medium | Patient Records — Missing Data & Outlier Audit | Find missing rates, detect outliers via IQR/Z-score |
| eda_003 | hard | E-Commerce Confounding Variable Detection | Detect Simpson's Paradox — higher discounts appear to lower revenue, but it's segment-driven |
| eda_004 | medium | Breast Cancer Wisconsin | Explore 30-feature clinical dataset, identify top malignancy predictors |
| eda_005 | easy | Iris — Species Separability | Compute correlations, identify most separable features across 3 species |
| eda_006 | easy | Salary Survey | Skewness, which department has highest median salary |
| eda_007 | medium | Manufacturing Quality | Compare process variation (std) between two machines across shifts |
| eda_011 | medium | Dirty Orders Export | Audit raw data: duplicates, total revenue, missing values, outliers — data is uncleaned |

---

## Feature Engineering (9 tasks)

| ID | Difficulty | Title | What it asks |
|----|-----------|-------|--------------|
| feat_001 | easy | Polynomial Features for House Prices | Correlations, create ratio/interaction features, measure improvement |
| feat_002 | medium | Categorical Encoding for Attrition | One-hot + ordinal encoding, feature selection |
| feat_003 | medium | Datetime Features for Retail Sales | Parse dates, extract year/month/day_of_week, aggregate |
| feat_004 | hard | Feature Selection for Credit Risk | Near-zero variance removal, correlation matrix, recursive feature elimination |
| feat_005 | hard | Imbalanced Fraud Detection | Engineer zscore/ratio features on 5% fraud dataset |
| feat_006 | medium | Diabetes — Feature Correlation | Correlations, regression baseline on real medical dataset |
| feat_009 | medium | Attrition — Encoding & Importance | Label encode ordinal, one-hot nominal, rank feature importances |
| feat_010 | hard | Retail Sales — Lag & Rolling Features | Lag-7 and 7-day rolling mean for time series, train/test split |
| feat_011 | medium | Dirty Sensor Readings | Clean IoT data with non-random missingness, engineer summary features |

---

## ML Engineering (9 tasks)

| ID | Difficulty | Title | What it asks |
|----|-----------|-------|--------------|
| mod_001 | easy | Data Leakage Detection | Identify the leaked feature (approval_code) in a loan dataset |
| mod_002 | easy | K-Fold vs Hold-Out | Compare accuracy/AUC of single split vs 5-fold CV on noisy data |
| mod_003 | medium | Probability Calibration | Calibrate Random Forest probabilities (Platt/isotonic), compare Brier scores |
| mod_004 | medium | Ensemble Voting | Compare soft-vote ensemble vs 3 individual classifiers |
| mod_005 | hard | Nested CV | Non-nested vs nested cross-validation to quantify optimism bias |
| mod_006 | medium | Breast Cancer — CV vs Hold-Out | Quantify variance difference between single split and 5-fold on real clinical data |
| mod_009 | medium | Fraud Threshold Optimization | Optimize decision threshold for recall-weighted F-score on imbalanced fraud data |
| mod_010 | hard | Feature Stability via Bootstrap | Bootstrap 50 times, rank features by mean importance and stability |
| mod_011 | hard | Loan Default — Leakage Gate | Audit raw loan data for duplicates, target leakage, missing values before modeling |

---

## Modeling (8 tasks)

| ID | Difficulty | Title | What it asks |
|----|-----------|-------|--------------|
| model_001 | easy | Logistic Regression — Diabetes | Train/evaluate logistic regression, report accuracy + AUC |
| model_002 | medium | Random Forest — Wine Quality | Classify high_quality wine (quality ≥ 7), report AUC + top features |
| model_003 | medium | Ridge vs Lasso — Student Performance | Compare regularization methods on RMSE and feature sparsity |
| model_004 | hard | Gradient Boosting — Churn | GBM with full classification report + feature importance |
| model_005 | hard | Multi-Model Regression — Energy | Compare Linear, Random Forest, GBM on RMSE; identify best model |
| model_006 | medium | Wine Recognition — Multi-Class | 3-class classification on 178 samples with 13 chemical features |
| model_009 | medium | Wine Quality — Linear vs RF | Predict numeric quality score, compare RMSE of two models |
| model_010 | medium | House Prices — Ridge vs Lasso | Compare RMSE and count how many features Lasso zeros out |

---

## Statistical Inference (9 tasks)

| ID | Difficulty | Title | What it asks |
|----|-----------|-------|--------------|
| stat_001 | easy | A/B Test — Conversion Rate | Conversion rates, absolute/relative lift, two-proportion z-test |
| stat_002 | medium | Clinical Trial — Drug Efficacy | t-test on blood pressure reduction drug vs placebo |
| stat_003 | hard | Salary Gap — Controlling Confounders | Raw gap + OLS regression controlling for experience/role/dept |
| stat_004 | medium | Time Series Decomposition | Trend direction, weekly seasonality, correlation with time |
| stat_005 | hard | Statistical Process Control | Defect rate per machine, chi-squared test, control chart limits |
| stat_006 | medium | Iris — One-Way ANOVA | ANOVA on petal length across 3 species, post-hoc test |
| stat_009 | medium | Salary — Mann-Whitney Test | Shapiro-Wilk normality check, then non-parametric gender comparison |
| stat_010 | easy | Attrition — Chi-Squared Test | 2×2 contingency table, chi-squared test for overtime vs attrition |
| stat_011 | medium | Dirty Survey — Two-Group Test | Clean inconsistent group labels + duplicates, then run a two-group test |
