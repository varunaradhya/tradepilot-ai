import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = { children: ReactNode };

type State = { hasError: boolean; error: Error | null };

export default class AppErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("TradePilot UI runtime error", error, info.componentStack);
  }

  retry = () => {
    this.setState({ hasError: false, error: null });
  };

  resetSession = () => {
    localStorage.removeItem("access_token");
    window.location.reload();
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070b14] p-6 text-white">
        <section className="w-full max-w-xl rounded-3xl border border-rose-400/20 bg-white/[.03] p-8 shadow-2xl backdrop-blur-xl">
          <div className="flex items-start gap-4">
            <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-rose-400/10 text-xl text-rose-300">!</div>
            <div>
              <p className="text-[10px] font-black uppercase tracking-[.2em] text-rose-300">UI runtime protection</p>
              <h1 className="mt-2 text-2xl font-black">TradePilot hit a screen error</h1>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                The production build is valid, but a browser-side error stopped this screen from rendering. Your data has not been modified.
              </p>
            </div>
          </div>
          <details className="mt-6 rounded-2xl border border-white/10 bg-black/20 p-4">
            <summary className="cursor-pointer text-xs font-bold text-slate-400">Technical details</summary>
            <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap break-words text-[11px] leading-5 text-rose-200">{this.state.error?.stack ?? this.state.error?.message ?? "Unknown UI error"}</pre>
          </details>
          <div className="mt-6 flex flex-wrap gap-3">
            <button type="button" onClick={this.retry} className="rounded-xl bg-white px-5 py-3 text-xs font-black text-slate-950 hover:bg-slate-200">Try again</button>
            <button type="button" onClick={this.resetSession} className="rounded-xl border border-white/10 bg-white/[.04] px-5 py-3 text-xs font-black text-slate-200 hover:bg-white/[.08]">Reset session & reload</button>
          </div>
        </section>
      </main>
    );
  }
}
