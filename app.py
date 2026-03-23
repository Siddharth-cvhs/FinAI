import os
import time
from typing import Dict, List

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Fraud Detection Dashboard", layout="wide")

# --- Session state init ----------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "dashboard"
if "transactions" not in st.session_state:
    st.session_state.transactions = pd.DataFrame()
if "selected_tx" not in st.session_state:
    st.session_state.selected_tx = None
if "investigation_result" not in st.session_state:
    st.session_state.investigation_result = None


def fetch_stream() -> List[Dict]:
    resp = requests.get(f"{API_BASE}/stream_transactions", timeout=10)
    resp.raise_for_status()
    return resp.json()


def run_investigation(tx_id: str) -> Dict:
    resp = requests.post(f"{API_BASE}/investigate/{tx_id}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def show_dashboard():
    st.title("Live Fraud Dashboard")
    st.caption("Auto-refreshing every 2 seconds from /stream_transactions")

    # Pull new rows
    try:
        new_rows = fetch_stream()
        if new_rows:
            new_df = pd.DataFrame(new_rows)
            st.session_state.transactions = (
                pd.concat([st.session_state.transactions, new_df], ignore_index=True)
                .drop_duplicates(subset=["Transaction_ID"], keep="last")
            )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Stream error: {exc}")

    latest = st.session_state.transactions.tail(20)
    st.subheader("Latest Alerts")
    for _, row in latest.iterrows():
        with st.container():
            c1, c2 = st.columns([9, 1])
            c1.write(
                {
                    "Transaction_ID": row.get("Transaction_ID"),
                    "User_ID": row.get("User_ID"),
                    "Amount": row.get("Amount"),
                    "Location": row.get("Location"),
                    "Timestamp": row.get("Timestamp"),
                }
            )
            if c2.button("Investigate", key=f"btn_{row.get('Transaction_ID')}"):
                st.session_state.selected_tx = row.to_dict()
                st.session_state.page = "investigation"
                st.session_state.investigation_result = None
                st.experimental_rerun()


def show_investigation():
    tx = st.session_state.selected_tx
    if not tx:
        st.warning("Select a transaction from the dashboard to investigate.")
        if st.button("Back to dashboard"):
            st.session_state.page = "dashboard"
            st.experimental_rerun()
        return

    st.title(f"Investigation: {tx.get('Transaction_ID')}")
    st.json(tx)

    if st.session_state.investigation_result is None:
        with st.spinner("Running multi-agent investigation..."):
            try:
                st.session_state.investigation_result = run_investigation(tx.get("Transaction_ID"))
            except Exception as exc:  # noqa: BLE001
                st.error(f"Investigation failed: {exc}")
                if st.button("Back to dashboard"):
                    st.session_state.page = "dashboard"
                    st.experimental_rerun()
                return

    result = st.session_state.investigation_result
    st.subheader("Agent Outputs")
    st.markdown("**Agent 1 - Historian**")
    st.write(result.get("agent_1_statement"))
    st.markdown("**Agent 2 - Network**")
    st.write(result.get("agent_2_statement"))
    st.markdown("**Agent 3 - Compliance**")
    st.write(result.get("agent_3_statement"))
    st.markdown("**Final Executive Summary**")
    st.write(result.get("final_summary"))

    st.subheader("System Metrics")
    st.metric("Decision Latency (ms)", result.get("latency_ms"))

    risk = result.get("risk_metrics") or {}
    st.subheader("Risk Metrics (Heuristics + IF model)")
    cols = st.columns(3)
    cols[0].metric("Risk Score", risk.get("risk_score"))
    cols[1].metric("Risk Label", risk.get("risk_label"))
    cols[2].metric("IF Flagged", str(risk.get("if_flagged")))
    # Bar chart of component scores
    score_chart = pd.DataFrame(
        {
            "score": [
                risk.get("score_a_zscore"),
                risk.get("score_b_isoforest"),
                risk.get("score_c_rules"),
                risk.get("risk_score"),
            ]
        },
        index=["Score A (Z)", "Score B (IF)", "Score C (Rules)", "Final Risk"],
    )
    st.bar_chart(score_chart)
    if risk.get("triggered_rules"):
        st.markdown("**Triggered Rules**")
        for rule in risk["triggered_rules"]:
            st.write(f"[!] {rule}")
    else:
        st.info("No rule triggers.")

    st.info("“Till this flow is done by AI; there may be flaws or misconceptions. Please have a human review before final action.”")

    # Action buttons -> persist decision
    decision_cols = st.columns(4)
    decisions = ["Block", "Escalate", "No risk", "Monitor"]

    def send_decision(decision: str):
        try:
            resp = requests.post(f"{API_BASE}/monitor_log", json={"decision": decision, "result": result}, timeout=15)
            resp.raise_for_status()
            st.success(f"Decision '{decision}' logged.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to log decision: {exc}")

    for d, col in zip(decisions, decision_cols):
        if col.button(d):
            send_decision(d)

    if st.button("Back to dashboard"):
        st.session_state.page = "dashboard"
        st.experimental_rerun()

if st.session_state.page == "dashboard":
    show_dashboard()
    # Simple auto-refresh loop (2 seconds)
    time.sleep(2)
    st.experimental_rerun()
else:
    show_investigation()
