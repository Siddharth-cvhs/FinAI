import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import GetStarted from "./pages/GetStarted";
import LiveMonitoring from "./pages/LiveMonitoring";
import Investigation from "./pages/Investigation";
import MonitoredLogs from "./pages/MonitoredLogs";
import AppLayout from "./components/AppLayout";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<GetStarted />} />
          <Route element={<AppLayout />}>
            <Route path="/monitoring" element={<LiveMonitoring />} />
            <Route path="/investigate/:txId" element={<Investigation />} />
            <Route path="/logs" element={<MonitoredLogs />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
