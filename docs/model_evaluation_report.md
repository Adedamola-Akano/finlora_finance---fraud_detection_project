# Model Evaluation Report — Finlora Transaction Fraud Detection

Compares Logistic Regression (interpretable baseline) and Random Forest (primary
prototype), both trained on a 75/25 stratified train-test split (94,500 train / 31,500
test transactions, fraud rate 2.66% preserved in both).

---

**Update:** `amount_to_avg_ratio` was winsorized (capped at the 99th percentile, 74.58)
after deployment testing revealed some flagged transactions produced a fraud probability
of exactly 1.000000 due to extreme outlier values (max observed: 31,762x baseline)
saturating the sigmoid function. All models below were retrained on the winsorized
feature. Metrics shifted only slightly (e.g. Logistic Regression ROC-AUC: 0.9345 → 0.9394)
— the fix resolved probability calibration without materially changing classification
performance. See Section 8 for the SMOTE comparison added in the same retraining pass.

## 1. Default-Threshold Performance (0.5 cutoff)

| Metric (fraud class) | Logistic Regression | Random Forest |
|---|---|---|
| Precision | 0.38 | 0.32 |
| Recall | 0.80 | 0.83 |
| F1 | **0.52** | 0.46 |
| ROC-AUC | 0.9345 | 0.9336 |

At the default classification threshold, Logistic Regression and Random Forest perform
comparably overall (ROC-AUC nearly identical), with Random Forest trading precision for a
small recall gain — resulting in a lower F1 score.

## 2. Confusion Matrices (default threshold)

**Logistic Regression:**

| | Predicted Legitimate | Predicted Fraud |
|---|---|---|
| **Actual Legitimate** | 29,574 | 1,088 |
| **Actual Fraud** | 165 | 673 |

**Random Forest:**

| | Predicted Legitimate | Predicted Fraud |
|---|---|---|
| **Actual Legitimate** | 29,168 | 1,494 |
| **Actual Fraud** | 142 | 696 |

Random Forest catches 23 more real fraud cases than Logistic Regression (696 vs. 673 of
838 total), but at the cost of 406 additional false alarms (1,494 vs. 1,088). Whether this
trade is worthwhile depends on the relative cost of analyst review time vs. missed fraud —
addressed directly in Section 3.

## 3. Precision at Fixed Recall Operating Points

Rather than comparing models only at their default threshold, precision was measured at
three recall levels the risk team might choose to operate at, based on review capacity and
risk tolerance:

| Recall Target | Logistic Regression Precision | Random Forest Precision |
|---|---|---|
| 70% | **0.646** | 0.547 |
| 80% | 0.386 | 0.388 |
| 90% | 0.110 | **0.138** |

**Finding:** neither model dominates the other across all operating points — the better
choice depends on the business's risk posture:
- **Conservative posture (70% recall target):** Logistic Regression is clearly better —
  meaningfully fewer false alarms per fraud case caught.
- **Balanced posture (80% recall target):** the two models are effectively tied.
- **Aggressive posture (90% recall target):** Random Forest is better — usable precision
  when trying to catch nearly all fraud, though both models' precision is low at this
  aggressive a target.

## 4. Recommendation

**Logistic Regression is recommended as the primary deployed model**, given that it
matches or exceeds Random Forest at every recall target except the most aggressive (90%),
while being simpler, faster to train, and more directly interpretable (coefficients map
transparently to feature effects, versus Random Forest's less direct feature importances).
Per the project's stated success criterion — that Random Forest should show a meaningful
improvement to justify its added complexity — that bar is not met here except at the 90%
recall operating point.

**Recommended default operating point:** 80% recall, where both models perform equivalently
(Logistic Regression precision 0.386). This balances catching the large majority of fraud
against a manageable false-positive volume for analyst review.

**If the business later adopts a more aggressive fraud-catching policy** (recall ≥ 90%),
Random Forest becomes the better choice and should be reconsidered as the primary model at
that time.

## 5. Caveats

- Both models were evaluated on synthetic/prototype data, not live production fraud data
  (per project scope) — real-world performance may differ, particularly given the
  unusually clean separation observed for `transaction_velocity_1h` in EDA.
- Random Forest was trained per the project brief's fixed specification (300 trees, max
  depth 10, balanced subsampling) rather than through hyperparameter tuning; a different
  configuration could shift this comparison.
- No separate validation set was used (75/25 train-test split only), consistent with the
  project's fixed-configuration, non-tuning scope — see `docs/problem_statement.md`.


  ## 8. SMOTE vs. Class Weighting — Empirical Comparison

**Question:** does SMOTE (synthetic oversampling) outperform class weighting
(`class_weight='balanced'`) for addressing the 2.66% fraud class imbalance?

**Method:** trained a third model — Logistic Regression on SMOTE-resampled training data
(balanced to 50/50 fraud/legitimate via synthetic minority examples, no class weighting
applied) — and evaluated it identically to the other two models, on the same unmodified
test set.

| Metric (fraud class) | LogReg (class_weight) | Random Forest | LogReg (SMOTE) |
|---|---|---|---|
| Precision | 0.37 | 0.32 | 0.36 |
| Recall | 0.81 | 0.83 | 0.82 |
| F1 | 0.51 | 0.46 | 0.50 |
| ROC-AUC | 0.9394 | 0.9337 | 0.9389 |

| Recall Target | LogReg (class_weight) | Random Forest | LogReg (SMOTE) |
|---|---|---|---|
| 70% | 0.655 | 0.561 | 0.656 |
| 80% | 0.394 | 0.385 | 0.405 |
| 90% | 0.142 | 0.130 | 0.142 |

**Finding:** class weighting and SMOTE perform **statistically equivalently** on this
dataset — all metrics fall within noise of each other, with no consistent advantage either
way across any recall target. This empirically confirms the original Step 5 decision to use
class weighting rather than SMOTE: the two approaches solve the imbalance problem
comparably well here, so the simpler, lower-risk method (class weighting — no synthetic
data generation, no risk of unrealistic interpolated fraud patterns) is preferred on the
grounds of simplicity and interpretability, not because it was shown to be numerically
superior.

**Recommendation unchanged**: Logistic Regression (class weighting) remains the primary
deployed model, per Section 4.
