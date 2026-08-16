import { FormEvent, useState } from "react";
import { api } from "../services/api";
import { login, register } from "../services/auth";

type AuthPageProps = { mode: "login" | "register"; onModeChange: (mode: "login" | "register") => void; onAuthenticated: () => void };

type AuthView = "auth" | "forgot";

export default function AuthPage({ mode, onModeChange, onAuthenticated }: AuthPageProps) {
  const [view, setView] = useState<AuthView>("auth");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const registering = mode === "register";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setMessage("");
    if (registering && password !== confirmPassword) { setError("Passwords do not match."); return; }
    setLoading(true);
    try { if (registering) await register({ full_name: fullName, email, password }); else await login({ email, password }); onAuthenticated(); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Unable to authenticate. Please try again."); }
    finally { setLoading(false); }
  }

  async function forgot(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setMessage(""); setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setMessage("If an account exists for this email, password reset instructions will be sent.");
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Unable to process the request."); }
    finally { setLoading(false); }
  }

  return <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6"><section className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-2xl">
    <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-400">TradePilot AI</p>
    {view === "forgot" ? <><h1 className="mt-3 text-3xl font-bold text-white">Reset your password</h1><p className="mt-2 text-sm text-slate-400">Enter your account email and we will send reset instructions.</p><form className="mt-8 space-y-4" onSubmit={(e) => void forgot(e)}><label className="block text-sm text-slate-300">Email<input required type="email" value={email} onChange={e => setEmail(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white" /></label>{message && <p className="rounded-lg bg-emerald-950/50 p-3 text-sm text-emerald-300">{message}</p>}{error && <p className="rounded-lg bg-rose-950/60 p-3 text-sm text-rose-300">{error}</p>}<button disabled={loading} className="w-full rounded-lg bg-sky-400 px-4 py-2 font-semibold text-slate-950 disabled:opacity-60">{loading ? "Please wait..." : "Send reset instructions"}</button></form><button type="button" className="mt-6 w-full text-sm font-semibold text-sky-400" onClick={() => { setView("auth"); setMessage(""); setError(""); }}>Back to login</button></> : <><h1 className="mt-3 text-3xl font-bold text-white">{registering ? "Create your account" : "Welcome back"}</h1><p className="mt-2 text-sm text-slate-400">Portfolio intelligence, in one secure workspace.</p><form className="mt-8 space-y-4" onSubmit={(event) => void submit(event)}>{registering && <label className="block text-sm text-slate-300">Full name<input required value={fullName} onChange={e => setFullName(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white" /></label>}<label className="block text-sm text-slate-300">Email<input required type="email" value={email} onChange={e => setEmail(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white" /></label><label className="block text-sm text-slate-300">Password<input required minLength={registering ? 8 : 1} type="password" value={password} onChange={e => setPassword(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white" /></label>{registering && <label className="block text-sm text-slate-300">Confirm password<input required type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white" /></label>}{!registering && <div className="text-right"><button type="button" onClick={() => setView("forgot")} className="text-sm font-semibold text-sky-400 hover:text-sky-300">Forgot password?</button></div>}{error && <p className="rounded-lg bg-rose-950/60 p-3 text-sm text-rose-300">{error}</p>}<button disabled={loading} className="w-full rounded-lg bg-sky-400 px-4 py-2 font-semibold text-slate-950 disabled:opacity-60">{loading ? "Please wait..." : registering ? "Create account" : "Log in"}</button></form><p className="mt-6 text-center text-sm text-slate-400">{registering ? "Already have an account?" : "New to TradePilot?"} <button className="font-semibold text-sky-400" type="button" onClick={() => onModeChange(registering ? "login" : "register")}>{registering ? "Log in" : "Create an account"}</button></p></>}
  </section></main>;
}
