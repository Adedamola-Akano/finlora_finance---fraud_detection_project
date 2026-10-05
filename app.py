import streamlit as st
import pandas as pd
import numpy as np
import joblib

st.title("Finlora Fraud Review Queue")

# --- Load trained model, scaler, and feature schema ---
logreg = joblib.load("model/saved_models/logreg_model.pkl")
scaler = joblib.load("model/saved_models/scaler.pkl")
feature_columns = joblib.load("model/saved_models/feature_columns.pkl")

# --- Load the review-ready test set ---
data = pd.read_csv("data/processed/test_review_queue.csv")

# --- Score every transaction ---
X = data[feature_columns]
X_scaled = scaler.transform(X)
X_scaled = np.clip(X_scaled, -5, 5)
data['fraud_probability'] = logreg.predict_proba(X_scaled)[:, 1]

# --- Build the ranked review queue ---
display_cols = ['transaction_id', 'account_id', 'timestamp', 'amount',
                'merchant_name', 'merchant_category', 'channel', 'fraud_probability']
queue = data[display_cols].sort_values('fraud_probability', ascending=False)

st.subheader("Top 50 Highest-Risk Transactions")
st.dataframe(queue.head(50), width='stretch')
# loads the model, scaler, and your saved feature list exactly as before,
# then loads the review-ready test set we just built.
# X = data[feature_columns] pulls out only the 29 model columns (in the exact saved order — critical,
# since we discussed earlier that column order/consistency matters for scaled models),
# scales them the same way training data was scaled,
# then predict_proba(...)[:, 1] generates a fraud probability for every transaction,
# stored as a new column. Finally, we pick out human-readable columns plus the new probability score,
# sort by that score highest-first (sort_values(..., ascending=False) — the riskiest transactions land at the top,
# exactly the "prioritized queue" your brief calls for),
# and st.dataframe(...) renders it as an interactive table directly in the browser —
# width='stretch' just makes it stretch to fill the available page width nicely.

st.subheader("Explain a Flagged Transaction")

selected_id = st.selectbox(
    "Select a transaction to explain:", queue['transaction_id'].head(50))

if selected_id:
    row = data[data['transaction_id'] == selected_id].iloc[0]
    row_features = row[feature_columns].values.reshape(1, -1)
    row_scaled = scaler.transform(row_features)
    row_scaled = np.clip(row_scaled, -5, 5)

    # Contribution of each feature = (scaled value) x (model coefficient)
    contributions = row_scaled[0] * logreg.coef_[0]
    explanation = pd.DataFrame({
        'feature': feature_columns,
        'contribution': contributions
    }).sort_values('contribution', key=abs, ascending=False)

st.write(f"Fraud probability: **{row['fraud_probability']:.6f}**")
st.write(
    "Top contributing factors (positive = raises fraud risk, negative = lowers it):")
st.dataframe(explanation.head(10), width='stretch')
# st.selectbox(...) creates a dropdown menu in the app,
# letting a user pick one transaction from the top 50.
# Once selected, we pull that exact row, extract just its feature values,
# scale them the same way as before,
# and multiply each scaled feature value by that feature's learned coefficient (logreg.coef_[0])
# — this is the mathematical heart of Logistic Regression's interpretability:
# each feature's contribution to the final score is literally just its value times its weight.
# We sort by absolute contribution size (key=abs) so the most influential factors —
# whether pushing risk up or down — appear first,
# and display the top 10 in a small table alongside the overall fraud probability.
