# EDA Summary — Finlora Transaction Fraud Detection

Profiles transaction-level signals by fraud label (`is_fraud`) to identify which features
carry a genuine fraud signal before they're used in feature engineering and modeling.
Dataset: `data/processed/finlora_cleaned.csv` (126,000 transactions, fraud rate 2.66%).

---

## 1. Amount Deviation (`amount_to_avg_ratio`)

**Question:** Do fraud transactions tend to be unusually large relative to the account's
own spending baseline?

**Method:** Compared the distribution of `amount_to_avg_ratio` between legitimate
(`is_fraud = 0`) and fraud (`is_fraud = 1`) transactions using summary statistics and a
log-scale boxplot.

**Result:**

| | Legitimate | Fraud |
|---|---|---|
| Median | 0.95x | **6.04x** |
| Mean | 3.98x | 152.12x |
| 75th percentile | 1.73x | 56.53x |

**Finding:** Amount deviation is a **meaningful fraud signal**. A typical legitimate
transaction sits right around the account's normal spend (~1x baseline), while a typical
fraud transaction runs at roughly **6x** the account's baseline. The boxplot confirms this
isn't driven by a handful of extreme outliers — the fraud group's entire distribution
(box and median) sits visibly higher than the legitimate group's, not just its tail.

**Note on the data:** both groups' means are much higher than their medians (e.g. fraud:
mean 152 vs. median 6), indicating strong right-skew with some extreme high-ratio
transactions in both classes. The median is the more representative statistic here. This
skew is also why the modeling plan calls for standardizing features before Logistic
Regression — raw amount-ratio values span from near-zero to over 30,000x.

---

*(Additional sections — velocity, device novelty, cross-border activity, channel, merchant
category — to be added as each is analyzed.)*