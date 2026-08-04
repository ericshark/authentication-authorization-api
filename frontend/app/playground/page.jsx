"use client";

import { useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Braces,
  Check,
  ChevronDown,
  CircleDashed,
  Clock3,
  Code2,
  Command,
  Copy,
  ExternalLink,
  FileJson,
  Filter,
  History,
  Info,
  Layers3,
  Play,
  RotateCcw,
  Search,
  Send,
  ServerCog,
  ShieldCheck,
  TerminalSquare,
  X,
  Zap,
} from "lucide-react";
import { useAuth, useToast } from "@/app/providers";
import { API_BASE, apiRequest, apiUrl } from "@/lib/api";
import { initialValues, routeCatalog, routeGroups } from "@/lib/route-catalog";

export default function PlaygroundPage() {
  const [selectedId, setSelectedId] = useState("register");
  const [search, setSearch] = useState("");
  const [group, setGroup] = useState("All");
  const [history, setHistory] = useState([]);

  const filtered = useMemo(() => routeCatalog.filter((route) => {
    const matchesGroup = group === "All" || route.group === group;
    const haystack = `${route.title} ${route.path} ${route.method} ${route.summary}`.toLowerCase();
    return matchesGroup && haystack.includes(search.toLowerCase());
  }), [group, search]);

  const selected = routeCatalog.find((route) => route.id === selectedId) || filtered[0] || routeCatalog[0];

  return (
    <div className="workbench-page">
      <header className="page-header workbench-header">
        <div><span className="eyebrow">Interactive API laboratory</span><h1>Route workbench.</h1><p>Select any FastAPI endpoint, shape the payload, send a real HTTP request, and inspect the full execution story.</p></div>
        <div className="workbench-stat"><span><Layers3 size={18} /></span><div><small>Connected routes</small><strong>{routeCatalog.length}</strong></div></div>
      </header>

      <section className="workbench-shell">
        <aside className="route-index">
          <div className="route-index-head">
            <label className="search-box"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search routes" />{search && <button onClick={() => setSearch("")}><X size={14} /></button>}</label>
            <label className="filter-select"><Filter size={14} /><select value={group} onChange={(event) => setGroup(event.target.value)}><option>All</option>{routeGroups.map((item) => <option key={item}>{item}</option>)}</select><ChevronDown size={13} /></label>
          </div>
          <div className="route-count"><span>{filtered.length} endpoints</span><code>{API_BASE}</code></div>
          <div className="route-scroll">
            {filtered.map((route) => <button className={`route-index-item ${selected.id === route.id ? "active" : ""}`} onClick={() => setSelectedId(route.id)} key={route.id}><span className={`method method-${route.method.toLowerCase()}`}>{route.method}</span><div><strong>{route.title}</strong><code>{route.path}</code></div><ArrowRight size={14} /></button>)}
            {!filtered.length && <div className="empty-filter"><Search size={20} /><p>No routes match this filter.</p></div>}
          </div>
        </aside>

        <RouteConsole route={selected} onComplete={(entry) => setHistory((current) => [entry, ...current].slice(0, 8))} />

        <aside className="history-rail">
          <div className="history-head"><span><History size={15} /> Request history</span><small>THIS SESSION</small></div>
          <div className="history-list">
            {history.length ? history.map((entry) => <button key={entry.id} onClick={() => setSelectedId(entry.routeId)}><span className={`history-status ${entry.ok ? "ok" : "error"}`} /> <div><strong>{entry.method} {entry.path}</strong><small>{entry.status} · {entry.duration}ms</small></div></button>) : <div className="empty-history"><Clock3 size={20} /><p>Sent requests will appear here.</p></div>}
          </div>
          <div className="proxy-note"><ShieldCheck size={16} /><div><strong>Same-origin proxy</strong><p>Next.js forwards /api/backend to FastAPI so credential cookies behave like production.</p></div></div>
        </aside>
      </section>
    </div>
  );
}

