import os
import random
import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict
from typing_extensions import Annotated
import json

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain.schema import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.graph import START, END
from langgraph.graph import StateGraph
import fraud_scorer

# --- Environment setup -----------------------------------------------------
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required. Put it in .env or environment variables.")

# --- Data loading ----------------------------------------------------------
DB_NAME = os.getenv("PGDATABASE", "VH_Hack")
DB_USER = os.getenv("PGUSER", "postgres")
DB_PASSWORD = os.getenv("PGPASSWORD", "Cvhs@12345")
DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = int(os.getenv("PGPORT", "5432"))

def _get_conn():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )

def _read_transactions_from_db(table: str) -> pd.DataFrame:
    with _get_conn() as conn:
        df = pd.read_sql(f"SELECT * FROM {table}", conn)
    # normalize column names to Title-style expected by the app
    rename_map = {
        "transaction_id": "Transaction_ID",
        "timestamp": "Timestamp",
        "user_id": "User_ID",
        "sender_account": "Sender_Account",
        "amount": "Amount",
        "origin_ip": "Origin_IP",
        "device_id": "Device_ID",
        "destination_account": "Destination_Account",
        "location": "Location",
        "is_fraud": "Is_Fraud",
    }
    df = df.rename(columns={c: rename_map.get(c.lower(), c) for c in df.columns})
    if "Is_Fraud" in df.columns:
        df = df.drop(columns=["Is_Fraud"])
    df["Amount_Value"] = (
        df["Amount"]
        .astype(str)
        .str.replace(r"[$,]", "", regex=True)
        .astype(float)
    )
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    return df

# Load data from Postgres (tables were already created)
df_live = _read_transactions_from_db("live_transcation")
df_history = _read_transactions_from_db("transaction_history")
with _get_conn() as conn:
    df_watchlist = pd.read_sql("SELECT * FROM watchlist", conn)
# Normalize watchlist columns
wl_rename = {
    "entity_type": "Entity_Type",
    "entity_value": "Entity_Value",
    "risk_level": "Risk_Level",
    "reason": "Reason",
}
df_watchlist = df_watchlist.rename(columns={c: wl_rename.get(c.lower(), c) for c in df_watchlist.columns})
df_combined = pd.concat([df_history, df_live], ignore_index=True)

# --- Monitoring log setup ---------------------------------------------------

