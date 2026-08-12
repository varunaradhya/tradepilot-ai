import { useState } from "react";

import { api, type HealthStatus } from "../services/api";

export function HomePage() {
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);

  async function checkApiHealth() {
    setIsCheckingHealth(true);
    setHealthError(null);

    try {
      setHealthStatus(await api.getHealth());
    } catch {
      setHealthStatus(null);
      setHealthError("The API could not be reached.");
    } finally {
      setIsCheckingHealth(false);
    }
  }

  return (
    <section className="max-w-3xl">
      <p className="mb-4 text-sm font-medium uppercase tracking-[0.2em] text-sky-400">
        Foundation
      </p>
      <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
        TradePilot AI
      </h1>
      <p className="mt-6 text-lg leading-8 text-slate-300">
        AI-powered stock portfolio tracking and analysis platform.
      </p>
      <p className="mt-4 max-w-2xl leading-7 text-slate-400">
        The application shell and API service are ready for portfolio features in
        future sprints.
      </p>

      <div className="mt-10 rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-base font-semibold text-white">API connection</h2>
        <p className="mt-2 text-sm text-slate-400">
          Verify communication with the FastAPI health endpoint.
        </p>
        <button
          className="mt-5 rounded-lg bg-sky-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isCheckingHealth}
          onClick={checkApiHealth}
          type="button"
        >
          {isCheckingHealth ? "Checking..." : "Check API health"}
        </button>
        {healthStatus && (
          <p className="mt-4 text-sm text-emerald-400">
            API status: {healthStatus.status}
          </p>
        )}
        {healthError && <p className="mt-4 text-sm text-rose-400">{healthError}</p>}
      </div>
    </section>
  );
}
