import { useEffect, useState } from "react";

import AuthPage from "./pages/AuthPage";
import BrokerPage from "./pages/BrokerPage";
import DashboardPage from "./pages/DashboardPage";
import IntradayScannerPage from "./pages/IntradayScannerPage";
import MarketPage from "./pages/MarketPage";
import PortfolioPage from "./pages/PortfolioPage";
import ResearchPage from "./pages/ResearchPage";
import StrategyBuilderPage from "./pages/StrategyBuilderPage";
import ToolsPage from "./pages/ToolsPage";
import TransactionsPage from "./pages/TransactionsPage";
import { isAuthenticated, logout } from "./services/auth";

type Page = "dashboard" | "research" | "scanner" | "strategy" | "transactions" | "market" | "portfolio" | "brokers" | "tools";

const navItems: Array<{ id: Page; label: string }> = [
  { id: "dashboard", label: "Overview" },
  { id: "research", label: "Research" },
  { id: "scanner", label: "Intraday Scanner" },
  { id: "strategy", label: "Strategy Builder" },
  { id: "portfolio", label: "Portfolio" },
  { id: "transactions", label: "Transactions" },
  { id: "market", label: "Markets" },
  { id: "tools", label: "Tools" },
  { id: "brokers", label: "Brokers" },
];

function Navigation({ page, setPage }: { page: Page; setPage: (page: Page) => void }) {
  return <nav className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 px-4 py-2 backdrop-blur"><div className="mx-auto flex max-w-7xl items-center gap-2 overflow-x-auto"><div className="mr-3 whitespace-nowrap text-sm font-extrabold text-slate-950">TradePilot</div>{navItems.map(item => <button key={item.id} type="button" onClick={() => setPage(item.id)} className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-semibold transition-all duration-200 ${page === item.id ? "bg-slate-950 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"}`}>{item.label}</button>)}</div></nav>;
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated);
  const [page, setPage] = useState<Page>("dashboard");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  useEffect(() => { const syncAuth = () => { setAuthenticated(isAuthenticated()); setPage("dashboard"); }; window.addEventListener("tradepilot:login", syncAuth); window.addEventListener("tradepilot:logout", syncAuth); return () => { window.removeEventListener("tradepilot:login", syncAuth); window.removeEventListener("tradepilot:logout", syncAuth); }; }, []);
  if (!authenticated) return <AuthPage mode={authMode} onModeChange={setAuthMode} onAuthenticated={() => setAuthenticated(true)} />;
  return <><Navigation page={page} setPage={setPage} />{page === "dashboard" && <DashboardPage onLogout={logout} onTransactions={() => setPage("transactions")} />}{page === "research" && <ResearchPage />}{page === "scanner" && <IntradayScannerPage />}{page === "strategy" && <StrategyBuilderPage />}{page === "transactions" && <TransactionsPage onBack={() => setPage("dashboard")} />}{page === "market" && <MarketPage />}{page === "portfolio" && <PortfolioPage />}{page === "tools" && <ToolsPage onBack={() => setPage("dashboard")} />}{page === "brokers" && <BrokerPage />}</>;
}