function RouteConsole({ route, onComplete }) {
  const { refreshUser } = useAuth();
  const toast = useToast();
  const [values, setValues] = useState(() => initialValues(route));
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const routeKey = route.id;
  const currentValues = values.__route === routeKey ? values : { ...initialValues(route), __route: routeKey };

  function update(name, value) {
    setValues({ ...currentValues, [name]: value, __route: routeKey });
  }

  async function execute() {
    if (route.external) {
      window.location.assign(apiUrl(route.path));
      return;
    }
    if (route.disabled) return;
    if (route.dangerous && !window.confirm(`Send the destructive ${route.method} ${route.path} request?`)) return;

    setLoading(true);
    const started = performance.now();
    let path = route.path;
    for (const name of route.params || []) path = path.replace(`{${name}}`, encodeURIComponent(currentValues[name] || ""));

    const query = new URLSearchParams();
    for (const name of route.query || []) if (currentValues[name] !== "") query.set(name, currentValues[name]);
    if ([...query].length) path += `?${query}`;

    const payload = Object.fromEntries((route.body || route.form || []).map((name) => {
      const raw = currentValues[name];
      return [name, (route.numeric || []).includes(name) && raw !== "" ? Number(raw) : raw];
    }).filter(([, value]) => !route.omitEmpty || value !== ""));

    const request = {
      method: route.method,
      url: `${API_BASE}${path}`,
      headers: route.form ? { "Content-Type": "application/x-www-form-urlencoded" } : route.body ? { "Content-Type": "application/json" } : {},
      body: route.form || route.body ? redact(payload) : null,
      credentials: "include",
    };

    try {
      const response = await apiRequest(path, { method: route.method, ...(route.form ? { form: payload } : route.body ? { json: payload } : {}) });
      const duration = Math.round(performance.now() - started);
      setResult({ ok: true, status: response.status, duration, request, data: response.data });
      if (route.refreshAuth) await refreshUser();
      toast(`${route.method} ${route.path} completed`);
      onComplete({ id: crypto.randomUUID(), routeId: route.id, method: route.method, path: route.path, status: response.status, duration, ok: true });
    } catch (error) {
      const duration = Math.round(performance.now() - started);
      setResult({ ok: false, status: error.status || "ERR", duration, request, data: error.data || { detail: error.message } });
      toast(error.message, "error");
      onComplete({ id: crypto.randomUUID(), routeId: route.id, method: route.method, path: route.path, status: error.status || "ERR", duration, ok: false });
    } finally { setLoading(false); }
  }

  function reset() {
    setValues({ ...initialValues(route), __route: routeKey });
    setResult(null);
  }

  return (
    <div className="route-console" key={route.id}>
      <div className="console-head">
        <div className="console-title-row"><span className={`method method-large method-${route.method.toLowerCase()}`}>{route.method}</span><div><span className="route-group">{route.group}</span><h2>{route.title}</h2></div></div>
        <button className="icon-button" onClick={reset} title="Reset form"><RotateCcw size={17} /></button>
      </div>
      <div className="endpoint-bar"><span className="endpoint-lock"><ShieldCheck size={14} /></span><code>{API_BASE}<strong>{route.path}</strong></code><button onClick={() => { navigator.clipboard.writeText(`${API_BASE}${route.path}`); toast("Endpoint copied"); }}><Copy size={14} /></button></div>
      <p className="console-summary">{route.summary}</p>

      <div className="console-section">
        <div className="console-section-title"><span><TerminalSquare size={15} /> Request builder</span><small>{route.fields?.length || 0} configurable fields</small></div>
        {route.fields?.length ? <div className="builder-fields">{route.fields.map((item) => <RouteField field={item} value={currentValues[item.name] || ""} onChange={(value) => update(item.name, value)} key={item.name} />)}</div> : <div className="no-payload"><Braces size={20} /><div><strong>No request payload</strong><p>This endpoint only needs the URL and any existing HTTP-only authentication cookie.</p></div></div>}
        {route.dangerous && <div className="danger-callout"><AlertTriangle size={16} /><span>This route changes security state or account access. The workbench asks for confirmation before sending it.</span></div>}
        <button className={`button ${route.dangerous ? "button-danger" : "button-primary"} send-button`} onClick={execute} disabled={loading || route.disabled}>
          {loading ? <CircleDashed className="spin" size={17} /> : route.external ? <ExternalLink size={17} /> : <Send size={17} />}
          {loading ? "Request in flight…" : route.external ? "Open authorization flow" : route.disabled ? "Handled automatically" : `Send ${route.method} request`}
          {!loading && !route.disabled && <span className="keyboard-hint">HTTP</span>}
        </button>
      </div>

      <div className="console-section under-hood-section">
        <div className="console-section-title"><span><ServerCog size={15} /> Under the hood</span><small>SERVER EXECUTION TRACE</small></div>
        <div className="execution-flow">
          {route.underHood.map((step, index) => <div className="execution-step" key={step}><span>{String(index + 1).padStart(2, "0")}</span><div><i>{index === 0 ? <Zap size={14} /> : index === route.underHood.length - 1 ? <Check size={14} /> : <Code2 size={14} />}</i><p>{step}</p></div></div>)}
        </div>
      </div>

      <div className="console-section response-section">
        <div className="console-section-title"><span><FileJson size={15} /> HTTP exchange</span>{result && <span className={`response-status ${result.ok ? "success" : "error"}`}><i /> {result.status} · {result.duration}ms</span>}</div>
        {result ? <div className="exchange-grid"><CodePanel label="REQUEST" value={result.request} /><CodePanel label="RESPONSE" value={result.data} /></div> : <div className="response-placeholder"><Play size={22} /><strong>Ready to send</strong><p>The exact outgoing request and parsed FastAPI response will appear here.</p></div>}
      </div>
    </div>
  );
}

function RouteField({ field, value, onChange }) {
  return <label className="field"><span>{field.label}<code>{field.name}</code></span>{field.type === "select" ? <select value={value} onChange={(event) => onChange(event.target.value)}>{field.options.map((option) => <option key={option}>{option}</option>)}</select> : <input type={field.type || "text"} value={value} onChange={(event) => onChange(event.target.value)} placeholder={field.label} />}</label>;
}

function CodePanel({ label, value }) {
  const text = JSON.stringify(value, null, 2);
  return <div className="code-panel"><div><span>{label}</span><button onClick={() => navigator.clipboard.writeText(text)}><Copy size={13} /> Copy</button></div><pre>{text}</pre></div>;
}

function redact(payload) {
  return Object.fromEntries(Object.entries(payload).map(([key, value]) => [key, key.toLowerCase().includes("password") || key.includes("token") || key === "code" ? "••••••••" : value]));
}
