import type { ReactNode } from "react";

type AppLayoutProps = {
  children: ReactNode;
};

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/90">
        <nav
          aria-label="Primary navigation"
          className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4"
        >
          <a className="text-lg font-semibold tracking-tight" href="/">
            TradePilot AI
          </a>
          <span className="text-sm text-slate-400">Portfolio intelligence</span>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-16">{children}</main>
    </div>
  );
}
