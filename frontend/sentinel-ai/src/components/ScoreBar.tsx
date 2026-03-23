interface ScoreBarProps {
  label: string;
  value: number;
  max?: number;
  color?: string;
}

export const ScoreBar = ({ label, value, max = 1, color }: ScoreBarProps) => {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100);
  const barColor = color || (pct > 75 ? "bg-risk-critical" : pct > 50 ? "bg-risk-high" : pct > 25 ? "bg-risk-medium" : "bg-risk-low");

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono font-semibold">{value.toFixed(3)}</span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
};
