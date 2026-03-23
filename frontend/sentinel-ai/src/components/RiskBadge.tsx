import { cn } from "@/lib/utils";

const riskStyles: Record<string, string> = {
  CRITICAL: "bg-risk-critical/15 text-risk-critical border-risk-critical/30",
  HIGH: "bg-risk-high/15 text-risk-high border-risk-high/30",
  MEDIUM: "bg-risk-medium/15 text-risk-medium border-risk-medium/30",
  LOW: "bg-risk-low/15 text-risk-low border-risk-low/30",
};

export const RiskBadge = ({ label }: { label: string }) => (
  <span className={cn(
    "px-2.5 py-0.5 rounded-full text-xs font-bold border uppercase tracking-wider",
    riskStyles[label] || "bg-muted text-muted-foreground"
  )}>
    {label}
  </span>
);
