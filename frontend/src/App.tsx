import { useEffect, useMemo, useState } from "react";
import AuthPage from "./pages/AuthPage";
import BrokerPage from "./pages/BrokerPage";
import DashboardPage from "./pages/DashboardPageStable";
import FNOPage from "./pages/FNOPage";
import IntradayEvidencePage from "./pages/IntradayEvidencePage";
import IntradayScannerPage from "./pages/IntradayScannerPage";
import MarketPage from "./pages/MarketPage";
import PaperTradingPage from "./pages/PaperTradingPage";
import PortfolioPage from "./pages/PortfolioPage";
import ProfilePage from "./pages/ProfilePage";
import ResearchPage from "./pages/ResearchPage";
import StrategyBuilderPage from "./pages/StrategyBuilderPage";
import ToolsPage from "./pages/ToolsPage";
import TradeDecisionPage from "./pages/TradeDecisionPage";
import TransactionsPage from "./pages/TransactionsPage";
import { isAuthenticated, logout } from "./services/auth";

type Page = "dashboard"|"research"|"evidence"|"scanner"|"strategy"|"decision"|"paper"|"fno"|"transactions"|"market"|"portfolio"|"brokers"|"tools"|"profile";
type NavItem = { id: Page; label: string; hint: string };
type NavGroup = { label: string; items: NavItem[] };

const navGroups: NavGroup[] = [
  { label: "Research", items: [
    { id: "research", label: "Research", hint: "Stock research workspace" },
    { id: "evidence", label: "Evidence", hint: "Cross-stock validation" },
    { id: "scanner", label: "Opportunity Scanner", hint: "Find qualified setups" },
  ]},
  { label: "Trading", items: [
    { id: "fno", label: "F&O Intelligence", hint: "NSE derivatives decision engine" },
    { id: "strategy", label: "Strategy Builder", hint: "Build and qualify strategies" },
    { id: "decision", label: "Trade Decision", hint: "Evaluate a trade" },
    { id: "paper", label: "Paper Trading", hint: "Simulation cockpit" },
  ]},
  { label: "Portfolio", items: [
    { id: "portfolio", label: "Portfolio", hint: "Holdings and returns" },
    { id: "transactions", label: "Transactions", hint: "Transaction history" },
  ]},
  { label: "Market", items: [{ id: "market", label: "Markets", hint: "Market data" }] },
  { label: "Tools", items: [{ id: "tools", label: "Trading Tools", hint: "Trading utilities" }] },
  { label: "Connections", items: [{ id: "brokers", label: "Broker Center", hint: "Connections and safety" }] },
];
const allNavItems = navGroups.flatMap(g => g.items);
const validPages = new Set<Page>(["dashboard","research","evidence","scanner","strategy","decision","paper","fno","transactions","market","portfolio","brokers","tools","profile"]);