def _ensure_monitor_table():
    ddl = """
    CREATE TABLE IF NOT EXISTS monitoring_logs (
        id SERIAL PRIMARY KEY,
        transaction_id TEXT,
        decision TEXT,
        payload JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()

_ensure_monitor_table()

# --- LLM setup -------------------------------------------------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2,
    google_api_key=GEMINI_API_KEY,
    convert_system_message_to_human=True,
)

# Load fraud scoring context (Isolation Forest bundle + stats)
fraud_models = fraud_scorer.load_models_from_frames(df_history, df_watchlist)

# --- LangGraph state -------------------------------------------------------
class AgentState(TypedDict, total=False):
    transaction: Dict[str, Any]
    agent_1_statement: str
    agent_2_statement: str
    agent_3_statement: str
    final_summary: str
    fanout_marker: Annotated[int, lambda x, y: y]  # enables multi-edge fanout in this langgraph version

# --- Tooling functions -----------------------------------------------------
def historian_tool(user_id: str) -> Dict[str, Any]:
    user_df = df_history[df_history["User_ID"] == user_id]
    if user_df.empty:
        return {"history_found": False}

    summary = {
        "history_found": True,
        "count": len(user_df),
        "avg_amount": round(user_df["Amount_Value"].mean(), 2),
        "median_amount": round(user_df["Amount_Value"].median(), 2),
        "top_locations": user_df["Location"].value_counts().head(3).to_dict(),
        "top_devices": user_df["Device_ID"].value_counts().head(3).to_dict(),
        "recent_timestamp": user_df["Timestamp"].max().isoformat(),
    }
    return summary


def network_tool(origin_ip: str, destination_account: str, user_id: str) -> Dict[str, Any]:
    combined = pd.concat([df_live, df_history], ignore_index=True)

    ip_matches = combined[
        (combined["Origin_IP"] == origin_ip) & (combined["User_ID"] != user_id)
    ]
    dest_matches = combined[
        (combined["Destination_Account"] == destination_account)
        & (combined["User_ID"] != user_id)
    ]
    return {
        "shared_origin_ip_count": len(ip_matches),
        "shared_destination_count": len(dest_matches),
        "distinct_users_via_ip": ip_matches["User_ID"].nunique(),
        "distinct_users_via_destination": dest_matches["User_ID"].nunique(),
        "sample_ip_matches": ip_matches.head(5).to_dict(orient="records"),
        "sample_destination_matches": dest_matches.head(5).to_dict(orient="records"),
    }


def compliance_tool(origin_ip: str, destination_account: str, location: str) -> Dict[str, Any]:
    hits: List[Dict[str, str]] = []
    for _, row in df_watchlist.iterrows():
        if row["Entity_Type"].upper() == "IP" and row["Entity_Value"] == origin_ip:
            hits.append({"field": "Origin_IP", **row.to_dict()})
        if row["Entity_Type"].upper() == "ACCOUNT" and row["Entity_Value"] == destination_account:
            hits.append({"field": "Destination_Account", **row.to_dict()})
        # coarse location match
        if row["Entity_Type"].upper() == "LOCATION" and row["Entity_Value"].lower() in location.lower():
            hits.append({"field": "Location", **row.to_dict()})
    return {"hits": hits, "hit_count": len(hits)}


# --- Agent nodes -----------------------------------------------------------
async def historian_node(state: AgentState) -> AgentState:
    tx = state["transaction"]
    stats = historian_tool(tx["User_ID"])

    sys_prompt = "Historian agent: compare live txn vs user history; note deviation on amount/device/location. Keep to 2 sentences."
    human_prompt = f"Txn: {tx}\nHistory summary: {stats}\nReturn a deviation-risk statement."
    resp = await llm.ainvoke([SystemMessage(content=sys_prompt), HumanMessage(content=human_prompt)])
    return {"agent_1_statement": resp.content}


async def network_node(state: AgentState) -> AgentState:
    tx = state["transaction"]
    net = network_tool(tx["Origin_IP"], tx["Destination_Account"], tx["User_ID"])

    sys_prompt = "Network agent: look for shared Origin_IP/Destination_Account across other users; assess mule risk in 2 sentences with counts."
    human_prompt = f"Txn: {tx}\nNetwork evidence: {net}\nGive your assessment."
    resp = await llm.ainvoke([SystemMessage(content=sys_prompt), HumanMessage(content=human_prompt)])
    return {"agent_2_statement": resp.content}


async def compliance_node(state: AgentState) -> AgentState:
    tx = state["transaction"]
    comp = compliance_tool(tx["Origin_IP"], tx["Destination_Account"], tx["Location"])

    sys_prompt = "Compliance agent: check against watchlist; if hits, state severity; else say no direct risk. Max 2 sentences."
    human_prompt = f"Txn: {tx}\nHits: {comp}\nGive compliance risk statement."
    resp = await llm.ainvoke([SystemMessage(content=sys_prompt), HumanMessage(content=human_prompt)])
    return {"agent_3_statement": resp.content}


async def synth_node(state: AgentState) -> AgentState:
    # Ensure we only synthesize once all agent statements exist
    if state.get("final_summary"):
        return {}
    if not (state.get("agent_1_statement") and state.get("agent_2_statement") and state.get("agent_3_statement")):
        return {}

    tx = state["transaction"]
    sys_prompt = "Synthesizer: decide Block/Escalate/Clear using agent statements; cite key signals; <=5 sentences; concise exec summary."
    human_prompt = (
        f"Txn: {tx}\nHistorian: {state['agent_1_statement']}\n"
        f"Network: {state['agent_2_statement']}\nCompliance: {state['agent_3_statement']}\n"
        "Return summary with recommendation."
    )
    resp = await llm.ainvoke([SystemMessage(content=sys_prompt), HumanMessage(content=human_prompt)])
    return {"final_summary": resp.content}


# --- LangGraph assembly ----------------------------------------------------
graph = StateGraph(AgentState)
async def fanout_node(state: AgentState) -> AgentState:
    # No mutation; used only to fan out from START
    return {}

graph.add_node("fanout", fanout_node)
graph.add_node("historian", historian_node)
graph.add_node("network", network_node)
graph.add_node("compliance", compliance_node)
graph.add_node("synthesizer", synth_node)

# START can only have one outgoing edge in this langgraph version
graph.add_edge(START, "fanout")
graph.add_edge("fanout", "historian")
graph.add_edge("fanout", "network")
graph.add_edge("fanout", "compliance")

graph.add_edge("historian", "synthesizer")
graph.add_edge("network", "synthesizer")
graph.add_edge("compliance", "synthesizer")
graph.add_edge("synthesizer", END)

lang_app = graph.compile()

# --- FastAPI app -----------------------------------------------------------
api = FastAPI(title="Fraud Detection Agentic API", version="1.0")
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

stream_index = 0
stream_lock = asyncio.Lock()


def _normalize_row(row: pd.Series) -> Dict[str, Any]:
    data = row.to_dict()
    if isinstance(data.get("Timestamp"), pd.Timestamp):
        data["Timestamp"] = data["Timestamp"].isoformat()
    # Drop helper column if present
    data.pop("Amount_Value", None)
    return data


def _country_from_location(loc: str) -> str:
    if not loc or not isinstance(loc, str):
        return ""
    parts = loc.split(",")
    return parts[-1].strip().lower() if parts else ""


def _enrich_for_scorer(tx: Dict[str, Any]) -> Dict[str, Any]:
    """Add engineered features expected by fraud_scorer."""
    ts = pd.to_datetime(tx["Timestamp"])
    user_id = tx["User_ID"]
    amount_clean = float(str(tx["Amount"]).replace("$", "").replace(",", ""))

    # Transactions for this user before current ts
    user_txn_before = df_combined[(df_combined["User_ID"] == user_id) & (df_combined["Timestamp"] < ts)]

    # Velocity: txns in last 60 minutes
    window_start = ts - pd.Timedelta(minutes=60)
    velocity_count = len(user_txn_before[user_txn_before["Timestamp"] >= window_start])

    # Time since last transaction
    if not user_txn_before.empty:
        last_ts = user_txn_before["Timestamp"].max()
        time_since_last = (ts - last_ts).total_seconds() / 3600
        last_loc = user_txn_before.loc[user_txn_before["Timestamp"].idxmax(), "Location"]
    else:
        time_since_last = 999.0
        last_loc = ""

    # Spending deviation score (absolute z scaled roughly)
    stats = fraud_models["user_stats"].get(user_id)
    if stats and stats.get("mean"):
        std = stats.get("std") if stats.get("std") and stats.get("std") > 0 else 1.0
        spending_dev = abs(amount_clean - stats["mean"]) / std
    else:
        spending_dev = 0.0

    # Geo anomaly: 0.8 if country changed vs last, else 0.1
    curr_country = _country_from_location(tx.get("Location"))
    last_country = _country_from_location(last_loc)
    geo_anomaly = 0.8 if last_country and curr_country and curr_country != last_country else 0.1

    return {
        "transaction_id": tx["Transaction_ID"],
        "timestamp": tx["Timestamp"],
        "user_id": tx["User_ID"],
        "sender_account": tx["Sender_Account"],
        "amount": tx["Amount"],
        "origin_ip": tx["Origin_IP"],
        "device_id": tx["Device_ID"],
        "destination_account": tx["Destination_Account"],
        "location": tx["Location"],
        "spending_deviation_score": round(spending_dev, 3),
        "velocity_score": velocity_count,
        "geo_anomaly_score": round(geo_anomaly, 3),
        "time_since_last_transaction": round(time_since_last, 3),
    }


@api.get("/stream_transactions")
async def stream_transactions(batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Return a small batch (1-3 rows) of live transactions to simulate streaming.
    """
    global stream_index
    n = batch_size or random.randint(1, 3)
    async with stream_lock:
        start = stream_index
        end = min(start + n, len(df_live))
        batch = df_live.iloc[start:end]
        stream_index = end % len(df_live)
    return [_normalize_row(r) for _, r in batch.iterrows()]


