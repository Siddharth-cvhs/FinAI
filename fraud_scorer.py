"""
Fraud Risk Scoring Engine - Single Transaction Mode
Adapted for CSV-backed demo (no Postgres dependency).

Layer A: Z-score  (amount vs user historical spend)
Layer B: Isolation Forest (7 rich features, pre-trained)
Layer C: Rule-based boosters (10 rules)
"""

import warnings
warnings.filterwarnings("ignore")

import joblib
import numpy as np
import pandas as pd

WEIGHT_A     = 0.25
WEIGHT_B     = 0.35
WEIGHT_C     = 0.40
IF_THRESHOLD = 0.30

# ── Helpers ──────────────────────────────────────────────────────────────

def _parse_amount(val: str) -> float:
    return float(str(val).replace("$", "").replace(",", ""))

def _clamp(val, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(val)))

def _risk_label(score: float) -> str:
    if score >= 0.75: return "CRITICAL"
    if score >= 0.50: return "HIGH"
    if score >= 0.25: return "MEDIUM"
    return "LOW"

def _is_round_amount(amount: float) -> bool:
    """Flags structuring: amounts ending in 000, 500, or 999-pattern."""
    return (amount % 1000 == 0) or (amount % 500 == 0) or (amount % 999 == 0)

# ── Model Loading (from in-memory dataframes) ────────────────────────────

def load_models_from_frames(history_df: pd.DataFrame, watchlist_df: pd.DataFrame) -> dict:
    """Build scoring context from CSV-backed dataframes plus the joblib bundle."""
    hist = history_df.copy()
    hist["Amount_Value"] = hist["Amount"].astype(str).str.replace(r"[$,]", "", regex=True).astype(float)
    user_stats = (
        hist.groupby("User_ID")["Amount_Value"]
        .agg(["mean", "std"])
        .fillna({"std": 1.0})
        .to_dict("index")
    )

    user_senders = (
        hist.groupby("User_ID")["Sender_Account"]
        .apply(lambda s: set(s.tolist()))
        .to_dict()
    )

    hist_sorted = hist.sort_values("Timestamp")
    user_last_location = (
        hist_sorted.groupby("User_ID")
        .tail(1)
        .set_index("User_ID")[["Location", "Timestamp"]]
        .to_dict("index")
    )

    wl = watchlist_df.copy()
    wl["Entity_Type_norm"] = wl["Entity_Type"].str.upper()
    bad_ips       = set(wl[wl["Entity_Type_norm"] == "IP"]["Entity_Value"])
    bad_accounts  = set(wl[wl["Entity_Type_norm"] == "ACCOUNT"]["Entity_Value"])
    bad_countries = {str(v).lower() for v in wl[wl["Entity_Type_norm"] == "LOCATION"]["Entity_Value"]}

    bundle  = joblib.load("if_model.joblib")

    return {
        "user_stats":          user_stats,
        "user_senders":        user_senders,
        "user_last_location":  user_last_location,
        "scaler":              bundle["scaler"],
        "iso":                 bundle["model"],
        "iso_min":             bundle["iso_min"],
        "iso_max":             bundle["iso_max"],
        "bad_ips":             bad_ips,
        "bad_accounts":        bad_accounts,
        "bad_countries":       bad_countries,
    }

# ── Score a Single Transaction ───────────────────────────────────────────

