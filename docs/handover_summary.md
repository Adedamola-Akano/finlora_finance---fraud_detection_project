# Handover Summary — Finlora Transaction Fraud Detection

**Project:** Transaction risk scoring model and analyst review queue for Finlora Fintech
**Status:** Core pipeline complete and deployed (Steps 1–7), plus a full round of fixes
following supervisor review (see Section 7). CSV upload enhancement still pending.

---

## 1. What This Project Delivers

A working, end-to-end fraud detection prototype that replaces binary rule-based monitoring
with a continuous, rankable fraud probability score:

- A cleaned, joined, analysis-ready dataset built from raw transaction and account data
- Documented evidence of which behavioral signals actually separate fraud from legitimate
  activity, ranked by strength
- Two trained and evaluated classifiers (Logistic Regression, Random Forest), compared
  fairly at multiple operating points, plus a third variant using SMOTE to empirically test
  an alternative imbalance-handling method
- Feature importance analysis for both models, with a chart
- A deployed Streamlit application giving analysts a prioritized, explainable review queue,
  with currency-standardized amounts and no raw transaction IDs cluttering the display

Full detail on each phase lives in the documents and notebooks referenced throughout this
summary — this document is the map connecting them, not a replacement for them.

## 2. Project Structure

```
finlora_fintech/
├── data/
│   ├── raw/                        ← original CSVs, untouched
│   └── processed/                  ← cleaned, engineered, and review-ready outputs
├── docs/
│   ├── problem_statement.md        ← Step 1
│   ├── eda_summary.md              ← Step 3 (all six signals, ranked, + currency note)
│   ├── model_evaluation_report.md  ← Step 5-6 (model comparison, feature importance, SMOTE)
│   ├── feature_importance_chart.png
│   └── handover_summary.md         ← this document
├── model/
│   └── saved_models/               ← trained model, scaler, feature schema (.pkl files)
├── notebooks/
│   ├── 01_data_cleaning.ipynb
│   ├── 02_eda.ipynb
│   ├── 03_feature_engineering.ipynb
│   └── 04_modeling.ipynb           ← includes model training, evaluation, and saving
└── app.py                          ← Streamlit review queue
```

## 3. Key Decisions Made Along the Way

- **`status` excluded from model features** (Step 2): "Reversed" transactions showed a
  33% fraud rate vs. ~1.7% for other statuses — but a transaction's status often only
  resolves *after* the fact, making it a data leakage risk rather than a genuine
  at-scoring-time signal.
- **Class weighting over SMOTE, empirically validated** (Step 5, revisited in review round):
  `class_weight='balanced'` was used to address the 2.66% fraud imbalance. A SMOTE variant
  was later trained and evaluated side by side to directly test this choice — the two
  approaches perform statistically equivalently (see `model_evaluation_report.md` Section
  8), confirming class weighting as the simpler, lower-risk choice without sacrificing
  performance.
- **`is_new_device` nulls filled with 0, not 1** (Step 4): EDA showed missing device data
  sits at baseline fraud rate, while genuinely new devices show a real elevated rate.
- **No train/validation/test split** (Step 5): a 75/25 stratified train-test split was used
  given the fixed model configurations specified and the limited fraud-positive sample size.
- **Logistic Regression selected as the primary deployed model** (Step 6): matches or beats
  Random Forest at every recall operating point except the most aggressive (90% recall).
- **`amount_to_avg_ratio` winsorized at the 99th percentile** (review round): extreme
  outliers (max 31,762x baseline) were causing some fraud probabilities to mathematically
  saturate at exactly 1.000000. Capping at 74.58 (99th percentile, affecting 1% of rows)
  preserved ranking behavior while resolving this.
- **Scaled features clipped to +/-5 standard deviations** (review round): winsorizing alone
  did not fully resolve saturation - `transaction_velocity_1h`, a heavily skewed feature
  (98.9% zero), produces extreme standardized z-scores for its rare non-zero values even
  though the raw values themselves are small. Clipping all scaled features post-`StandardScaler`
  addresses this mechanism generally, rather than chasing individual raw features one at a time.
- **Currency investigated, not altered in modeling**: confirmed every account transacts in
  exactly one currency consistently, so `amount_to_avg_ratio` (always account-relative)
  remained valid throughout. Added `amount_usd` as a display-only standardized figure for
  the Streamlit queue, where raw multi-currency amounts would otherwise look misleadingly
  comparable. See `eda_summary.md` for the full investigation and a caught merge bug
  (`currency_x`/`currency_y`) found along the way.

## 4. What the Model Actually Learned

**EDA findings** (ranked by strength, full detail in `docs/eda_summary.md`):

| Signal | Strength |
|---|---|
| Transaction velocity | Very strong (near-deterministic in this dataset) |
| Amount-to-average deviation | Strong (~6x median shift) |
| Merchant category | Strong (Wire Transfer, Payroll Transfer, Crypto Exchange riskiest) |
| Device novelty (new device) | Moderate |
| Channel | Weak-to-moderate |
| Cross-border activity | Weak |
| Device on record (missing) | No signal |

