"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Check,
  ChevronRight,
  CircleDashed,
  Clock3,
  Copy,
  Fingerprint,
  KeyRound,
  Laptop,
  LockKeyhole,
  LogOut,
  MonitorSmartphone,
  QrCode,
  RefreshCw,
  ShieldCheck,
  ShieldOff,
  Smartphone,
  Trash2,
} from "lucide-react";
import { useAuth, useToast } from "@/app/providers";
import { apiRequest } from "@/lib/api";

export default function SecurityPage() {
  const { user, authLoading, refreshUser } = useAuth();
  const toast = useToast();
  const [overview, setOverview] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [twoFactorSetup, setTwoFactorSetup] = useState(null);
  const [code, setCode] = useState("");
  const [backupCodes, setBackupCodes] = useState([]);

  const load = useCallback(async () => {
    if (!user) return setLoading(false);
    setLoading(true);
    const [overviewResult, sessionsResult, activityResult] = await Promise.allSettled([
      apiRequest("/users/me/overview"),
      apiRequest("/users/me/sessions"),
      apiRequest("/users/me/activity?limit=30"),
    ]);
    if (overviewResult.status === "fulfilled") setOverview(overviewResult.value.data);
    if (sessionsResult.status === "fulfilled") setSessions(sessionsResult.value.data);
    if (activityResult.status === "fulfilled") setActivity(activityResult.value.data);
    setLoading(false);
  }, [user]);

  useEffect(() => { load(); }, [load]);

  async function revoke(id) {
    try {
      await apiRequest(`/users/me/sessions/${encodeURIComponent(id)}`, { method: "DELETE" });
      toast("Device session revoked");
      load();
    } catch (error) { toast(error.message, "error"); }
  }

  async function revokeOthers() {
    try {
      const { data } = await apiRequest("/users/me/sessions", { method: "DELETE" });
      toast(`${data.revoked} other session(s) revoked`);
      load();
    } catch (error) { toast(error.message, "error"); }
  }

  async function beginTwoFactor() {
    try {
      const { data } = await apiRequest("/auth/2fa/setup", { method: "POST" });
      setTwoFactorSetup(data);
      toast("Authenticator secret created");
    } catch (error) { toast(error.message, "error"); }
  }

  async function confirmTwoFactor() {
    try {
      const { data } = await apiRequest("/auth/2fa/confirm", { method: "POST", json: { secret_token: code } });
      setBackupCodes(data.backup_codes || []);
      setTwoFactorSetup(null);
      setCode("");
      await refreshUser();
      await load();
      toast("Two-factor authentication enabled");
    } catch (error) { toast(error.message, "error"); }
  }

  async function disableTwoFactor() {
    try {
      await apiRequest("/auth/2fa/disable", { method: "POST", json: { secret_token: code } });
      setCode("");
      await refreshUser();
      await load();
      toast("Two-factor authentication disabled");
    } catch (error) { toast(error.message, "error"); }
  }

  async function regenerateCodes() {
    try {
      const { data } = await apiRequest("/users/me/backup-codes/regenerate", { method: "POST", json: { secret_token: code } });
      setBackupCodes(data.backup_codes || []);
      setCode("");
      load();
      toast("Recovery codes rotated");
    } catch (error) { toast(error.message, "error"); }
  }

  if (authLoading || loading) return <PageLoading label="Loading security posture" />;
  if (!user) return <SignedOutState />;

  const score = overview?.security_score || 0;

  return (
    <div className="standard-page">
      <header className="page-header">
        <div><span className="eyebrow">Security center</span><h1>Protect the whole account.</h1><p>Monitor sessions, strengthen sign-in, rotate recovery credentials, and inspect every security-sensitive event.</p></div>
        <div className={`risk-badge ${score >= 80 ? "risk-good" : "risk-warn"}`}><ShieldCheck size={18} /><span><small>Security score</small><strong>{score} / 100</strong></span></div>
      </header>

      <section className="security-overview-grid">
        <div className="panel posture-card">
          <div className="panel-head"><div><span className="eyebrow">Protection layers</span><h3>Account posture</h3></div><span className="status-pill status-live">Live</span></div>
          <div className="posture-score"><div className="score-ring score-ring-large" style={{ "--score": `${score * 3.6}deg` }}><div><strong>{score}</strong><span>points</span></div></div><div><h4>{score >= 80 ? "Your account is well protected" : "A few upgrades will make a big difference"}</h4><p>The score is calculated server-side from five transparent controls.</p></div></div>
          <div className="posture-checks">
            {(overview?.security_checks || []).map((item) => <div key={item.id}><span className={item.complete ? "complete" : "pending"}>{item.complete ? <Check size={13} /> : <CircleDashed size={13} />}</span><strong>{item.label}</strong><b>+{item.points}</b></div>)}
          </div>
        </div>

        <div className="panel factor-card">
          <div className="panel-head"><div><span className="eyebrow">Second factor</span><h3>Authenticator app</h3></div><span className={`status-pill ${user.totp_enabled ? "status-live" : "status-muted"}`}>{user.totp_enabled ? "Enabled" : "Not active"}</span></div>
          <div className="factor-hero"><span><Fingerprint size={31} /></span><div><h4>{user.totp_enabled ? "Sign-ins require a rotating code" : "Block password-only account takeover"}</h4><p>{user.totp_enabled ? "Your encrypted TOTP secret stays on the server and codes rotate every 30 seconds." : "Connect any standards-compatible authenticator and generate one-time recovery codes."}</p></div></div>
          {!user.totp_enabled && !twoFactorSetup && <button className="button button-primary" onClick={beginTwoFactor}><QrCode size={17} /> Set up authenticator</button>}
          {twoFactorSetup && <TwoFactorSetup setup={twoFactorSetup} code={code} setCode={setCode} confirm={confirmTwoFactor} />}
          {user.totp_enabled && <div className="factor-actions"><label className="field"><span>Current authenticator code</span><input value={code} onChange={(event) => setCode(event.target.value)} placeholder="123456" inputMode="numeric" /></label><div><button className="button button-secondary" onClick={regenerateCodes}><RefreshCw size={16} /> Rotate recovery codes</button><button className="button button-danger-ghost" onClick={disableTwoFactor}><ShieldOff size={16} /> Disable 2FA</button></div></div>}
        </div>
      </section>

      {backupCodes.length > 0 && <BackupCodes codes={backupCodes} onCopy={() => { navigator.clipboard.writeText(backupCodes.join("\n")); toast("Recovery codes copied"); }} />}

      <section className="panel sessions-panel">
        <div className="panel-head"><div><span className="eyebrow">Device control</span><h3>Active sessions</h3><p>Every valid refresh token or server session, normalized into one device view.</p></div><button className="button button-secondary" onClick={revokeOthers}><LogOut size={16} /> Revoke other devices</button></div>
        <div className="session-list">
          {sessions.length ? sessions.map((session) => <SessionRow session={session} onRevoke={() => revoke(session.id)} key={session.id} />) : <div className="empty-state compact"><MonitorSmartphone size={24} /><strong>No active sessions returned</strong></div>}
        </div>
      </section>

      <section className="panel activity-log-panel">
        <div className="panel-head"><div><span className="eyebrow">Security audit</span><h3>Account activity</h3><p>A bounded, newest-first event stream stored in Redis.</p></div><span className="event-count">{activity.length} events</span></div>
        <div className="activity-table">
          {activity.length ? activity.map((event) => <ActivityTableRow event={event} key={event.id} />) : <div className="empty-state"><Clock3 size={28} /><strong>No recorded activity</strong><p>Security-sensitive actions will appear here as they happen.</p></div>}
        </div>
      </section>
    </div>
  );
}

