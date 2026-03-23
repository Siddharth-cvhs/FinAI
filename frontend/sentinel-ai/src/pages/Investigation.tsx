import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Clock, History, Network, ShieldCheck, AlertTriangle, Ban, ArrowUpCircle, CheckCircle, Eye } from "lucide-react";
import { investigate, postMonitorLog, InvestigationResult, Decision } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { AgentCard } from "@/components/AgentCard";
import { ScoreBar } from "@/components/ScoreBar";
import { RiskBadge } from "@/components/RiskBadge";
import { useToast } from "@/hooks/use-toast";
import { Skeleton } from "@/components/ui/skeleton";

const decisionButtons: { label: Decision; icon: typeof Ban; variant: "destructive" | "secondary" | "default" | "outline" }[] = [
  { label: "Block", icon: Ban, variant: "destructive" },
  { label: "Escalate", icon: ArrowUpCircle, variant: "secondary" },
  { label: "No risk", icon: CheckCircle, variant: "default" },
  { label: "Monitor", icon: Eye, variant: "outline" },
];

const Investigation = () => {
  const { txId } = useParams<{ txId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [data, setData] = useState<InvestigationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deciding, setDeciding] = useState(false);

  useEffect(() => {
    if (!txId) return;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    investigate(txId, controller.signal)
      .then(setData)
      .catch(e => { if (e.name !== "AbortError") setError(e.message); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [txId]);

  const handleDecision = async (decision: Decision) => {
    if (!data) return;
    setDeciding(true);
    try {
      await postMonitorLog(decision, data);
      toast({ title: "Decision logged", description: `${decision} — ${txId}` });
      navigate("/monitoring");
    } catch {
      toast({ title: "Error", description: "Failed to log decision", variant: "destructive" });
    } finally {
      setDeciding(false);
    }
  };

  if (loading) return (
    <div className="p-6 max-w-5xl mx-auto flex flex-col items-center justify-center min-h-[60vh] space-y-6">
      <div className="relative">
        <div className="w-16 h-16 rounded-full border-4 border-primary/30 border-t-primary animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <ShieldCheck className="w-6 h-6 text-primary animate-pulse" />
        </div>
      </div>
      <div className="text-center space-y-2">
        <p className="text-lg font-semibold">AI Agents Processing…</p>
        <p className="text-sm text-muted-foreground">
          Analyzing transaction patterns, network links & compliance checks
        </p>
        <div className="flex items-center justify-center gap-1.5 mt-3">
          {["Historian", "Network", "Compliance"].map((agent, i) => (
            <span
              key={agent}
              className="px-2.5 py-1 rounded-full text-xs font-mono bg-primary/10 text-primary animate-pulse"
              style={{ animationDelay: `${i * 0.3}s` }}
            >
              {agent}
            </span>
          ))}
        </div>
      </div>
    </div>
  );

  if (error) return (
    <div className="p-6 max-w-5xl mx-auto text-center space-y-4">
      <AlertTriangle className="w-12 h-12 text-destructive mx-auto" />
      <p className="text-lg font-semibold">{error}</p>
      <Button variant="secondary" onClick={() => navigate("/monitoring")}>
        <ArrowLeft className="w-4 h-4 mr-2" /> Back to Monitoring
      </Button>
    </div>
  );

  if (!data) return null;

  const { transaction: tx, risk_metrics: rm } = data;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/monitoring")}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold font-mono">{tx.Transaction_ID}</h1>
            <RiskBadge label={rm.risk_label} />
          </div>
          <p className="text-sm text-muted-foreground">
            {tx.User_ID} • {tx.Amount} • {tx.Location}
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Clock className="w-3.5 h-3.5" />
          {data.latency_ms.toFixed(0)}ms
        </div>
      </div>

      {/* Transaction details */}
      <div className="glass rounded-xl p-5">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          {[
            ["Sender", tx.Sender_Account],
            ["Destination", tx.Destination_Account],
            ["Origin IP", tx.Origin_IP],
            ["Device", tx.Device_ID],
            ["Amount", tx.Amount],
            ["Location", tx.Location],
            ["Timestamp", new Date(tx.Timestamp).toLocaleString()],
            ["IF Flagged", rm.if_flagged ? "Yes ⚠️" : "No"],
          ].map(([label, val]) => (
            <div key={label}>
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="font-mono text-xs font-medium mt-0.5 break-all">{val}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Agent statements */}
      <div className="grid md:grid-cols-3 gap-4">
        <AgentCard icon={History} title="Historical Analysis" agentName="Agent 1 — Historian" statement={data.agent_1_statement} />
        <AgentCard icon={Network} title="Network Analysis" agentName="Agent 2 — Network" statement={data.agent_2_statement} />
        <AgentCard icon={ShieldCheck} title="Compliance Check" agentName="Agent 3 — Compliance" statement={data.agent_3_statement} />
      </div>

      {/* Executive Summary */}
      <div className="glass rounded-xl p-5 border-l-4 border-primary">
        <p className="text-xs text-primary font-semibold uppercase tracking-wider mb-2">Executive Summary</p>
        <p className="text-sm leading-relaxed">{data.final_summary}</p>
      </div>

      {/* Scores */}
      <div className="glass rounded-xl p-5 space-y-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Risk Scores</p>
        <div className="grid md:grid-cols-2 gap-x-8 gap-y-3">
          <ScoreBar label="Z-Score (Behavioral)" value={rm.score_a_zscore} />
          <ScoreBar label="Isolation Forest" value={rm.score_b_isoforest} />
          <ScoreBar label="Rule Engine" value={rm.score_c_rules} />
          <ScoreBar label="Final Risk Score" value={rm.risk_score} />
        </div>
      </div>

      {/* Triggered Rules */}
      {rm.triggered_rules.length > 0 && (
        <div className="glass rounded-xl p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Triggered Rules</p>
          <div className="flex flex-wrap gap-2">
            {rm.triggered_rules.map(rule => (
              <span key={rule} className="px-2.5 py-1 rounded-md bg-destructive/10 text-destructive text-xs font-mono">
                {rule}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Human-in-the-loop */}
      <div className="glass rounded-xl p-5 border border-risk-medium/30 bg-risk-medium/5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-risk-medium mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-semibold">Human Review Required</p>
            <p className="text-xs text-muted-foreground mt-1">
              This analysis was generated by AI agents. There may be flaws or misconceptions. Please have a human review before taking final action.
            </p>
          </div>
        </div>
      </div>

      {/* Decision buttons */}
      <div className="flex flex-wrap gap-3">
        {decisionButtons.map(({ label, icon: Icon, variant }) => (
          <Button
            key={label}
            variant={variant}
            onClick={() => handleDecision(label)}
            disabled={deciding}
            className="gap-2"
          >
            <Icon className="w-4 h-4" />
            {label}
          </Button>
        ))}
      </div>
    </div>
  );
};

export default Investigation;
