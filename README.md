# FinAI – Real‑Time Fraud Detection (FastAPI + LangGraph + React)

## Overview
FinAI ingests live transactions from Postgres, scores them with a hybrid Isolation‑Forest + rule engine, runs three parallel LLM agents (Historian, Network, Compliance) and synthesizes a recommended action (Block / Escalate / Clear). Human reviewers finalize the decision; all outcomes are logged for audit.

## Architecture (mermaid)
```mermaid
flowchart TD
    A[Live Monitoring] --> B[Investigation]
    B --> C{Agentic Workflow}
    C --> H[Historian Agent]
    C --> N[Network Agent]
    C --> P[Compliance Agent]
    H --> S[Summary Agent]
    N --> S
    P --> S
    S --> R[Final Recommendation]
    C -->|Non‑agentic Scoring| E[Risk / Evaluation Metrics]
    E --> R
    R --> D[Decision (Human in the loop)]
    D --> L[(Monitored Logs)]
    L -->|Fetch| B
    B -->|Add| DB[(Postgres DB)]
    L -->|Delete| DB
    DB --> B
```

## Key Components
- **Backend:** FastAPI, LangGraph/LangChain (Gemini 2.5 Flash), Pandas, psycopg2, IsolationForest bundle (`if_model.joblib`), heuristic rules.
- **Frontend:** React (Lovable scaffold) under `front/sentinel-ai` with live polling, investigation view, and monitored-log review.
- **Database:** Postgres `VH_Hack` with tables: `live_transcation`, `transaction_history`, `watchlist`, `monitoring_logs`.

## API Endpoints
- `GET /stream_transactions?batch_size=` – returns 1–3 live rows (wrap‑around).
- `POST /investigate/{transaction_id}` – enrich + score + agentic workflow; returns transaction, agent statements, final summary, risk_metrics, latency_ms.
- `POST /monitor_log` – body `{decision, result}`; stores decision + payload in `monitoring_logs`.
- `GET /monitor_log` – list recent monitoring logs.
- `DELETE /monitor_log/{id}` – delete a monitoring log entry.

## Run Locally
```bash
# Backend
cd C:\VH811\Hackathon
pip install -r requirements.txt
uvicorn main:api --reload --port 8000
# Requires GEMINI_API_KEY or GOOGLE_API_KEY; Postgres defaults:
# host=localhost port=5432 db=VH_Hack user=postgres password=Cvhs@12345

# Frontend (Lovable app)
cd front/sentinel-ai
npm install
npm run dev   # http://localhost:5173
```

## Data / Scoring
- Feature engineering: velocity (last 60m), time since last txn, geo anomaly, spending deviation, hour, day-of-week.
- Rules: watchlist IP/account, banned country, velocity spike, structured amount, off-hours, geo anomaly, unknown sender, high-amount vs mean, impossible travel.
- Outputs: `risk_score`, `risk_label`, scores A/B/C, IF flag, triggered_rules.

## Human-in-the-loop
- Frontend buttons: Block / Escalate / No risk / Monitor.
- Decisions are written to `monitoring_logs` with full investigation payload; logs can be re-opened or deleted.

## Paths of Interest
- Backend: `main.py`, `fraud_scorer.py`, `requirements.txt`
- Frontend: `front/sentinel-ai/src`
- Model bundle: `if_model.joblib`

## Tests / Validation
- Smoke: hit `/stream_transactions` and `/investigate/{id}` for an existing Transaction_ID.
- UI: verify theme toggle (light/dark) and live polling at 2s cadence.

## Notes
- CORS is open to `*` for easy local React usage.
- Light theme is default; toggle persists in `localStorage` (`finai-theme`).
