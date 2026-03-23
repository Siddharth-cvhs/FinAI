import { LucideIcon } from "lucide-react";

interface AgentCardProps {
  icon: LucideIcon;
  title: string;
  agentName: string;
  statement: string;
}

export const AgentCard = ({ icon: Icon, title, agentName, statement }: AgentCardProps) => (
  <div className="glass rounded-xl p-5 space-y-3">
    <div className="flex items-center gap-3">
      <div className="p-2 rounded-lg bg-primary/10">
        <Icon className="w-4 h-4 text-primary" />
      </div>
      <div>
        <p className="text-sm font-semibold">{title}</p>
        <p className="text-xs text-muted-foreground font-mono">{agentName}</p>
      </div>
    </div>
    <p className="text-sm text-secondary-foreground leading-relaxed">{statement}</p>
  </div>
);
