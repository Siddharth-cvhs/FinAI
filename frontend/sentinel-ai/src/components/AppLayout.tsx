import { NavLink, Outlet } from "react-router-dom";
import { Activity, FileText, Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/ThemeToggle";

const tabs = [
  { to: "/monitoring", label: "Live Monitoring", icon: Activity },
  { to: "/logs", label: "Monitored Logs", icon: FileText },
];

const AppLayout = () => (
  <div className="min-h-screen flex flex-col">
    <header className="glass border-b border-border/50 sticky top-0 z-40">
      <div className="max-w-[1400px] mx-auto px-6 h-14 flex items-center gap-6">
        <NavLink to="/" className="flex items-center gap-2 shrink-0">
          <Shield className="w-5 h-5 text-primary" />
          <span className="font-bold text-sm tracking-tight">FinAI</span>
        </NavLink>
        <nav className="flex gap-1">
          {tabs.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors",
                isActive ? "bg-primary/10 text-primary font-semibold" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </div>
    </header>
    <main className="flex-1">
      <Outlet />
    </main>
  </div>
);

export default AppLayout;
