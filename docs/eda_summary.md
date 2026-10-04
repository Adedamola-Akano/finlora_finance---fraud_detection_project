# EDA Summary — Finlora Transaction Fraud Detection

Profiles transaction-level signals by fraud label (`is_fraud`) to identify which features
carry a genuine fraud signal before they're used in feature engineering and modeling.
Dataset: `data/processed/finlora_cleaned.csv` (126,000 transactions, fraud rate 2.66%).

---

## Note: `merchant_name` Missing Values Explained

Investigating missing `merchant_name` values (28,610 rows) after refining the fill logicgit 
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


## 4. Cross-Border Activity (`is_cross_border`)

**Question:** Is fraud disproportionately cross-border?

**Method:** Compared fraud rate between domestic and cross-border transactions; checked
overall prevalence of cross-border activity.

**Result:**

| | Legitimate | Fraud |
|---|---|---|
| Domestic | 97.4% | 2.6% |
| Cross-border | 96.6% | 3.4% |

Cross-border transactions make up only 2.0% of all transactions.

**Finding:** Cross-border activity is a **weak** signal — fraud rate rises modestly (2.6% →
3.4%) but the effect is small compared to velocity or amount deviation, and the feature is
rare overall (only 2% of transactions). Direction is intuitive (cross-border carries more
risk), but this alone won't meaningfully separate fraud from legitimate activity.


## 5. Channel

**Question:** Does fraud concentrate in specific transaction channels?

**Method:** Fraud rate per channel, ranked highest to lowest, checked against transaction
volume to rule out small-sample noise.

**Result:**

| Channel | Transactions | Fraud Rate |
|---|---|---|
| API/Integration | 13,083 | 3.65% |
| Web Dashboard | 31,330 | 2.96% |
| Mobile App | 41,615 | 2.51% |
| Card Not Present | 17,422 | 2.34% |
| Card Present | 15,080 | 2.24% |
| USSD | 7,470 | 2.12% |

**Finding:** Channel is a **weak-to-moderate** signal. Fraud rate ranges from 2.12%
(USSD) to 3.65% (API/Integration) — about a 1.7x spread, all backed by solid transaction
volume (no small-sample noise). The ranking is intuitive: programmatic/API access carries
somewhat more fraud risk than direct human channels, while USSD (tightly tied to a
phone/SIM) is safest. Real but modest — comparable to cross-border activity, well below
velocity or amount deviation in strength.


## 6. Merchant Category

**Question:** Does fraud concentrate in specific merchant categories?

**Method:** Fraud rate per category, ranked highest to lowest, checked against transaction
volume.

**Result (highest and lowest risk categories):**

| Category | Transactions | Fraud Rate |
|---|---|---|
| Wire Transfer | 7,639 | 7.58% |
| Payroll Transfer | 17,117 | 5.59% |
| Crypto Exchange | 1,692 | 5.20% |
| ... | | |
| Groceries | 13,650 | 1.26% |
| Restaurants | 8,416 | 1.12% |

**Finding:** Merchant category is the **strongest categorical signal** identified — a ~6.8x
spread between riskiest (Wire Transfer) and safest (Restaurants) categories, all backed by
solid volume. The top three risky categories (Wire Transfer, Payroll Transfer, Crypto
Exchange) share a common trait: large, fast, hard-to-reverse fund movements — exactly what
fraud tends to target. Notably, P2P Transfer sits near baseline (2.54%) despite also lacking
a traditional merchant, showing that "no merchant involved" alone doesn't drive risk — it's
specifically the large/irreversible transfer pattern that does.

---

## Summary Across All Six Signals

| Signal | Strength |
|---|---|
| Transaction velocity | **Very strong** (near-deterministic; caveat: dataset may over-represent this) |
| Amount-to-average deviation | **Strong** (~6x median shift) |
| Merchant category | **Strong** (~6.8x spread; intuitive pattern) |
| Device novelty (new device) | **Moderate** (2.6% → 5.9%) |
| Channel | **Weak-to-moderate** (~1.7x spread) |
| Cross-border activity | **Weak** (2.6% → 3.4%) |
| Device on record (missing) | **No signal** |

These findings directly inform Step 4 (Feature Engineering) and the feature importance
analysis expected from the trained models in Step 5–6.


## Summary

Final feature set: 7 numeric features + 22 one-hot encoded categorical columns (from
account_type, kyc_tier, merchant_category, channel) = 29 features total.

Key decision: `is_new_device` nulls (missing device data) filled with 0 rather than 1,
based on EDA evidence that missing device data shows baseline fraud rate, while genuinely
new devices show a real elevated rate — filling with 1 would have falsely inflated risk on
rows the data shows are not actually elevated.

## Summary

Final feature set: 7 numeric features + 22 one-hot encoded categorical columns (from
account_type, kyc_tier, merchant_category, channel) = 29 features total.

Key decision: `is_new_device` nulls (missing device data) filled with 0 rather than 1,
based on EDA evidence that missing device data shows baseline fraud rate, while genuinely
new devices show a real elevated rate — filling with 1 would have falsely inflated risk on
rows the data shows are not actually elevated.

Output: `data/processed/finlora_model_ready.csv` — fully numeric, model-ready dataset
(126,000 rows × 30 columns, including target).


## Note: Currency Standardization

**Investigated:** whether the `currency` column affects comparability of `amount` and
`amount_to_avg_ratio` across accounts, following a review question about multi-currency
data (NGN, USD, GBP, EUR all present in `finlora_transactions.csv`).

**Found:** every account transacts in exactly one currency, consistently (never mixed).
This means `amount_to_avg_ratio` — always a comparison to the *same account's own*
baseline — remains valid as a currency-agnostic signal regardless of which currency an
account uses, since both the transaction amount and the baseline it's compared to are in
the same currency for any given account. No change to the model or its features was
needed.

**Also found (bug):** the Step 2 merge between transactions and accounts was silently
producing duplicate `currency_x`/`currency_y` columns, since both source tables share a
`currency` field and the original merge didn't account for it. Confirmed the two columns
always agreed (0 mismatches), then corrected the merge to drop the duplicate from the
accounts side, restoring a single clean `currency` column.

**Added:** `amount_usd`, a standardized-to-USD version of `amount`, for display purposes
only (not used as a model feature). Converted using approximate current mid-market
exchange rates — a snapshot, not the historical rate on each transaction's actual date:

| Currency | Rate to USD |
|---|---|
| USD | 1.00 |
| GBP | 1.34 |
| EUR | 1.14 |
| NGN | 1 / 1,375 |

This column makes transaction sizes visually comparable across accounts in the Streamlit
review queue, where raw `amount` values in different currencies would otherwise look
misleadingly comparable side by side.