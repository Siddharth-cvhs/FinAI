import { useEffect, useState } from "react";
import { fetchMonitorLogs, deleteMonitorLog, MonitorLog } from "@/lib/api";
import { RiskBadge } from "@/components/RiskBadge";
import { FileText, X, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AgentCard } from "@/components/AgentCard";
import { ScoreBar } from "@/components/ScoreBar";
import { History, Network, ShieldCheck } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";

const decisionColors: Record<string, string> = {
  Block: "text-risk-critical",
  Escalate: "text-risk-high",
  Monitor: "text-risk-medium",
  "No risk": "text-risk-low",
};

const MonitoredLogs = () => {
  const [logs, setLogs] = useState<MonitorLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<MonitorLog | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const { toast } = useToast();

  const handleDelete = async (logId: number) => {
    setDeletingId(logId);
    try {
      await deleteMonitorLog(logId);
      setLogs(prev => prev.filter(l => l.id !== logId));
      toast({ title: "Deleted", description: "Log entry removed" });
    } catch {
      toast({ title: "Error", description: "Failed to delete log", variant: "destructive" });
    } finally {
      setDeletingId(null);
    }
  };

  useEffect(() => {
    fetchMonitorLogs()
      .then(setLogs)
      .catch(() => toast({ title: "Error", description: "Failed to load logs", variant: "destructive" }))
      .finally(() => setLoading(false));
  }, [toast]);

  if (loading) return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-4">
      {[1,2,3,4].map(i => <Skeleton key={i} className="h-14 rounded-lg" />)}
    </div>
  );

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary/10">
          <FileText className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold">Monitored Logs</h1>
          <p className="text-sm text-muted-foreground">{logs.length} decisions logged</p>
        </div>
      </div>

      {logs.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <p className="text-muted-foreground">No decisions logged yet.</p>
        </div>
      ) : (
        <div className="glass rounded-xl overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="py-3 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Time</th>
                <th className="py-3 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Transaction</th>
                <th className="py-3 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Decision</th>
                <th className="py-3 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Risk</th>
                <th className="py-3 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Score</th>
                <th className="py-3 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                  <td className="py-3 px-4 text-xs text-muted-foreground font-mono">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="py-3 px-4 font-mono text-xs text-primary">{log.transaction_id}</td>
                  <td className={`py-3 px-4 text-sm font-semibold ${decisionColors[log.decision] || ""}`}>
                    {log.decision}
                  </td>
                  <td className="py-3 px-4">
                    <RiskBadge label={log.payload?.risk_metrics?.risk_label || "—"} />
                  </td>
                  <td className="py-3 px-4 font-mono text-sm">
                    {log.payload?.risk_metrics?.risk_score?.toFixed(3) || "—"}
                  </td>
                  <td className="py-3 px-4 text-right space-x-2">
                    <Button size="sm" variant="secondary" onClick={() => setSelected(log)}>
                      Open
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleDelete(log.id)}
                      disabled={deletingId === log.id}
                      className="gap-1.5"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      {deletingId === log.id ? "…" : "Delete"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail modal */}
      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4" onClick={() => setSelected(null)}>
          <div className="glass rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold font-mono">{selected.transaction_id}</h2>
                <p className="text-sm text-muted-foreground">
                  Decision: <span className={`font-semibold ${decisionColors[selected.decision]}`}>{selected.decision}</span>
                </p>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setSelected(null)}>
                <X className="w-5 h-5" />
              </Button>
            </div>

            {selected.payload && (
              <>
                <div className="grid md:grid-cols-3 gap-4">
                  <AgentCard icon={History} title="Historical Analysis" agentName="Agent 1" statement={selected.payload.agent_1_statement} />
                  <AgentCard icon={Network} title="Network Analysis" agentName="Agent 2" statement={selected.payload.agent_2_statement} />
                  <AgentCard icon={ShieldCheck} title="Compliance Check" agentName="Agent 3" statement={selected.payload.agent_3_statement} />
                </div>

                <div className="glass rounded-xl p-4 border-l-4 border-primary">
                  <p className="text-xs text-primary font-semibold uppercase mb-1">Summary</p>
                  <p className="text-sm">{selected.payload.final_summary}</p>
                </div>

                {selected.payload.risk_metrics && (
                  <div className="glass rounded-xl p-4 space-y-3">
                    <div className="flex items-center gap-3">
                      <RiskBadge label={selected.payload.risk_metrics.risk_label} />
                      <span className="text-xs text-muted-foreground">
                        IF Flagged: {selected.payload.risk_metrics.if_flagged ? "Yes" : "No"}
                      </span>
                    </div>
                    <div className="grid md:grid-cols-2 gap-x-8 gap-y-2">
                      <ScoreBar label="Z-Score" value={selected.payload.risk_metrics.score_a_zscore} />
                      <ScoreBar label="Isolation Forest" value={selected.payload.risk_metrics.score_b_isoforest} />
                      <ScoreBar label="Rule Engine" value={selected.payload.risk_metrics.score_c_rules} />
                      <ScoreBar label="Final Risk" value={selected.payload.risk_metrics.risk_score} />
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default MonitoredLogs;
