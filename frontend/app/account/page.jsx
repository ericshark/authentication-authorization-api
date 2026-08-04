"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BadgeCheck,
  CalendarDays,
  Check,
  CircleDashed,
  Download,
  Fingerprint,
  KeyRound,
  LockKeyhole,
  LogOut,
  Mail,
  Save,
  ShieldAlert,
  Trash2,
  UserRound,
} from "lucide-react";
import { useAuth, useToast } from "@/app/providers";
import { apiRequest } from "@/lib/api";

export default function AccountPage() {
  const { user, authLoading, refreshUser } = useAuth();
  const toast = useToast();
  const [profile, setProfile] = useState({ username: "", name: "", email: "" });
  const [passwords, setPasswords] = useState({ old_password: "", new_password: "" });
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState("");

  useEffect(() => {
    if (user) setProfile({ username: user.username || "", name: user.name || "", email: user.email || "" });
  }, [user]);

  async function saveProfile(event) {
    event.preventDefault();
    setSaving(true);
    try {
      await apiRequest("/users/update-me", { method: "PATCH", json: profile });
      await refreshUser();
      toast("Profile updated");
    } catch (error) { toast(error.message, "error"); }
    finally { setSaving(false); }
  }

  async function changePassword(event) {
    event.preventDefault();
    setSaving(true);
    try {
      await apiRequest("/auth/password", { method: "PATCH", json: passwords });
      setPasswords({ old_password: "", new_password: "" });
      await refreshUser();
      toast("Password changed. All sessions were revoked.");
    } catch (error) { toast(error.message, "error"); }
    finally { setSaving(false); }
  }

  async function downloadExport() {
    try {
      const { data } = await apiRequest("/users/me/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `aegis-account-${user.username}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      toast("Account export downloaded");
    } catch (error) { toast(error.message, "error"); }
  }

  async function logout() {
    try {
      await apiRequest("/auth/logout");
      await refreshUser();
      toast("Signed out");
    } catch (error) { toast(error.message, "error"); }
  }

  async function deleteAccount() {
    if (confirmDelete !== user.username) return toast("Type your exact username to confirm", "error");
    try {
      await apiRequest("/users/me/delete", { method: "DELETE" });
      await refreshUser();
      toast("Account deactivated");
    } catch (error) { toast(error.message, "error"); }
  }

  if (authLoading) return <div className="page-loading"><CircleDashed className="spin" size={26} /><span>Loading account</span></div>;
  if (!user) return <div className="signed-out-state"><span><LockKeyhole size={28} /></span><h1>Account settings are protected</h1><p>Sign in from the command center to manage profile and credentials.</p><Link className="button button-primary" href="/">Go to sign in <ArrowRight size={16} /></Link></div>;

  return (
    <div className="standard-page account-page">
      <header className="page-header">
        <div><span className="eyebrow">Identity settings</span><h1>Your account, your control.</h1><p>Manage the public identity layer, rotate your primary credential, and export or deactivate your data.</p></div>
        <button className="button button-secondary" onClick={logout}><LogOut size={16} /> Sign out here</button>
      </header>

      <section className="identity-banner">
        <div className="large-avatar">{(user.name || user.username)[0].toUpperCase()}</div>
        <div className="identity-banner-main"><span className="status-pill status-live"><BadgeCheck size={13} /> Active account</span><h2>{user.name || user.username}</h2><p>@{user.username} · {user.email}</p></div>
        <div className="identity-meta"><div><CalendarDays size={16} /><span><small>Member since</small><strong>{formatDate(user.date_created)}</strong></span></div><div><Fingerprint size={16} /><span><small>Account role</small><strong>{user.role}</strong></span></div></div>
      </section>

      <section className="account-grid">
        <form className="panel settings-card" onSubmit={saveProfile}>
          <div className="panel-head"><div><span className="eyebrow">Profile</span><h3>Identity details</h3><p>These are the safe fields returned by the current-user route.</p></div><UserRound size={21} /></div>
          <div className="form-row"><Field icon={UserRound} label="Full name" name="name" value={profile.name} onChange={(event) => setProfile({ ...profile, name: event.target.value })} /><Field icon={Fingerprint} label="Username" name="username" value={profile.username} onChange={(event) => setProfile({ ...profile, username: event.target.value })} /></div>
          <Field icon={Mail} label="Email address" name="email" type="email" value={profile.email} onChange={(event) => setProfile({ ...profile, email: event.target.value })} />
          <div className="form-action-row"><p><Check size={14} /> Unique fields are enforced by the database.</p><button className="button button-primary" disabled={saving}><Save size={16} /> Save profile</button></div>
        </form>

        <div className="panel settings-card data-card">
          <div className="panel-head"><div><span className="eyebrow">Portability</span><h3>Account data export</h3><p>Download a safe JSON snapshot generated at request time.</p></div><Download size={21} /></div>
          <div className="export-preview"><div><span>PROFILE</span><code>username, name, email, role</code></div><div><span>SECURITY</span><code>2FA status, providers, session count</code></div><div className="export-blocked"><span>NEVER EXPORTED</span><code>passwords, tokens, secrets</code></div></div>
          <button className="button button-secondary full-button" onClick={downloadExport}><Download size={16} /> Download JSON export</button>
        </div>
      </section>

      <section className="panel password-card">
          <div className="password-copy"><span className="password-icon"><KeyRound size={21} /></span><div><span className="eyebrow">Primary credential</span><h3>Change password</h3><p>The current password is verified with Argon2. A successful change revokes every device and clears this browser&apos;s auth cookies.</p></div></div>
        <form onSubmit={changePassword}><Field icon={LockKeyhole} label="Current password" type="password" value={passwords.old_password} onChange={(event) => setPasswords({ ...passwords, old_password: event.target.value })} /><Field icon={KeyRound} label="New password" type="password" value={passwords.new_password} onChange={(event) => setPasswords({ ...passwords, new_password: event.target.value })} /><button className="button button-primary" disabled={saving}><KeyRound size={16} /> Change password</button></form>
      </section>

      <section className="danger-zone">
        <div className="danger-copy"><span><ShieldAlert size={21} /></span><div><small>Danger zone</small><h3>Deactivate this account</h3><p>This soft-deletes the identity, revokes authentication, and prevents future sign-ins.</p></div></div>
        <div className="danger-confirm"><label className="field"><span>Type <strong>{user.username}</strong> to confirm</span><input value={confirmDelete} onChange={(event) => setConfirmDelete(event.target.value)} placeholder={user.username} /></label><button className="button button-danger" onClick={deleteAccount}><Trash2 size={16} /> Deactivate account</button></div>
      </section>
    </div>
  );
}

function Field({ icon: Icon, label, ...props }) {
  return <label className="field icon-field"><span>{label}</span><div><Icon size={15} /><input required {...props} /></div></label>;
}

function formatDate(value) { return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value)); }