function pageFromHash(): Page {
  const value = window.location.hash.replace(/^#\/?/, "") as Page;
  return validPages.has(value) ? value : "dashboard";
}

function Workflow({ page, setPage }: { page: Page; setPage: (p: Page) => void }) {
  const steps: Array<{ id: Page; label: string }> = [
    { id: "research", label: "Research" },
    { id: "evidence", label: "Validate" },
    { id: "strategy", label: "Strategy" },
    { id: "decision", label: "Decision" },
    { id: "paper", label: "Paper" },
  ];
  const active = steps.findIndex(x => x.id === page);
  if (page === "dashboard" || page === "profile" || page === "portfolio" || page === "transactions" || page === "market" || page === "brokers" || page === "tools" || page === "fno" || page === "scanner") return null;
  return <div className="tp-workflow" aria-label="Trading research workflow">{steps.map((step, index) => <button type="button" key={step.id} onClick={() => setPage(step.id)} className={index === active ? "tp-workflow-step tp-workflow-active" : index < active ? "tp-workflow-step tp-workflow-done" : "tp-workflow-step"}><span>{index + 1}</span>{step.label}</button>)}</div>;
}

function CommandPalette({ open, onClose, setPage }: { open: boolean; onClose: () => void; setPage: (p: Page) => void }) {
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState(0);
  const filtered = useMemo(() => { const x = q.trim().toLowerCase(); return x ? allNavItems.filter(i => `${i.label} ${i.hint}`.toLowerCase().includes(x)) : allNavItems; }, [q]);
  useEffect(() => { if (open) { setQ(""); setSelected(0); } }, [open]);
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowDown") { e.preventDefault(); setSelected(i => Math.min(i + 1, Math.max(filtered.length - 1, 0))); }
      if (e.key === "ArrowUp") { e.preventDefault(); setSelected(i => Math.max(i - 1, 0)); }
      if (e.key === "Enter" && filtered[selected]) { setPage(filtered[selected].id); onClose(); }
    };
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  }, [open, onClose, filtered, selected, setPage]);
  if (!open) return null;
  return <div className="fixed inset-0 z-[100] flex items-start justify-center bg-black/70 px-4 pt-[10vh] backdrop-blur-sm" role="presentation" onMouseDown={onClose}>
    <section className="tp-command w-full max-w-2xl overflow-hidden rounded-2xl border shadow-2xl" role="dialog" aria-modal="true" aria-label="TradePilot navigation" onMouseDown={e => e.stopPropagation()}>
      <div className="border-b border-white/10 p-4"><input autoFocus value={q} onChange={e => { setQ(e.target.value); setSelected(0); }} placeholder="Search TradePilot…" aria-label="Search TradePilot pages" className="w-full bg-transparent text-base font-semibold outline-none" /></div>
      <div className="max-h-[55vh] overflow-y-auto p-2" role="listbox">{filtered.length === 0 ? <p className="p-5 text-sm text-slate-500">No matching workspace.</p> : filtered.map((i, n) => <button type="button" key={i.id} onMouseEnter={() => setSelected(n)} onClick={() => { setPage(i.id); onClose(); }} className={`flex w-full rounded-xl px-3 py-3 text-left ${selected === n ? "bg-white/10" : "hover:bg-white/5"}`}><span><b className="block text-sm text-white">{i.label}</b><span className="text-xs text-slate-500">{i.hint}</span></span></button>)}</div>
    </section>
  </div>;
}

