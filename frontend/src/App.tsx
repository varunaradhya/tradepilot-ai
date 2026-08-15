import { useEffect, useState } from "react";

import AuthPage from "./pages/AuthPage";
import BrokerPage from "./pages/BrokerPage";
import DashboardPage from "./pages/DashboardPage";
import IntradayEvidencePage from "./pages/IntradayEvidencePage";
import IntradayScannerPage from "./pages/IntradayScannerPage";
import MarketPage from "./pages/MarketPage";
import PaperTradingPage from "./pages/PaperTradingPage";
import PortfolioPage from "./pages/PortfolioPage";
import ResearchPage from "./pages/ResearchPage";
import StrategyBuilderPage from "./pages/StrategyBuilderPage";
import ToolsPage from "./pages/ToolsPage";
import TradeDecisionPage from "./pages/TradeDecisionPage";
import TransactionsPage from "./pages/TransactionsPage";
import { isAuthenticated, logout } from "./services/auth";

type Page = "dashboard" | "research" | "evidence" | "scanner" | "strategy" | "decision" | "paper" | "transactions" | "market" | "portfolio" | "brokers" | "tools";

const navItems: Array<{ id: Page; label: string }> = [
  { id: "dashboard", label: "Overview" },
  { id: "research", label: "Research" },
  { id: "evidence", label: "Evidence" },
  { id: "scanner", label: "Scanner" },
  { id: "strategy", label: "Strategy" },
  { id: "decision", label: "Decision" },
  { id: "paper", label: "Paper" },
  { id: "portfolio", label: "Portfolio" },
  { id: "transactions", label: "Ledger" },
  { id: "market", label: "Markets" },
  { id: "tools", label: "Tools" },
  { id: "brokers", label: "Brokers" },
];

function Navigation({ page, setPage }: { page: Page; setPage: (page: Page) => void }) {
  return (
    <header className="tp-nav sticky top-0 z-50 border-b px-4 py-3 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1440px] items-center gap-3">
        <button type="button" className="tp-brand mr-2" onClick={() => setPage("dashboard")} aria-label="TradePilot home">
          <img src="/tradepilot-mark.svg" alt="" aria-hidden="true" />
          <span>
            <span className="tp-brand-name block">TradePilot AI</span>
            <span className="tp-brand-sub block">Intelligent trading cockpit</span>
          </span>
        </button>

        <div className="hidden h-7 w-px bg-white/10 xl:block" />
        <nav aria-label="Primary navigation" className="flex min-w-0 flex-1 gap-1 overflow-x-auto py-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {navItems.map(item => (
            <button
              key={item.id}
              type="button"
              onClick={() => setPage(item.id)}
              className={`tp-nav-item whitespace-nowrap rounded-xl px-3 py-2 text-[12px] font-bold transition-all duration-200 ${page === item.id ? "tp-nav-item-active" : ""}`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="hidden items-center gap-2 lg:flex">
          <span className="tp-status"><span className="tp-status-dot" />Paper mode</span>
          <button type="button" onClick={logout} className="rounded-xl border border-white/10 px-3 py-2 text-[12px] font-bold text-slate-300 transition hover:border-white/20 hover:bg-white/5 hover:text-white">
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated);
  const [page, setPage] = useState<Page>("dashboard");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");

  useEffect(() => {
    const syncAuth = () => {
      setAuthenticated(isAuthenticated());
      setPage("dashboard");
    };
    window.addEventListener("tradepilot:login", syncAuth);
    window.addEventListener("tradepilot:logout", syncAuth);
    return () => {
      window.removeEventListener("tradepilot:login", syncAuth);
      window.removeEventListener("tradepilot:logout", syncAuth);
    };
  }, []);

  if (!authenticated) return <AuthPage mode={authMode} onModeChange={setAuthMode} onAuthenticated={() => setAuthenticated(true)} />;

  return (
    <div className="tp-shell">
      <Navigation page={page} setPage={setPage} />
      <main>
        {page === "dashboard" && <DashboardPage onLogout={logout} onTransactions={() => setPage("transactions")} />}
        {page === "research" && <ResearchPage />}
        {page === "evidence" && <IntradayEvidencePage />}
        {page === "scanner" && <IntradayScannerPage />}
        {page === "strategy" && <StrategyBuilderPage />}
        {page === "decision" && <TradeDecisionPage />}
        {page === "paper" && <PaperTradingPage />}
        {page === "transactions" && <TransactionsPage onBack={() => setPage("dashboard")} />}
        {page === "market" && <MarketPage />}
        {page === "portfolio" && <PortfolioPage />}
        {page === "tools" && <ToolsPage onBack={() => setPage("dashboard")} />}
        {page === "brokers" && <BrokerPage />}
      </main>
    </div>
  );
}