def score_transaction(txn: dict, models: dict) -> dict:
    amount = _parse_amount(txn["amount"])
    ts     = pd.to_datetime(txn["timestamp"])

    # Layer A: Z-score
    stats = models["user_stats"].get(txn["user_id"])
    if stats and stats.get("mean") is not None:
        std = stats.get("std") if stats.get("std") and stats.get("std") > 0 else 1.0
        z   = (amount - stats["mean"]) / std
    else:
        z = 0.0

    score_a = _clamp(abs(z) / 6.0)

    # Layer B: Isolation Forest
    feat      = np.array([[
        amount,
        float(txn.get("spending_deviation_score", 0) or 0),
        float(txn.get("velocity_score", 0) or 0),
        float(txn.get("geo_anomaly_score", 0) or 0),
        float(txn.get("time_since_last_transaction", 0) or 0),
        ts.hour,
        ts.dayofweek,
    ]])
    feat_s    = models["scaler"].transform(feat)
    raw_b     = models["iso"].decision_function(feat_s)[0]
    iso_range = models["iso_max"] - models["iso_min"] + 1e-9
    score_b   = _clamp(1 - (raw_b - models["iso_min"]) / iso_range)

    # Layer C: Rule-based boosters
    boost = 0.0
    rules = []

    if txn.get("origin_ip") in models["bad_ips"]:
        boost += 0.40
        rules.append(f"Watchlisted IP: {txn['origin_ip']}")

    if txn.get("destination_account") in models["bad_accounts"]:
        boost += 0.45
        rules.append(f"Watchlisted account: {txn['destination_account']}")

    loc_lower = str(txn.get("location", "")).lower()
    hit_country = next((c for c in models["bad_countries"] if c in loc_lower), None)
    if hit_country:
        boost += 0.35
        rules.append(f"Banned country: {txn['location']}")

    velocity = int(txn.get("velocity_score", 0) or 0)
    if velocity >= 5:
        boost += 0.30
        rules.append(f"Velocity spike: {velocity} txns in last 60 min")

    if _is_round_amount(amount):
        boost += 0.20
        rules.append(f"Structured/round amount: {txn['amount']}")

    if 1 <= ts.hour <= 5:
        boost += 0.15
        rules.append(f"Off-hours transaction: {ts.strftime('%H:%M')}")

    geo = float(txn.get("geo_anomaly_score", 0) or 0)
    if geo >= 0.7:
        boost += 0.25
        rules.append(f"High geo anomaly score: {geo}")

    known_senders = models["user_senders"].get(txn["user_id"], set())
    if known_senders and txn.get("sender_account") not in known_senders:
        boost += 0.30
        rules.append(f"Unknown sender account: {txn.get('sender_account')}")

    if stats and stats.get("mean") and amount > stats["mean"] * 5:
        boost += 0.25
        rules.append(f"High amount ({txn['amount']}) is >5x user mean (${stats['mean']:.2f})")

    last = models["user_last_location"].get(txn["user_id"])
    if last:
        last_loc   = str(last["Location"]).lower() if "Location" in last else str(last.get("location", "")).lower()
        last_ts    = pd.to_datetime(last["Timestamp"] if "Timestamp" in last else last.get("timestamp"))
        hours_diff = abs((ts - last_ts).total_seconds()) / 3600
        if hours_diff < 3 and loc_lower != last_loc and loc_lower != "":
            boost += 0.40
            rules.append(
                f"Impossible travel: {last.get('Location', last.get('location'))} -> {txn['location']} "
                f"in {hours_diff:.1f}h"
            )

    score_c    = _clamp(boost)
    risk_score = _clamp(WEIGHT_A * score_a + WEIGHT_B * score_b + WEIGHT_C * score_c)

    return {
        "transaction_id":    txn["transaction_id"],
        "user_id":           txn["user_id"],
        "amount":            txn["amount"],
        "location":          txn.get("location"),
        "z_score":           round(z, 4),
        "score_a_zscore":    round(score_a, 4),
        "score_b_isoforest": round(score_b, 4),
        "if_flagged":        score_b >= IF_THRESHOLD,
        "score_c_rules":     round(score_c, 4),
        "risk_score":        round(risk_score, 4),
        "risk_label":        _risk_label(risk_score),
        "triggered_rules":   rules,
    }

# ── Interactive CLI (optional) ───────────────────────────────────────────

def _prompt(label, default=None):
    suffix = f" [{default}]" if default else ""
    val = input(f"  {label}{suffix}: ").strip()
    return val if val else default

def interactive_mode(models: dict):
    from datetime import datetime
    print("\n── Live Transaction Scorer ──")
    print("Type a transaction manually. Press Ctrl+C to quit.\n")

    while True:
        try:
            print("─" * 40)
            txn = {
                "transaction_id":             _prompt("Transaction ID",            "TXN-LIVE-001"),
                "timestamp":                  _prompt("Timestamp",                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                "user_id":                    _prompt("User ID",                   "USR-001"),
                "sender_account":             _prompt("Sender Account",            "ACC-000100"),
                "amount":                     _prompt("Amount (e.g. $500.00)",     "$100.00"),
                "origin_ip":                  _prompt("Origin IP",                 "192.168.1.1"),
                "device_id":                  _prompt("Device ID",                 "DEV-ABC-001"),
                "destination_account":        _prompt("Destination Account",       "ACC-998877"),
                "location":                   _prompt("Location",                  "New York, USA"),
                "spending_deviation_score":   _prompt("Spending Deviation Score",  "0.0"),
                "velocity_score":             _prompt("Velocity Score",            "1"),
                "geo_anomaly_score":          _prompt("Geo Anomaly Score",         "0.0"),
                "time_since_last_transaction":_prompt("Time Since Last Txn (hrs)", "24.0"),
            }

            result = score_transaction(txn, models)

            print("\n── Result ──")
            print(f"  Z-Score          : {result['z_score']}")
            print(f"  Score A (Z-score): {result['score_a_zscore']}")
            print(f"  Score B (ML)     : {result['score_b_isoforest']}  (flagged: {result['if_flagged']})")
            print(f"  Score C (Rules)  : {result['score_c_rules']}")
            print(f"  Final Risk Score : {result['risk_score']}")
            print(f"  Risk Label       : {result['risk_label']}")
            if result["triggered_rules"]:
                print("  Triggered Rules  :")
                for r in result["triggered_rules"]:
                    print(f"    [!] {r}")
            print()

        except KeyboardInterrupt:
            print("\nExiting scorer.")
            break

if __name__ == "__main__":
    # Example standalone usage expects you to prepare history_df/watchlist_df first.
    print("Please import and call load_models_from_frames(history_df, watchlist_df) in your app context.")
