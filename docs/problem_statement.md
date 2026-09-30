# Problem Statement — Finlora Transaction Fraud Risk Scoring

## 1. Business Problem

Finlora currently relies on binary rule-based monitoring to flag potentially fraudulent
transactions. As transaction volume grows, this approach misses subtler fraud patterns that
don't trip a hard-coded rule but are still anomalous when viewed across multiple signals at
once (spend behavior, velocity, device, geography). Rules also produce all-or-nothing flags,
giving analysts no way to prioritize review effort by how risky a transaction actually is.

## 2. Data Science Framing

This is translated into a **binary classification problem**: for each transaction, predict
whether it is `fraud` (1) or `legitimate` (0), and — more usefully than the raw class label —
produce a **continuous fraud probability score** that can be used to rank transactions by risk
rather than just tag them.

- **Unit of analysis:** one transaction
- **Target variable:** fraud label (binary)
- **Output:** fraud probability per transaction (0–1), used to build a ranked review queue
- **Positive class:** fraud (a minority class — confirmed at 2.66% during EDA)

## 3. Objectives

1. **Measurement** — Build a transaction risk scoring model that assigns a fraud probability
   to every transaction, replacing binary rule triggers with a continuous, rankable signal.
2. **Analysis** — Identify the behavioral drivers of fraud (amount deviation, velocity, device
   novelty, cross-border activity, channel, merchant category) via feature importance and
   pattern analysis on flagged vs. legitimate transactions.
3. **Prediction** — Train and validate a baseline ML classifier: Logistic Regression as an
   interpretable benchmark, then Random Forest as the primary prototype. Validate with
   precision, recall, F1, and ROC-AUC on a held-out test set.
4. **Application** — Deploy the model to Streamlit as a prioritized, explainable review queue,
   so analysts see the highest-risk transactions first along with the signals driving each flag.

## 4. Data Sources

| Source | Description | Grain |
|---|---|---|
| `finlora_transactions.csv` | Transaction-level records | 1 row per transaction |
| `finlora_accounts.csv` | Account-level attributes | 1 row per account |

Joined on `account_id` to build a single transaction-level modeling table with account
context attached.

## 5. Scope

### In scope
- Fraud-probability risk scoring model (Logistic Regression baseline + Random Forest)
- Features: spend baseline deviation, velocity, device novelty, cross-border activity,
  channel, merchant category
- Feature importance & pattern analysis on flagged vs. legitimate transactions
- Validation via precision, recall, F1, ROC-AUC on a held-out test set
- Deployment to Streamlit as a prioritized, explainable review queue

### Out of scope
- Live integration with Finlora's real payment/processing systems
- Real production-labeled fraud data
- Automated blocking or step-up verification
- Analyst feedback loop & model retraining pipeline
- Deep learning/ensemble models beyond Logistic Regression & Random Forest
- Credit risk, churn, or budgeting models
- Dashboard auth, hosting hardening, or regulatory sign-off

## 6. Project Phases

| Step | Phase | Deliverable |
|---|---|---|
| 1 | Problem Framing | This document |
| 2 | Data Cleaning | Clean, joined, analysis-ready dataset in `data/processed/` |
| 3 | Exploratory Data Analysis | EDA summary report (fraud vs. legitimate patterns) |
| 4 | Feature Engineering | Feature set: `amount_to_avg_ratio`, `transaction_velocity_1h`, `is_new_device`, `is_cross_border`, one-hot encoded categoricals |
| 5 | Model Development | Logistic Regression (baseline) + Random Forest (primary), 75/25 stratified split |
| 6 | Evaluation | Precision, recall, F1, ROC-AUC, confusion matrix, precision at fixed recall (70/80/90%) |
| 7 | Deployment & Monitoring Considerations | Streamlit review queue; notes on scoring endpoint, logging, retraining cadence (next phase, not built in this prototype) |

## 7. Success Criteria for This Prototype

- Both models trained and evaluated on the same held-out test set, with results directly
  comparable.
- Random Forest (primary model) achieves meaningfully better ROC-AUC / recall-at-precision
  than the Logistic Regression baseline — otherwise the added complexity isn't justified.
- Every flagged transaction in the Streamlit queue is explainable: the analyst can see which
  features pushed the score up, not just the score itself.
- Every phase's output is reproducible from `data/raw/` forward — no manual, undocumented data
  edits.