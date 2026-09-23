# EDA Summary — Finlora Transaction Fraud Detection

Profiles transaction-level signals by fraud label (`is_fraud`) to identify which features
carry a genuine fraud signal before they're used in feature engineering and modeling.
Dataset: `data/processed/finlora_cleaned.csv` (126,000 transactions, fraud rate 2.66%).

---

## Note: `merchant_name` Missing Values Explained

Investigating missing `merchant_name` values (28,610 rows) after refining the fill logic
revealed the pattern is structural, not random: ~97% of missing merchant names come from
`Payroll Transfer` and `P2P Transfer` transactions, which genuinely have no associated
merchant (money movement between accounts/employer, not a purchase). This confirms
`merchant_name` missingness carries no fraud signal of its own — it's a category artifact,
not a data quality issue — and validates filling with `Unknown (category)` rather than a
bare placeholder.

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


## 2. Transaction Velocity (`transaction_velocity_1h`)

**Question:** Do fraud transactions cluster with unusually high transaction counts in the
trailing 1-hour window?

**Method:** Compared transaction_velocity_1h between legitimate and fraud transactions,
then computed fraud rate at each velocity level directly (crosstab normalized by row).

**Result:**

| Velocity (txns in trailing 1h) | Legitimate | Fraud |
|---|---|---|
| 0 | 98.3% | 1.7% |
| 1 | 7.4% | 92.6% |
| 2 | 11.5% | 88.5% |
| 3 | 0% | 100% |

**Finding:** Velocity is the **strongest signal identified so far**. 98.9% of all
transactions have velocity 0 and sit at the baseline ~2% fraud rate, but any transaction
with velocity ≥1 is overwhelmingly likely to be fraud (88–100%). This matches a common
real-world fraud pattern — rapid repeat transactions on a compromised account or card
before it's caught. Note: velocity is computed from transaction timing at the moment of
the transaction, so — unlike `status` — it does not carry the same look-ahead/leakage risk;
this information is genuinely available at scoring time.

**Caveat:** the near-binary separation here is unusually clean for a real-world signal.
Since this is prototype/synthetic data (not live production fraud data, per project scope),
this pattern should be treated as a strong but possibly dataset-specific signal — real-world
velocity effects are typically directional rather than this deterministic.


## 3. Device Novelty (`has_device_on_record`, `is_new_device`)

**Question:** Does missing device data, or transacting from a new/unrecognized device,
correlate with fraud?

**Method:** Two separate checks — first whether having no device on record at all
correlates with fraud, then (among transactions with a device recorded) whether the device
being new correlates with fraud.

**Result:**

| | Legitimate | Fraud |
|---|---|---|
| No device on record | 97.6% | 2.4% |
| Has device on record | 97.3% | 2.7% |

| | Legitimate | Fraud |
|---|---|---|
| Known device | 97.4% | 2.6% |
| New device | 94.1% | **5.9%** |

**Finding:** Simply having no device on record is **not** a meaningful signal — both rows
sit at baseline, consistent with the earlier finding that this missingness is essentially
random. However, among transactions with a recorded device, a **new** device more than
doubles the fraud rate (2.6% → 5.9%). This is a real but moderate signal — most new-device
transactions are still legitimate, so it's more useful in combination with other features
than as a standalone flag.

*(Additional sections — cross-border activity, channel, merchant
category — to be added as each is analyzed.)*git 