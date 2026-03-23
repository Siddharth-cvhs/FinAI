const BASE_URL = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export interface Transaction {
  Transaction_ID: string;
  Timestamp: string;
  User_ID: string;
  Sender_Account: string;
  Amount: string;
  Origin_IP: string;
  Device_ID: string;
  Destination_Account: string;
  Location: string;
}

export interface RiskMetrics {
  transaction_id: string;
  user_id: string;
  amount: string;
  location: string;
  z_score: number;
  score_a_zscore: number;
  score_b_isoforest: number;
  if_flagged: boolean;
  score_c_rules: number;
  risk_score: number;
  risk_label: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  triggered_rules: string[];
}

export interface InvestigationResult {
  transaction: Transaction;
  agent_1_statement: string;
  agent_2_statement: string;
  agent_3_statement: string;
  final_summary: string;
  risk_metrics: RiskMetrics;
  latency_ms: number;
}

export type Decision = "Block" | "Escalate" | "No risk" | "Monitor";

export interface MonitorLog {
  id: number;
  transaction_id: string;
  decision: Decision;
  payload: InvestigationResult;
  created_at: string;
}

export async function streamTransactions(batchSize = 3, signal?: AbortSignal): Promise<Transaction[]> {
  const res = await fetch(`${BASE_URL}/stream_transactions?batch_size=${batchSize}`, { signal });
  if (!res.ok) throw new Error("Failed to fetch transactions");
  return res.json();
}

export async function investigate(transactionId: string, signal?: AbortSignal): Promise<InvestigationResult> {
  const res = await fetch(`${BASE_URL}/investigate/${transactionId}`, { method: "POST", signal });
  if (res.status === 404) throw new Error("Transaction not found");
  if (!res.ok) throw new Error("Investigation failed");
  return res.json();
}

export async function postMonitorLog(decision: Decision, result: InvestigationResult): Promise<{ status: string; transaction_id: string; decision: string }> {
  const res = await fetch(`${BASE_URL}/monitor_log`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, result }),
  });
  if (!res.ok) throw new Error("Failed to log decision");
  return res.json();
}

export async function fetchMonitorLogs(limit = 100): Promise<MonitorLog[]> {
  const res = await fetch(`${BASE_URL}/monitor_log?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch logs");
  return res.json();
}

export async function deleteMonitorLog(logId: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/monitor_log/${logId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete log");
}