**Model feature importance** (full detail in `model_evaluation_report.md` Section 7): both
deployed models agree that `amount_to_avg_ratio` and `transaction_velocity_1h` dominate, but
weigh them differently - Logistic Regression gives `amount_to_avg_ratio` nearly 7x the
weight of velocity, while Random Forest treats them as almost equally important. This
reflects a structural difference in how each algorithm captures a smooth linear
relationship versus a sharp threshold effect, not a disagreement about the underlying data.

## 5. Known Limitations and Caveats

- **Synthetic/prototype data**: not live production fraud data (explicitly out of scope).
  Real-world performance, especially the near-perfect separation seen for
  `transaction_velocity_1h`, may not replicate on real transaction data.
- **Some probabilities remain very close to 1** (e.g. 0.999998) when multiple strong
  signals combine on the same transaction (e.g. high velocity + high amount deviation +
  a risky merchant category). This is expected, genuine model confidence, not a
  calibration bug - distinct transactions now produce distinct values rather than all
  pegging to an identical 1.000000, which was the original issue (see Section 7).
- **Fixed model configuration**: Random Forest was trained per the brief's specification
  rather than tuned; a different configuration could change the Step 6 comparison.
- **No live scoring endpoint, analyst feedback loop, or retraining pipeline** - explicitly
  out of scope per the original problem statement.
- **Exchange rates for `amount_usd` are a single current-rate snapshot**, not the historical
  rate on each transaction's actual date - a documented simplification, not a precision claim.

## 6. Suggested Next Steps

1. **CSV upload enhancement** (not yet built): allow analysts to upload a cleaned-format
   transactions CSV for on-demand scoring, rather than only viewing the fixed test set.
   Requires applying the same encoding as `03_feature_engineering.ipynb`, reindexing against
   the saved `feature_columns.pkl` schema (filling missing category columns with 0), and
   applying the same winsorizing cap and scaled-feature clipping used in training.
2. **SHAP-based explainability** (optional, raised in review but not required): would
   provide a more rigorous, model-agnostic alternative to the current coefficient-based
   explanation, and would be close to necessary if Random Forest were ever chosen as the
   primary model instead of Logistic Regression, since it lacks simple linear coefficients.
3. **Threshold selection UI**: let an analyst adjust the operating recall/precision point
   interactively, using the precision-at-recall analysis already computed in Step 6.
4. **Scoring endpoint and monitoring**: package the chosen model behind an API, log analyst
   outcomes to build a growing labeled dataset, and establish a retraining cadence.
5. **Revisit Random Forest vs. Logistic Regression** if the business adopts an aggressive
   (>=90% recall) fraud policy.

## 7. Supervisor Review Round - Issues Raised and Resolved

A review of the initial deliverable surfaced five items, all addressed:

| Item Raised | Resolution |
|---|---|
| "How did we treat class imbalance?" / requested SMOTE | Implemented SMOTE as a third model variant, evaluated identically to the other two. Found statistically equivalent to class weighting - see Section 3 and `model_evaluation_report.md` Section 8. |
| Feature importance not shown | Added global feature importance analysis (coefficient magnitude for Logistic Regression, built-in `feature_importances_` for Random Forest) with a comparison chart - `model_evaluation_report.md` Section 7. |
| Currency column - could affect `amount` | Investigated: confirmed each account uses one currency consistently, so `amount_to_avg_ratio` was never affected. Added `amount_usd` for display comparability. Caught and fixed an unrelated merge bug (`currency_x`/`currency_y` duplicate columns) in the process. |
| Streamlit shows test data, not future predictions | Root issue acknowledged; CSV upload for on-demand scoring of new transactions identified as the fix, carried forward to Section 6 (not yet built). |
| Transaction ID shouldn't be in the interface; fraud probability showing exactly 1.000000 | Removed `transaction_id` from the main table (kept available internally for the "Explain" dropdown via a separate reference to `data`, avoiding a `KeyError` this change initially caused). Root-caused the saturated probability to two compounding issues - extreme outliers in `amount_to_avg_ratio` and extreme standardized values from the skewed `transaction_velocity_1h` feature - fixed via winsorizing and scaled-feature clipping respectively, and found/fixed an inconsistency where one of two scaling code paths in `app.py` had the clipping fix applied and the other didn't. |

## 8. How to Run This Project

```powershell
# Launch the review queue app (adjust interpreter path if needed - see note below)
streamlit run app.py
```

**Note:** this project uses a specific Python interpreter
(`C:\Program Files\Python314\python3.14t.exe`) that differs from the terminal's default
`python`. If `streamlit run app.py` fails with a missing-module error, use:
```powershell
& "C:\Program Files\Python314\python3.14t.exe" -m streamlit run app.py
```

To retrain or re-run any phase, execute the notebooks in order (`01` through `04`) - each
reads from the previous phase's saved output in `data/processed/`. Any change to feature
engineering (Step 4) requires re-running `04_modeling.ipynb` afterward to keep the saved
models, scaler, and review queue consistent with the current data.