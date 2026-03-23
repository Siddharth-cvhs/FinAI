import { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, AlertTriangle } from "lucide-react";
import { streamTransactions, Transaction } from "@/lib/api";
import { TransactionRow } from "@/components/TransactionRow";
import { useToast } from "@/hooks/use-toast";
import { motion, AnimatePresence } from "framer-motion";

const LiveMonitoring = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [investigatingId, setInvestigatingId] = useState<string | null>(null);
  const seenIds = useRef(new Set<string>());
  const navigate = useNavigate();
  const { toast } = useToast();

  const poll = useCallback(async (signal: AbortSignal) => {
    try {
      const batch = await streamTransactions(3, signal);
      setTransactions(prev => {
        const newTxns = batch.filter(t => !seenIds.current.has(t.Transaction_ID));
        newTxns.forEach(t => seenIds.current.add(t.Transaction_ID));
        if (newTxns.length === 0) return prev;
        const merged = [...prev, ...newTxns];
        return merged.slice(-200); // keep latest at bottom
      });
    } catch (e: any) {
      if (e.name !== "AbortError") {
        toast({ title: "Connection error", description: "Failed to fetch transactions", variant: "destructive" });
      }
    }
  }, [toast]);

  useEffect(() => {
    const controller = new AbortController();
    const id = setInterval(() => poll(controller.signal), 2000);
    poll(controller.signal);
    return () => { clearInterval(id); controller.abort(); };
  }, [poll]);

  const handleInvestigate = (txId: string) => {
    setInvestigatingId(txId);
    navigate(`/investigate/${txId}`);
  };

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary/10">
          <Activity className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold">Live Monitoring</h1>
          <p className="text-sm text-muted-foreground">
            Streaming transactions • {transactions.length} in buffer
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
          <span className="w-2 h-2 rounded-full bg-risk-low animate-pulse-glow" />
          Polling every 2s
        </div>
      </div>

      {transactions.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <AlertTriangle className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground">Waiting for transactions…</p>
          <p className="text-xs text-muted-foreground/60 mt-1">Make sure the backend is running on port 8000</p>
        </div>
      ) : (
        <div className="glass rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="py-3 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">ID</th>
                  <th className="py-3 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">User</th>
                  <th className="py-3 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Amount</th>
                  <th className="py-3 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Location</th>
                  <th className="py-3 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Time</th>
                  <th className="py-3 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">IP</th>
                  <th className="py-3 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden xl:table-cell">Destination</th>
                  <th className="py-3 px-4"></th>
                </tr>
              </thead>
              <AnimatePresence initial={false}>
                <tbody>
                  {transactions.map((tx, idx) => (
                    <motion.tr
                      key={tx.Transaction_ID}
                      layout
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -12 }}
                      transition={{ duration: 0.35, ease: "easeOut", delay: Math.min(idx, 5) * 0.02 }}
                      className="border-b border-border/50 hover:bg-muted/30 transition-colors"
                    >
                      <td className="py-3 px-4 font-mono text-xs text-primary">{tx.Transaction_ID}</td>
                      <td className="py-3 px-4 text-sm">{tx.User_ID}</td>
                      <td className="py-3 px-4 text-sm font-semibold">{tx.Amount}</td>
                      <td className="py-3 px-4 text-sm">{tx.Location}</td>
                      <td className="py-3 px-4 text-xs text-muted-foreground font-mono">
                        {new Date(tx.Timestamp).toLocaleTimeString()}
                      </td>
                      <td className="py-3 px-4 text-xs text-muted-foreground font-mono hidden lg:table-cell">{tx.Origin_IP}</td>
                      <td className="py-3 px-4 text-xs text-muted-foreground hidden xl:table-cell">{tx.Destination_Account}</td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleInvestigate(tx.Transaction_ID)}
                          disabled={investigatingId === tx.Transaction_ID}
                          className="inline-flex items-center gap-1.5 h-9 rounded-md px-3 text-sm font-medium bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors disabled:opacity-50"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                          Investigate
                        </button>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </AnimatePresence>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default LiveMonitoring;
