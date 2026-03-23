"""
Model Evaluation — Isolation Forest (Retrained)
=================================================
Retrains IF using rich features from the external dataset:
  amount, spending_deviation_score, velocity_score,
  geo_anomaly_score, time_since_last_transaction, hour, day_of_week

80% legit rows used for training, 20% + all fraud for testing.
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, precision_recall_curve, auc
)

FEATURES = [
    "amount",
    "spending_deviation_score",
    "velocity_score",
    "geo_anomaly_score",
    "time_since_last_transaction",
    "hour",
    "day_of_week",
]

# ── 1. Load External Dataset ──────────────────────────────────────────────────
print("Loading financial_fraud_detection_dataset.csv...")
df = pd.read_csv("financial_fraud_detection_dataset.csv")
df.columns = df.columns.str.strip().str.lower()

df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce")
df["hour"]         = df["timestamp_dt"].dt.hour
df["day_of_week"]  = df["timestamp_dt"].dt.dayofweek
df["label"]        = df["is_fraud"].astype(int)

df = df.dropna(subset=FEATURES + ["label"])
print(f"Dataset: {len(df):,} rows | Fraud: {df['label'].sum():,} | Legit: {(df['label']==0).sum():,}")

# ── 2. Train/Test Split ───────────────────────────────────────────────────────
# Train ONLY on legit transactions (80% of legit rows)
legit = df[df["label"] == 0].sample(frac=1, random_state=42)
# Cap training to 200k for performance
train_size = min(200_000, int(len(legit) * 0.8))
train = legit.iloc[:train_size]
# Test: remaining legit (capped at 50k) + ALL fraud
test_legit = legit.iloc[train_size:train_size + 50_000]
test  = pd.concat([test_legit, df[df["label"] == 1]])

print(f"Train: {len(train):,} legit rows | Test: {len(test):,} rows "
      f"({test['label'].sum():,} fraud)\n")

# ── 3. Train Retrained IF ─────────────────────────────────────────────────────
print("Training Isolation Forest on rich features...")
scaler  = StandardScaler()
X_train = scaler.fit_transform(train[FEATURES])

iso = IsolationForest(n_estimators=300, contamination=0.05, random_state=42, n_jobs=-1)
iso.fit(X_train)
raw_train = iso.decision_function(X_train)
iso_min, iso_max = raw_train.min(), raw_train.max()
print(f"Model trained.\n")

# ── 4. Score Test Set ─────────────────────────────────────────────────────────
print("Scoring test set...")
X_test         = scaler.transform(test[FEATURES])
raw_b          = iso.decision_function(X_test)
iso_range      = iso_max - iso_min + 1e-9
test           = test.copy()
test["if_score"] = np.clip(1 - (raw_b - iso_min) / iso_range, 0, 1)

# Binary prediction at threshold 0.5
THRESHOLD        = 0.3
test["if_pred"]  = (test["if_score"] >= THRESHOLD).astype(int)

# ── 5. Evaluation Metrics ─────────────────────────────────────────────────────
print("=" * 55)
print("  ISOLATION FOREST — RETRAINED MODEL EVALUATION")
print("=" * 55)
print(f"  Features used: {FEATURES}\n")

print("── Classification Report (threshold = 0.3) ──")
print(classification_report(test["label"], test["if_pred"],
                             target_names=["Legit", "Fraud"]))

cm = confusion_matrix(test["label"], test["if_pred"])
tn, fp, fn, tp = cm.ravel()
print("── Confusion Matrix ──")
print(f"  True Negatives  (Legit correctly ignored) : {tn:,}")
print(f"  False Positives (Legit flagged as fraud)  : {fp:,}")
print(f"  False Negatives (Fraud missed)            : {fn:,}")
print(f"  True Positives  (Fraud correctly caught)  : {tp:,}")

roc   = roc_auc_score(test["label"], test["if_score"])
prec, rec, _ = precision_recall_curve(test["label"], test["if_score"])
pr_auc = auc(rec, prec)

print(f"\n── AUC Scores ──")
print(f"  ROC-AUC : {roc:.4f}  (0.5 = random, 1.0 = perfect)")
print(f"  PR-AUC  : {pr_auc:.4f}")

print("\n── Threshold Sensitivity ──")
print(f"  {'Threshold':>10} | {'Precision':>10} | {'Recall':>10} | {'F1':>10} | {'Flagged':>8}")
print("  " + "-" * 58)
for t in [0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8]:
    pred  = (test["if_score"] >= t).astype(int)
    tp_t  = ((pred == 1) & (test["label"] == 1)).sum()
    fp_t  = ((pred == 1) & (test["label"] == 0)).sum()
    fn_t  = ((pred == 0) & (test["label"] == 1)).sum()
    prec_t = tp_t / (tp_t + fp_t + 1e-9)
    rec_t  = tp_t / (tp_t + fn_t + 1e-9)
    f1_t   = 2 * prec_t * rec_t / (prec_t + rec_t + 1e-9)
    print(f"  {t:>10.2f} | {prec_t:>10.4f} | {rec_t:>10.4f} | {f1_t:>10.4f} | {pred.sum():>8,}")

print("\nEvaluation complete.")
