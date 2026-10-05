# Handover Summary — Finlora Transaction Fraud Detection

**Project:** Transaction risk scoring model and analyst review queue for Finlora Fintech
**Status:** Core pipeline complete and deployed (Steps 1–7), including a full round of
fixes following supervisor review (Section 7) and the CSV upload enhancement (Section 8).

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
- A CSV upload feature allowing analysts to score new, previously unseen transactions on
  demand, not just replay the fixed test set

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
│   └── saved_models/               ← trained model, scaler, feature schema, winsorizing cap
├── notebooks/
│   ├── 01_data_cleaning.ipynb
│   ├── 02_eda.ipynb
│   ├── 03_feature_engineering.ipynb
│   └── 04_modeling.ipynb           ← includes model training, evaluation, and saving
└── app.py                          ← Streamlit review queue + CSV upload scoring
```

## 3. Key Decisions Made Along the Way

- **`status` excluded from model features** (Step 2): a transaction's status often only
  resolves *after* the fact ("Reversed" showed 33% fraud vs. ~1.7% elsewhere), making it a
  data leakage risk rather than a genuine at-scoring-time signal.
- **Class weighting over SMOTE, empirically validated** (Step 5, revisited in review round):
  a SMOTE variant was trained and evaluated side by side with the original class-weighted
  model — the two perform statistically equivalently (see `model_evaluation_report.md`
  Section 8), confirming class weighting as the simpler, lower-risk choice.
- **`is_new_device` nulls filled with 0, not 1** (Step 4): missing device data sits at
  baseline fraud rate, while genuinely new devices show a real elevated rate; this exact
  logic had to be replicated separately in the CSV upload path (Section 8).
- **No train/validation/test split** (Step 5): a 75/25 stratified split was used given the
  fixed model configurations specified and the limited fraud-positive sample size.
- **Logistic Regression selected as the primary deployed model** (Step 6): matches or beats
  Random Forest at every recall operating point except the most aggressive (90% recall).
- **`amount_to_avg_ratio` winsorized at the 99th percentile** (review round): extreme
  outliers (max 31,762x baseline) were causing some fraud probabilities to mathematically
  saturate at exactly 1.000000. The cap value (74.58) is persisted as its own artifact
  (`amount_ratio_cap.pkl`) so new uploads reuse the training-derived cap rather than
  computing their own from a potentially tiny or skewed upload sample.
- **Scaled features clipped to ±5 standard deviations** (review round): winsorizing alone
  did not fully resolve saturation — `transaction_velocity_1h`, heavily skewed (98.9%
  zero), produces extreme standardized z-scores for its rare non-zero values. Scaling and
  clipping were consolidated into one shared `scale_and_clip()` function used by every
  scoring path in `app.py`, after an inconsistency was found where one path had the fix and
  another didn't.
- **Currency investigated, not altered in modeling**: every account transacts in exactly
  one currency consistently, so `amount_to_avg_ratio` (always account-relative) remained
  valid. Added `amount_usd` as a display-only standardized figure. Caught and fixed an
  unrelated merge bug (`currency_x`/`currency_y`) along the way.

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
deployed models agree `amount_to_avg_ratio` and `transaction_velocity_1h` dominate, but
weigh them differently — Logistic Regression gives `amount_to_avg_ratio` nearly 7x the
weight of velocity, while Random Forest treats them as almost equally important, reflecting
a structural difference in how each algorithm captures linear versus threshold effects.

## 5. Known Limitations and Caveats

- **Synthetic/prototype data**: not live production fraud data. Real-world performance,
  especially the near-perfect separation seen for `transaction_velocity_1h`, may not
  replicate on real transaction data.
- **Some probabilities remain very close to 1** (e.g. 0.999998) when multiple strong
  signals combine on the same transaction — expected, genuine model confidence, not a
  calibration bug (see Section 7).
- **Fixed model configuration**: Random Forest was trained per the brief's specification
  rather than tuned.
- **No live scoring endpoint, analyst feedback loop, or retraining pipeline** — explicitly
  out of scope.
- **Exchange rates for `amount_usd` are a single current-rate snapshot**, not the historical
  rate on each transaction's actual date.
- **CSV upload expects a specific "cleaned" format** (same columns as
  `data/processed/finlora_cleaned.csv`, pre-encoding) — it does not accept raw
  transaction/account files directly, and does not perform the Step 2 cleaning/join steps.

## 6. Suggested Next Steps

1. **SHAP-based explainability** (optional, raised in review but not required): a more
   rigorous, model-agnostic alternative to the current coefficient-based explanation.
2. **Threshold selection UI**: let an analyst adjust the operating recall/precision point
   interactively, using the precision-at-recall analysis from Step 6.
3. **Scoring endpoint and monitoring**: package the chosen model behind an API, log analyst
   outcomes to build a growing labeled dataset, and establish a retraining cadence.
4. **Revisit Random Forest vs. Logistic Regression** if the business adopts an aggressive
   (≥90% recall) fraud policy.
5. **Extend CSV upload to accept raw (pre-cleaning) files**, running the Step 2 join and
   cleaning logic on upload, if analysts need to score data that hasn't been pre-processed.

## 7. Supervisor Review Round — Issues Raised and Resolved

| Item Raised | Resolution |
|---|---|
| "How did we treat class imbalance?" / requested SMOTE | Implemented SMOTE as a third model variant, evaluated identically to the other two. Found statistically equivalent to class weighting. |
| Feature importance not shown | Added global feature importance analysis for both models with a comparison chart. |
| Currency column — could affect `amount` | Investigated: confirmed each account uses one currency consistently. Added `amount_usd` for display comparability; fixed an unrelated merge bug found in the process. |
| Streamlit shows test data, not future predictions | Resolved via the CSV upload feature (Section 8) — analysts can now score new transactions on demand. |
| Transaction ID shouldn't be in the interface; fraud probability showing exactly 1.000000 | Removed `transaction_id` from the main table display. Root-caused the saturated probability to extreme outliers plus a skewed-feature scaling effect; fixed via winsorizing and scaled-feature clipping; found and fixed an inconsistency where one of two scoring code paths had the clipping fix applied and the other didn't. |

## 8. CSV Upload Enhancement

Analysts can now upload a cleaned-format transactions CSV (same column structure as
`data/processed/finlora_cleaned.csv`) directly in the Streamlit app and receive a ranked,
scored review queue for those specific transactions — rather than only viewing the fixed
held-out test set.

**Implementation notes:**
- Validates required columns are present before processing; shows a clear error listing
  any missing columns rather than crashing.
- Replicates the `is_new_device` null-handling decision from Step 4 (a bug initially
  missed — the first test upload failed with a `NaN`-related error until this was added).
- Applies the **saved** winsorizing cap (`amount_ratio_cap.pkl`), not a freshly computed
  one, so a single upload's own outliers can't define a new "normal" range.
- One-hot encodes, then **reindexes** against the saved `feature_columns` schema with
  `fill_value=0` — this means an upload missing some category (e.g. no USSD transactions
  in a given batch) still produces a valid, correctly-shaped input instead of crashing or
  silently misaligning columns.
- Uses the same shared `scale_and_clip()` function as every other scoring path in the app.

Tested successfully on a 20-row sample pulled from `finlora_cleaned.csv`.

## 9. How to Run This Project

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

To retrain or re-run any phase, execute the notebooks in order (`01` through `04`) — each
reads from the previous phase's saved output in `data/processed/`. Any change to feature
engineering (Step 4) requires re-running `04_modeling.ipynb` afterward, and re-saving the
winsorizing cap artifact, to keep the app consistent with the current data.