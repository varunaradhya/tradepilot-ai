import { useEffect, useMemo, useState } from "react";

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

type NavItem = { id: Page; label: string; hint: string };

const navItems: NavItem[] = [
  { id: "dashboard", label: "Overview", hint: "Portfolio command center" },
  { id: "research", label: "Research", hint: "Research workspace" },
  { id: "evidence", label: "Evidence", hint: "Cross-stock validation" },
  { id: "scanner", label: "Scanner", hint: "Opportunity radar" },
  { id: "strategy", label: "Strategy", hint: "Build and qualify" },
  { id: "decision", label: "Decision", hint: "Trade decision lab" },
  { id: "paper", label: "Paper", hint: "Simulation cockpit" },
  { id: "portfolio", label: "Portfolio", hint: "Holdings and returns" },
  { id: "transactions", label: "Ledger", hint: "Transaction history" },
  { id: "market", label: "Markets", hint: "Market data" },
  { id: "tools", label: "Tools", hint: "Trading utilities" },
  { id: "brokers", label: "Brokers", hint: "Connections and safety" },
];

function CommandPalette({ open, onClose, page, setPage }: { open: boolean; onClose: () => void; page: Page; setPage: (page: Page) => void }) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? navItems.filter(item => `${item.label} ${item.hint}`.toLowerCase().includes(q)) : navItems;
  }, [query]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key === "Enter" && filtered.length > 0) {
        setPage(filtered[0].id);
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose, setPage, filtered]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center bg-black/65 px-4 pt-[12vh] backdrop-blur-sm" onMouseDown={onClose}>
      <section className="tp-command w-full max-w-2xl overflow-hidden rounded-2xl border shadow-2xl" onMouseDown={event => event.stopPropagation()} role="dialog" aria-modal="true" aria-label="TradePilot command palette">
        <div className="border-b border-white/10 p-4">
          <div className="flex items-center gap-3">
            <span className="text-lg text-slate-400">⌕</span>
            <input autoFocus value={query} onChange={event => setQuery(event.target.value)} placeholder="Search TradePilot…" className="w-full border-0 bg-transparent text-base font-semibold outline-none" />
            <kbd className="rounded-lg border border-white/10 px-2 py-1 text-[10px] font-bold text-slate-500">ESC</kbd>
          </div>
        </div>
        <div className="max-h-[55vh] overflow-y-auto p-2">
          {filtered.map(item => (
            <button key={item.id} type="button" onClick={() => { setPage(item.id); onClose(); }} className={`flex w-full items-center justify-between rounded-xl px-3 py-3 text-left transition hover:bg-white/5 ${page === item.id ? "bg-white/5" : ""}`}>
              <span><span className="block text-sm font-bold text-white">{item.label}</span><span className="block text-xs text-slate-500">{item.hint}</span></span>
              <span className="text-xs font-bold text-slate-600">↵</span>
            </button>
          ))}
          {filtered.length === 0 && <div className="p-8 text-center text-sm text-slate-500">No matching TradePilot destination.</div>}
        </div>
        <div className="flex items-center justify-between border-t border-white/10 px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-slate-600"><span>Command navigation</span><span>Enter open · Esc close</span></div>
      </section>
    </div>
  );
}

function Navigation({ page, setPage, onCommand }: { page: Page; setPage: (page: Page) => void; onCommand: () => void }) {
  return (
    <header className="tp-nav sticky top-0 z-50 border-b px-4 py-3 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1440px] items-center gap-3">
        <button type="button" className="tp-brand mr-2" onClick={() => setPage("dashboard")} aria-label="TradePilot home">
          <img src="/tradepilot-mark.svg" alt="" aria-hidden="true" />
          <span><span className="tp-brand-name block">TradePilot AI</span><span className="tp-brand-sub block">Intelligent trading cockpit</span></span>
        </button>
        <div className="hidden h-7 w-px bg-white/10 xl:block" />
        <nav aria-label="Primary navigation" className="flex min-w-0 flex-1 gap-1 overflow-x-auto py-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {navItems.map(item => <button key={item.id} type="button" onClick={() => setPage(item.id)} title={item.hint} className={`tp-nav-item whitespace-nowrap rounded-xl px-3 py-2 text-[12px] font-bold transition-all duration-200 ${page === item.id ? "tp-nav-item-active" : ""}`}>{item.label}</button>)}
        </nav>
        <button type="button" onClick={onCommand} className="hidden items-center gap-2 rounded-xl border border-white/10 bg-white/[.03] px-3 py-2 text-[11px] font-bold text-slate-400 transition hover:border-white/20 hover:text-white lg:flex" aria-label="Open command palette">
          <span>⌕</span><span>Search</span><kbd className="rounded border border-white/10 px-1.5 py-0.5 text-[9px] text-slate-600">Ctrl K</kbd>
        </button>
        <div className="hidden items-center gap-2 lg:flex"><span className="tp-status"><span className="tp-status-dot" />Paper mode</span><button type="button" onClick={logout} className="rounded-xl border border-white/10 px-3 py-2 text-[12px] font-bold text-slate-300 transition hover:border-white/20 hover:bg-white/5 hover:text-white">Sign out</button></div>
      </div>
    </header>
  );
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated);
  const [page, setPage] = useState<Page>("dashboard");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [commandOpen, setCommandOpen] = useState(false);

  useEffect(() => {
    const syncAuth = () => { setAuthenticated(isAuthenticated()); setPage("dashboard"); };
    window.addEventListener("tradepilot:login", syncAuth);
    window.addEventListener("tradepilot:logout", syncAuth);
    return () => { window.removeEventListener("tradepilot:login", syncAuth); window.removeEventListener("tradepilot:logout", syncAuth); };
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setCommandOpen(true); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!authenticated) return <AuthPage mode={authMode} onModeChange={setAuthMode} onAuthenticated={() => setAuthenticated(true)} />;

  return (
    <div className="tp-shell">
      <Navigation page={page} setPage={setPage} onCommand={() => setCommandOpen(true)} />
      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} page={page} setPage={setPage} />
      <div className="hidden border-b border-white/5 bg-white/[.015] lg:block"><div className="mx-auto flex max-w-[1440px] items-center justify-between px-7 py-2 text-[10px] font-bold uppercase tracking-[.12em] text-slate-600"><span>NSE • PAPER ENVIRONMENT</span><span>Live broker execution locked</span><span>Ctrl K command navigation</span></div></div>
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
