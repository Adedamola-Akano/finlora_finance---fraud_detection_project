# Handover Summary — Finlora Transaction Fraud Detection

**Project:** Transaction risk scoring model and analyst review queue for Finlora Fintech
**Status:** Core pipeline complete and deployed (Steps 1–7). One enhancement (CSV upload)
paused mid-design; see Section 6.

---

## 1. What This Project Delivers

A working, end-to-end fraud detection prototype that replaces binary rule-based monitoring
with a continuous, rankable fraud probability score:

- A cleaned, joined, analysis-ready dataset built from raw transaction and account data
- Documented evidence of which behavioral signals actually separate fraud from legitimate
  activity, ranked by strength
- Two trained and evaluated classifiers (Logistic Regression, Random Forest), compared
  fairly at multiple operating points rather than a single threshold
- A deployed Streamlit application giving analysts a prioritized, explainable review queue

Full detail on each phase lives in the documents and notebooks referenced throughout this
summary — this document is the map connecting them, not a replacement for them.

## 2. Project Structure

finlora_fintech/
├── data/
│ ├── raw/ ← original CSVs, untouched
│ └── processed/ ← cleaned, engineered, and review-ready outputs
├── docs/
│ ├── problem_statement.md ← Step 1
│ ├── eda_summary.md ← Step 3 (all six signals, ranked)
│ ├── model_evaluation_report.md ← Step 5–6 (model comparison and recommendation)
│ └── handover_summary.md ← this document
├── model/
│ └── saved_models/ ← trained model, scaler, feature schema (.pkl files)
├── notebooks/
│ ├── 01_data_cleaning.ipynb
│ ├── 02_eda.ipynb
│ ├── 03_feature_engineering.ipynb
│ └── 04_modeling.ipynb ← includes model training, evaluation, and saving
└── app.py ← Streamlit review queue


## 3. Key Decisions Made Along the Way

These are worth carrying forward, since each reflects a deliberate choice rather than a
default:

- **`status` excluded from model features** (Step 2): "Reversed" transactions showed a
  33% fraud rate vs. ~1.7% for other statuses — but a transaction's status often only
  resolves *after* the fact, making it a data leakage risk rather than a genuine
  at-scoring-time signal.
- **Class weighting over SMOTE** (Step 5): `class_weight='balanced'` (and
  `balanced_subsample` for Random Forest) was used to address the 2.66% fraud imbalance,
  rather than synthetic oversampling — avoiding the risk of generating unrealistic
  synthetic fraud patterns, and consistent with the balanced-subsampling approach already
  specified for Random Forest.
- **`is_new_device` nulls filled with 0, not 1** (Step 4): EDA showed missing device data
  sits at baseline fraud rate, while genuinely new devices show a real elevated rate.
  Filling with 1 would have falsely inflated risk on rows the data shows are not actually
  elevated.
- **No train/validation/test split** (Step 5): a 75/25 stratified train-test split was used
  instead of a three-way split, given the fixed model configurations specified (no extensive
  hyperparameter search) and the limited size of the fraud-positive sample (3,352 cases).
- **Logistic Regression selected as the primary deployed model** (Step 6): despite Random
  Forest being specified as the "primary prototype," the evaluation showed Logistic
  Regression matches or beats Random Forest at every recall operating point except the most
  aggressive (90% recall) — the added complexity of Random Forest isn't justified except
  under that specific risk posture. Full reasoning in `model_evaluation_report.md`.

## 4. What the Model Actually Learned (Summary of EDA Findings)

Ranked by strength, full detail in `docs/eda_summary.md`:

| Signal | Strength |
|---|---|
| Transaction velocity | Very strong (near-deterministic in this dataset) |
| Amount-to-average deviation | Strong (~6x median shift; drives most flagged transactions) |
| Merchant category | Strong (Wire Transfer, Payroll Transfer, Crypto Exchange riskiest) |
| Device novelty (new device) | Moderate |
| Channel | Weak-to-moderate |
| Cross-border activity | Weak |
| Device on record (missing) | No signal |

The deployed app's explainability output consistently reflects this: `amount_to_avg_ratio`
dominates most flagged transactions' contribution breakdown, sometimes so strongly that the
sigmoid probability saturates to exactly 1.000000 — a mathematical consequence of extreme
outlier values, not a modeling error (see Section 5).

## 5. Known Limitations and Caveats

- **Synthetic/prototype data**: this project uses provided sample data, not live production
  fraud data (explicitly out of scope). Real-world performance, especially the near-perfect
  separation seen for `transaction_velocity_1h`, may not replicate on real transaction data.
- **Saturated probabilities**: some flagged transactions show a fraud probability of exactly
  1.000000 due to very large feature contributions pushing the sigmoid function to its
  numerical limit. This reflects extreme amount-deviation values in the data, not an error.
- **Fixed model configuration**: Random Forest was trained per the brief's specification
  (300 trees, max depth 10) rather than tuned; a different configuration could change the
  Step 6 comparison.
- **No live scoring endpoint, analyst feedback loop, or retraining pipeline** — explicitly
  out of scope per the original problem statement (Section 6 of
  `docs/problem_statement.md`).

## 6. Suggested Next Steps

In rough priority order:

1. **CSV upload enhancement** (paused mid-design): allow analysts to upload a cleaned-format
   transactions CSV (human-readable columns + engineered numeric features, not yet one-hot
   encoded) for on-demand scoring, rather than only viewing the fixed test set. Requires
   applying the same encoding as `03_feature_engineering.ipynb`, then reindexing the result
   against the saved `feature_columns.pkl` schema (filling any missing category columns with
   0) before scoring, since an upload may not contain every category value seen in training.
2. **Threshold selection UI**: let an analyst adjust the operating recall/precision point
   interactively in the app, using the precision-at-recall analysis already computed in
   Step 6, rather than only showing the model's default 0.5 threshold.
3. **Scoring endpoint and monitoring**, as outlined in the original Step 7 plan: package the
   chosen model behind an API, log analyst outcomes (confirmed fraud vs. false positive) to
   build a growing labeled dataset, and establish a periodic retraining cadence.
4. **Revisit the Random Forest vs. Logistic Regression decision** if the business adopts an
   aggressive (≥90% recall) fraud policy, per the Step 6 recommendation.

## 7. How to Run This Project

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
reads from the previous phase's saved output in `data/processed/`.