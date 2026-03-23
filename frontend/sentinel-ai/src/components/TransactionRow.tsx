import { Transaction } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Search } from "lucide-react";

interface Props {
  tx: Transaction;
  onInvestigate: (id: string) => void;
  loading?: boolean;
}

export const TransactionRow = ({ tx, onInvestigate, loading }: Props) => (
  <tr className="border-b border-border/50 hover:bg-muted/30 transition-colors">
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
      <Button
        size="sm"
        variant="secondary"
        onClick={() => onInvestigate(tx.Transaction_ID)}
        disabled={loading}
        className="gap-1.5"
      >
        <Search className="w-3.5 h-3.5" />
        Investigate
      </Button>
    </td>
  </tr>
);
