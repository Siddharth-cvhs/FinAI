"""
Train & Save Isolation Forest Model
=====================================
Trains on financial_fraud_detection_dataset.csv (legit rows only)
using 7 rich features, then saves model + scaler to disk.
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

FEATURES = [
    "amount",
    "spending_deviation_score",
    "velocity_score",
    "geo_anomaly_score",
    "time_since_last_transaction",
    "hour",
    "day_of_week",
]

print("Loading dataset (chunked)...")
chunks = []
for chunk in pd.read_csv("financial_fraud_detection_dataset.csv", chunksize=100_000):
    chunk.columns = chunk.columns.str.strip().str.lower()
    chunk = chunk[chunk["is_fraud"] == False]
    chunks.append(chunk)
    if sum(len(c) for c in chunks) >= 200_000:
        break

df = pd.concat(chunks, ignore_index=True).head(200_000)

df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce")
df["hour"]         = df["timestamp_dt"].dt.hour
df["day_of_week"]  = df["timestamp_dt"].dt.dayofweek
df = df.dropna(subset=FEATURES)
train = df
print(f"Training on {len(train):,} legit transactions with {len(FEATURES)} features...")

scaler  = StandardScaler()
X_train = scaler.fit_transform(train[FEATURES])

iso = IsolationForest(n_estimators=300, contamination=0.05, random_state=42, n_jobs=-1)
iso.fit(X_train)

# Store score range for normalisation
raw       = iso.decision_function(X_train)
iso_min   = float(raw.min())
iso_max   = float(raw.max())

# Save everything
joblib.dump({"model": iso, "scaler": scaler, "iso_min": iso_min,
             "iso_max": iso_max, "features": FEATURES}, "if_model.joblib")

print(f"Model saved to if_model.joblib")
print(f"  Score range: [{iso_min:.4f}, {iso_max:.4f}]")
print("Done.")
