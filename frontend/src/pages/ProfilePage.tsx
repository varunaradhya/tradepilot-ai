import { FormEvent, useEffect, useState } from "react";
import { api, User } from "../services/api";
import { logout } from "../services/auth";

type Props = { onBack: () => void };

export default function ProfilePage({ onBack }: Props) {
  const [user, setUser] = useState<User | null>(null);
  const [fullName, setFullName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void api.get<User>("/users/me").then(profile => {
      setUser(profile);
      setFullName(profile.full_name);
    }).catch(err => setError(err instanceof Error ? err.message : "Unable to load profile."));
  }, []);

  async function saveProfile(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); setMessage("");
    try {
      const updated = await api.put<User>("/users/me", { full_name: fullName });
      setUser(updated); setFullName(updated.full_name); setMessage("Profile updated successfully.");
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to update profile."); }
    finally { setSaving(false); }
  }

  async function changePassword(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); setMessage("");
    if (newPassword.length < 8) { setError("New password must be at least 8 characters."); setSaving(false); return; }
    if (newPassword !== confirmPassword) { setError("New passwords do not match."); setSaving(false); return; }
    try {
      await api.post("/users/me/change-password", { current_password: currentPassword, new_password: newPassword });
      setCurrentPassword(""); setNewPassword(""); setConfirmPassword(""); setMessage("Password changed successfully.");
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to change password."); }
    finally { setSaving(false); }
  }

  return <main className="mx-auto max-w-5xl px-6 py-8">
    <div className="mb-6 flex items-center justify-between"><div><p className="text-xs font-bold uppercase tracking-[.18em] text-sky-400">Account</p><h1 className="mt-2 text-3xl font-bold text-white">Profile & Security</h1><p className="mt-1 text-sm text-slate-500">Manage your TradePilot account and security.</p></div><button onClick={onBack} className="rounded-xl border border-white/10 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-white/5">Back</button></div>
    {(message || error) && <div className={`mb-5 rounded-xl border p-3 text-sm ${error ? "border-rose-500/20 bg-rose-500/10 text-rose-300" : "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"}`}>{error || message}</div>}
    <div className="grid gap-5 lg:grid-cols-2">
      <section className="rounded-2xl border border-white/10 bg-white/[.03] p-6"><h2 className="text-lg font-bold text-white">Personal information</h2><form onSubmit={(e) => void saveProfile(e)} className="mt-5 space-y-4"><label className="block text-sm text-slate-300">Full name<input value={fullName} onChange={e => setFullName(e.target.value)} required className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-white outline-none focus:border-sky-400" /></label><label className="block text-sm text-slate-300">Email<input value={user?.email ?? ""} disabled className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2.5 text-slate-500" /></label><button disabled={saving} className="rounded-xl bg-sky-400 px-4 py-2.5 font-bold text-slate-950 disabled:opacity-50">Save changes</button></form></section>
      <section className="rounded-2xl border border-white/10 bg-white/[.03] p-6"><h2 className="text-lg font-bold text-white">Change password</h2><form onSubmit={(e) => void changePassword(e)} className="mt-5 space-y-4"><input required type="password" placeholder="Current password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-white" /><input required minLength={8} type="password" placeholder="New password" value={newPassword} onChange={e => setNewPassword(e.target.value)} className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-white" /><input required minLength={8} type="password" placeholder="Confirm new password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-white" /><button disabled={saving} className="rounded-xl border border-white/10 px-4 py-2.5 font-bold text-white hover:bg-white/5 disabled:opacity-50">Update password</button></form></section>
      <section className="rounded-2xl border border-rose-500/15 bg-rose-500/[.03] p-6 lg:col-span-2"><h2 className="text-lg font-bold text-white">Sign out</h2><p className="mt-1 text-sm text-slate-500">End the current TradePilot session on this browser.</p><button onClick={logout} className="mt-4 rounded-xl border border-rose-500/20 px-4 py-2.5 font-bold text-rose-300 hover:bg-rose-500/10">Sign out</button></section>
    </div>
  </main>;
}