function TwoFactorSetup({ setup, code, setCode, confirm }) {
  return <div className="two-factor-setup"><div className="qr-frame"><img src={setup.qr_code} alt="Authenticator setup QR code" /></div><div><span className="step-label">STEP 1</span><h4>Scan this QR code</h4><p>Open your authenticator app and add a new account. Manual secret:</p><code className="secret-code">{setup.secret}</code><span className="step-label">STEP 2</span><label className="field"><span>Enter the generated code</span><input value={code} onChange={(event) => setCode(event.target.value)} placeholder="123456" /></label><button className="button button-primary" onClick={confirm}><Check size={16} /> Confirm and enable</button></div></div>;
}

function BackupCodes({ codes, onCopy }) {
  return <section className="backup-banner"><div className="backup-head"><span><KeyRound size={20} /></span><div><h3>Save these recovery codes now</h3><p>Each code works once. The server stores only their hashes, so this is the only time the plaintext values are available.</p></div><button className="button button-secondary" onClick={onCopy}><Copy size={15} /> Copy all</button></div><div className="code-grid">{codes.map((code) => <code key={code}>{code}</code>)}</div></section>;
}

function SessionRow({ session, onRevoke }) {
  const Device = session.device_name?.toLowerCase().includes("mobile") ? Smartphone : Laptop;
  return <div className="session-row"><span className="session-device"><Device size={20} /></span><div className="session-main"><div><strong>{session.device_name || "Unknown browser"}</strong>{session.current && <span className="current-badge">This device</span>}</div><span>{session.ip_address || "Unknown IP"} · Expires {formatDate(session.expires_at)}</span></div><div className="session-time"><Clock3 size={14} />{session.last_active ? formatDate(session.last_active) : "Refresh session"}</div><button className="icon-button danger-icon" disabled={session.current} onClick={onRevoke} title={session.current ? "Use sign out for this device" : "Revoke session"}><Trash2 size={17} /></button></div>;
}

function ActivityTableRow({ event }) {
  return <div className="activity-table-row"><span className="event-icon"><Activity size={16} /></span><div><strong>{humanize(event.action)}</strong><p>{event.detail}</p></div><span>{event.device_name || "Server"}</span><span>{event.ip_address || "—"}</span><time>{formatDate(event.created_at)}</time><ChevronRight size={15} /></div>;
}

function SignedOutState() {
  return <div className="signed-out-state"><span><LockKeyhole size={28} /></span><h1>Start a session first</h1><p>The security center reads protected account state. Sign in from the command center, then return here.</p><Link className="button button-primary" href="/">Go to sign in <ChevronRight size={16} /></Link></div>;
}

function PageLoading({ label }) {
  return <div className="page-loading"><CircleDashed className="spin" size={26} /><span>{label}</span></div>;
}

function humanize(value) { return value.split(".").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" "); }
function formatDate(value) { return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); }
