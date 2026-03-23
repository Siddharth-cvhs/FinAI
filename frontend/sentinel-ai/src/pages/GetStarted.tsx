import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Shield, Activity, Brain, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";

const features = [
  { icon: Activity, title: "Live Stream", desc: "Real-time transaction monitoring" },
  { icon: Brain, title: "AI Agents", desc: "Multi-agent fraud investigation" },
  { icon: Shield, title: "Risk Scoring", desc: "ML + heuristic risk analysis" },
  { icon: Zap, title: "Instant Action", desc: "Human-in-the-loop decisions" },
];

const GetStarted = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 relative overflow-hidden">
      {/* Background grid */}
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: `linear-gradient(hsl(var(--primary)) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--primary)) 1px, transparent 1px)`,
        backgroundSize: "60px 60px",
      }} />

      <div className="absolute top-4 right-4 z-20">
        <ThemeToggle />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="text-center max-w-3xl relative z-10"
      >
        <div className="flex items-center justify-center gap-3 mb-6">
          <div className="p-3 rounded-xl bg-primary/10 glow-primary">
            <Shield className="w-10 h-10 text-primary" />
          </div>
        </div>

        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-4">
          <span className="text-gradient-primary">FinAI</span>
        </h1>
        <p className="text-lg md:text-xl text-muted-foreground mb-2 font-light">
          Agentic AI for Real-Time Financial Transaction Fraud Detection
        </p>
        <p className="text-sm text-muted-foreground/60 font-mono mb-12">
          Powered by multi-agent investigation • ML scoring • Human-in-the-loop
        </p>

        <Button
          size="lg"
          onClick={() => navigate("/monitoring")}
          className="text-lg px-10 py-6 glow-primary font-semibold"
        >
          Get Started
        </Button>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.3 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-20 max-w-3xl w-full relative z-10"
      >
        {features.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 + i * 0.1 }}
            className="glass rounded-xl p-4 text-center"
          >
            <f.icon className="w-6 h-6 text-primary mx-auto mb-2" />
            <p className="text-sm font-semibold">{f.title}</p>
            <p className="text-xs text-muted-foreground mt-1">{f.desc}</p>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
};

export default GetStarted;