function Navigation({ page, setPage, onCommand, onProfile }: { page: Page; setPage: (p: Page) => void; onCommand: () => void; onProfile: () => void }) {
  const [menu, setMenu] = useState(false);
  const [profile, setProfile] = useState(false);
  useEffect(() => {
    if (!menu && !profile) return;
    const close = () => { setMenu(false); setProfile(false); };
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    window.addEventListener("keydown", k); document.addEventListener("mousedown", close);
    return () => { window.removeEventListener("keydown", k); document.removeEventListener("mousedown", close); };
  }, [menu, profile]);
  return <header className="tp-nav sticky top-0 z-50 border-b px-4 py-3 backdrop-blur-xl">
    <div className="mx-auto flex max-w-[1440px] items-center gap-3">
      <button type="button" onClick={() => setMenu(v => !v)} aria-label="Open navigation menu" aria-expanded={menu} className="tp-icon-button flex h-10 w-10 shrink-0 flex-col items-center justify-center gap-1.5 rounded-xl border border-white/10 bg-white/[.03]"><span className="h-0.5 w-5 bg-slate-300"/><span className="h-0.5 w-5 bg-slate-300"/><span className="h-0.5 w-5 bg-slate-300"/></button>
      <button type="button" className="tp-brand mr-2" onClick={() => setPage("dashboard")} aria-label="Go to TradePilot overview"><img src="/tradepilot-mark.svg" alt="" /><span><span className="tp-brand-name block">TradePilot AI</span><span className="tp-brand-sub block">Intelligent trading cockpit</span></span></button>
      <nav aria-label="Primary navigation" className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
        {([
          ["dashboard", "Overview", page === "dashboard"],
          ["research", "Research", ["research", "evidence", "scanner"].includes(page)],
          ["fno", "Trade", ["fno", "strategy", "decision", "paper"].includes(page)],
          ["portfolio", "Portfolio", ["portfolio", "transactions"].includes(page)],
          ["market", "Markets", page === "market"],
        ] as Array<[Page, string, boolean]>).map(([id, label, active]) => (
          <button type="button" key={id} onClick={() => setPage(id)} className={`tp-nav-item whitespace-nowrap rounded-xl px-3 py-2 text-[12px] font-bold ${active ? "tp-nav-item-active" : ""}`}>{label}</button>
        ))}
      </nav>
      <button type="button" onClick={onCommand} aria-label="Search TradePilot pages" className="hidden items-center gap-2 rounded-xl border border-white/10 bg-white/[.03] px-3 py-2 text-[11px] font-bold text-slate-400 lg:flex">⌕ <span>Search</span><kbd>Ctrl K</kbd></button>
      <div className="relative">
        <button type="button" onClick={e => { e.stopPropagation(); setProfile(v => !v); setMenu(false); }} aria-label="Open account menu" aria-expanded={profile} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-sky-400/30 bg-sky-400/10 text-xs font-extrabold text-sky-300">TP</button>
        {profile && <div onMouseDown={e => e.stopPropagation()} className="absolute right-0 top-12 z-[60] w-56 rounded-2xl border border-white/10 bg-slate-950/95 p-2 shadow-2xl" role="menu"><button type="button" role="menuitem" onClick={() => { onProfile(); setProfile(false); }} className="w-full rounded-xl px-3 py-3 text-left text-sm font-semibold text-white">Profile & Security</button><button type="button" role="menuitem" onClick={() => { logout(); setProfile(false); }} className="w-full rounded-xl px-3 py-3 text-left text-sm font-semibold text-rose-300">Sign out</button></div>}
      </div>
      {menu && <div onMouseDown={e => e.stopPropagation()} className="absolute left-4 top-[68px] z-[60] w-72 max-h-[calc(100vh-88px)] overflow-y-auto rounded-2xl border border-white/10 bg-slate-950/95 p-2 shadow-2xl" role="menu">{navGroups.map(g => <div key={g.label} className="mb-2"><p className="px-3 py-2 text-[10px] font-bold uppercase tracking-[.16em] text-slate-600">{g.label}</p>{g.items.map(i => <button type="button" role="menuitem" key={i.id} onClick={() => { setPage(i.id); setMenu(false); }} className="w-full rounded-xl px-3 py-2.5 text-left text-sm font-semibold text-slate-300 hover:bg-white/5">{i.label}<span className="block text-[11px] font-normal text-slate-600">{i.hint}</span></button>)}</div>)}</div>}
    </div>
  </header>;
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated);
  const [page, setPageState] = useState<Page>(pageFromHash);
  const [authMode, setAuthMode] = useState<"login"|"register">("login");
  const [commandOpen, setCommandOpen] = useState(false);

  const setPage = (next: Page) => { setPageState(next); window.location.hash = `#/${next}`; window.scrollTo({ top: 0, behavior: "smooth" }); };

  useEffect(() => {
    const onHash = () => setPageState(pageFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  useEffect(() => {
    const sync = () => { setAuthenticated(isAuthenticated()); setPageState(pageFromHash()); };
    window.addEventListener("tradepilot:login", sync); window.addEventListener("tradepilot:logout", sync);
    return () => { window.removeEventListener("tradepilot:login", sync); window.removeEventListener("tradepilot:logout", sync); };
  }, []);
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setCommandOpen(true); } };
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  }, []);

  if (!authenticated) return <AuthPage mode={authMode} onModeChange={setAuthMode} onAuthenticated={() => { setAuthenticated(true); setPage("dashboard"); }} />;
  return <div className="tp-shell">
    <Navigation page={page} setPage={setPage} onCommand={() => setCommandOpen(true)} onProfile={() => setPage("profile")} />
    <Workflow page={page} setPage={setPage} />
    <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} setPage={setPage} />
    <main>
      {page === "dashboard" && <DashboardPage onLogout={logout} onTransactions={() => setPage("transactions")} />}
      {page === "fno" && <FNOPage />}
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
      {page === "profile" && <ProfilePage onBack={() => setPage("dashboard")} />}
    </main>
  </div>;
}