@api.post("/investigate/{transaction_id}")
async def investigate(transaction_id: str) -> Dict[str, Any]:
    started = time.perf_counter()
    # Find transaction in live; fallback to history
    match = df_live[df_live["Transaction_ID"] == transaction_id]
    if match.empty:
        match = df_history[df_history["Transaction_ID"] == transaction_id]
    if match.empty:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx_dict = _normalize_row(match.iloc[0])

    # Build fraud risk metrics
    scorer_payload = _enrich_for_scorer(tx_dict)
    risk_metrics = fraud_scorer.score_transaction(scorer_payload, fraud_models)

    initial_state: AgentState = {"transaction": tx_dict}
    result = await lang_app.ainvoke(initial_state)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    # Placeholder evaluation metrics (need labeled data to populate)
    return {
        "transaction": tx_dict,
        "agent_1_statement": result.get("agent_1_statement"),
        "agent_2_statement": result.get("agent_2_statement"),
        "agent_3_statement": result.get("agent_3_statement"),
        "final_summary": result.get("final_summary"),
        "risk_metrics": risk_metrics,
        "latency_ms": latency_ms,
    }

# --- Monitoring log API -----------------------------------------------------

class MonitorPayload(BaseModel):
    decision: str
    result: Dict[str, Any]

@api.post("/monitor_log")
async def monitor_log(body: MonitorPayload):
    """
    Persist the investigation result plus human decision into monitoring_logs.
    """
    payload = body.result
    txn_id = payload.get("transaction", {}).get("Transaction_ID")
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO monitoring_logs (transaction_id, decision, payload) VALUES (%s, %s, %s)",
                (txn_id, body.decision, json.dumps(payload)),
            )
        conn.commit()
    return {"status": "ok", "transaction_id": txn_id, "decision": body.decision}


@api.get("/monitor_log")
async def list_monitor_logs(limit: int = 100):
    """
    Return recent monitoring logs.
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, transaction_id, decision, payload, created_at "
                "FROM monitoring_logs ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
    results = []
    for r in rows:
        results.append(
            {
                "id": r[0],
                "transaction_id": r[1],
                "decision": r[2],
                "payload": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
            }
        )
    return results


@api.delete("/monitor_log/{log_id}")
async def delete_monitor_log(log_id: int):
    """
    Delete a monitoring log by id.
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM monitoring_logs WHERE id = %s RETURNING id",
                (log_id,),
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Log not found")
    return {"status": "deleted", "id": log_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:api", host="0.0.0.0", port=8000, reload=True)
