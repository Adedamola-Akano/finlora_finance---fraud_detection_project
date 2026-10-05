import streamlit as st
import pandas as pd
import numpy as np
import joblib

st.title("Finlora Fraud Review Queue")

# --- Load trained model, scaler, and feature schema ---
logreg = joblib.load("model/saved_models/logreg_model.pkl")
scaler = joblib.load("model/saved_models/scaler.pkl")
feature_columns = joblib.load("model/saved_models/feature_columns.pkl")
amount_ratio_cap = joblib.load("model/saved_models/amount_ratio_cap.pkl")


def scale_and_clip(X_input):
    """Scales raw feature values and clips extreme z-scores. Used everywhere the app
    scores data, so the fix for sigmoid saturation can never be applied in only one
    place and missed in another."""
    X_scaled = scaler.transform(X_input)
    X_scaled = np.clip(X_scaled, -5, 5)
    return X_scaled


# --- Load the review-ready test set ---
data = pd.read_csv("data/processed/test_review_queue.csv")

# --- Score every transaction ---
X = data[feature_columns]
X_scaled = scale_and_clip(X)
data['fraud_probability'] = logreg.predict_proba(X_scaled)[:, 1]

# --- Build the ranked review queue ---
display_cols = ['account_id', 'timestamp', 'amount_usd', 'currency',
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
    "Select a transaction to explain:", data.sort_values('fraud_probability', ascending=False)['transaction_id'].head(50))

if selected_id:
    row = data[data['transaction_id'] == selected_id].iloc[0]
    row_features = row[feature_columns].values.reshape(1, -1)
    row_scaled = scale_and_clip(row_features)

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


st.subheader("Score New Transactions (CSV Upload)")

uploaded_file = st.file_uploader(
    "Upload a cleaned-format transactions CSV", type="csv")

if uploaded_file is not None:
    upload_df = pd.read_csv(uploaded_file)

    required_cols = ['amount_to_avg_ratio', 'transaction_velocity_1h', 'is_new_device',
                     'has_device_on_record', 'is_cross_border', 'account_age_days',
                     'personal_spend_baseline_usd', 'account_type', 'kyc_tier',
                     'merchant_category', 'channel']
    missing_cols = [c for c in required_cols if c not in upload_df.columns]

    if missing_cols:
        st.error(f"Uploaded file is missing required columns: {missing_cols}")
    else:
        upload_df['is_new_device'] = upload_df['is_new_device'].fillna(
            0).astype(int)

        upload_df['amount_to_avg_ratio'] = upload_df['amount_to_avg_ratio'].clip(
            upper=amount_ratio_cap)

        categorical_features = ['account_type',
                                'kyc_tier', 'merchant_category', 'channel']
        upload_encoded = pd.get_dummies(
            upload_df, columns=categorical_features)
        X_upload = upload_encoded.reindex(
            columns=feature_columns, fill_value=0)

        X_upload_scaled = scale_and_clip(X_upload)
        upload_df['fraud_probability'] = logreg.predict_proba(X_upload_scaled)[
            :, 1]

        st.success(f"Scored {len(upload_df)} transactions.")

        display_upload_cols = [c for c in ['account_id', 'timestamp', 'amount_usd', 'currency',
                                           'merchant_name', 'merchant_category', 'channel',
                                           'fraud_probability'] if c in upload_df.columns]
        upload_queue = upload_df[display_upload_cols].sort_values(
            'fraud_probability', ascending=False)

        st.dataframe(upload_queue, width='stretch')

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
