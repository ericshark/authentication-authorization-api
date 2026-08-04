import Link from "next/link";
import {
  ArrowRight,
  BookOpenText,
  Braces,
  Check,
  ChevronRight,
  CircleDot,
  Code2,
  Command,
  Database,
  ExternalLink,
  FileCode2,
  Fingerprint,
  Github,
  KeyRound,
  Layers3,
  LockKeyhole,
  Network,
  RefreshCw,
  Rocket,
  ServerCog,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  Workflow,
  Zap,
} from "lucide-react";

const guideCards = [
  { href: "/docs/quickstart", icon: Rocket, number: "01", title: "Quickstart", text: "Configure infrastructure, apply migrations, start both applications, and create your first session." },
  { href: "/docs/architecture", icon: Network, number: "02", title: "Architecture", text: "Understand the browser trust boundary, dependency chain, auth backend interface, and data ownership." },
  { href: "/docs/authentication", icon: KeyRound, number: "03", title: "Authentication", text: "Trace registration, Argon2 password login, OAuth linking, magic links, and two-factor challenges." },
  { href: "/docs/sessions", icon: RefreshCw, number: "04", title: "Sessions & tokens", text: "Compare JWT and server-session mode, refresh rotation, token families, cookies, and revocation." },
  { href: "/docs/security", icon: ShieldCheck, number: "05", title: "Security & recovery", text: "Learn lockout policy, encrypted TOTP, hashed recovery codes, reset tokens, and hardening steps." },
  { href: "/docs/operations", icon: ServerCog, number: "06", title: "Operations", text: "Run health probes, workers, role policy, deployment controls, tests, and future extensions." },
];

export function DocsHome() {
  return (
    <div className="docs-home">
      <section className="docs-hero">
        <div className="docs-hero-grid" aria-hidden="true" />
        <div className="docs-hero-glow" aria-hidden="true" />
        <div className="docs-hero-copy">
          <div className="docs-hero-badge"><span><Github size={14} /></span> Self-hosted authentication reference</div>
          <h1>Authentication you can <em>read</em> before you trust.</h1>
          <p>A complete FastAPI and Next.js platform that explains how passwords, cookies, JWTs, server sessions, OAuth, Redis, TOTP, email recovery, and role policy work together.</p>
          <div className="docs-hero-actions">
            <Link className="button button-primary" href="/docs/quickstart"><Rocket size={17} /> Start the quickstart <ArrowRight size={16} /></Link>
            <Link className="button button-ghost" href="/playground"><Command size={17} /> Explore 39 routes</Link>
          </div>
          <div className="docs-principles">
            <span><Check size={13} /> Own your identity data</span>
            <span><Check size={13} /> Swap JWT or sessions</span>
            <span><Check size={13} /> Inspect every request</span>
          </div>
        </div>

        <div className="docs-hero-code">
          <div className="hero-code-window">
            <div className="hero-code-head"><span><i /><i /><i /></span><code>POST /auth/login</code><b>200 OK</b></div>
            <div className="hero-code-body">
              <div className="code-line"><span>1</span><code><em>username</em>=ada&amp;<em>password</em>=••••••••</code></div>
              <div className="code-divider"><span>HTTP request enters FastAPI</span></div>
              <ExecutionLine icon={Braces} label="Pydantic" text="Parse form fields" state="done" />
              <ExecutionLine icon={Database} label="SQLAlchemy" text="Load active user" state="done" />
              <ExecutionLine icon={LockKeyhole} label="Argon2" text="Verify password hash" state="done" />
              <ExecutionLine icon={Fingerprint} label="TOTP policy" text="Check second factor" state="skip" />
              <ExecutionLine icon={ShieldCheck} label="JWT backend" text="Set HTTP-only cookies" state="done" />
              <div className="code-response"><span>set-cookie</span><code>access_token=&lt;http-only&gt;</code></div>
            </div>
          </div>
          <div className="hero-code-caption"><Zap size={14} /><span><strong>Nothing is mocked.</strong> The workbench sends this request to the running API.</span></div>
        </div>
      </section>

      <section className="docs-intro-strip">
        <div><span><BookOpenText size={18} /></span><strong>Documentation-first</strong><p>Concepts are tied directly to routes and models.</p></div>
        <div><span><Code2 size={18} /></span><strong>Implementation-first</strong><p>Every guide describes code that actually runs.</p></div>
        <div><span><Workflow size={18} /></span><strong>Strategy-neutral</strong><p>JWT and sessions share one backend contract.</p></div>
        <div><span><ShieldCheck size={18} /></span><strong>Security-explicit</strong><p>Trust boundaries and limitations stay visible.</p></div>
      </section>

      <section className="docs-home-section">
        <div className="docs-section-heading">
          <div><span className="eyebrow">Guided learning path</span><h2>From first request to production deployment.</h2><p>Read in order for a complete mental model, or jump directly to the part of the stack you are implementing.</p></div>
          <span className="docs-count">6 implementation guides</span>
        </div>
        <div className="guide-card-grid">
          {guideCards.map((guide) => <GuideCard guide={guide} key={guide.href} />)}
        </div>
      </section>

      <section className="docs-home-section">
        <div className="docs-section-heading">
          <div><span className="eyebrow">Request architecture</span><h2>One boundary, five cooperating systems.</h2><p>The API owns identity policy. Each supporting service has a narrow responsibility and an explicit failure mode.</p></div>
          <Link href="/docs/architecture">Read architecture guide <ArrowRight size={15} /></Link>
        </div>
        <div className="system-diagram">
          <SystemNode icon={FileCode2} overline="Untrusted client" title="Next.js" details={["Credentialed fetch", "HTTP-only cookies", "Interactive docs"]} accent="blue" />
          <SystemConnector label="HTTPS / JSON" />
          <SystemNode icon={ServerCog} overline="Policy boundary" title="FastAPI" details={["Pydantic validation", "Auth dependencies", "Role authorization"]} accent="lime" primary />
          <SystemConnector label="State adapters" />
          <div className="system-data-nodes">
            <SystemNode icon={Database} overline="Durable state" title="PostgreSQL" details={["Users & roles", "Tokens & sessions"]} accent="purple" />
            <SystemNode icon={Layers3} overline="Ephemeral state" title="Redis" details={["Lockouts & tokens", "Cache & activity"]} accent="orange" />
          </div>
        </div>
      </section>

      <section className="docs-home-split">
        <div className="source-map-card">
          <div className="docs-card-head"><div><span className="eyebrow">Repository map</span><h3>Where each concern lives</h3></div><Github size={21} /></div>
          <div className="source-tree">
            <TreeRow depth={0} type="folder" name="backend/app" note="FastAPI application" />
            <TreeRow depth={1} type="folder" name="routes" note="HTTP policy and handlers" />
            <TreeRow depth={1} type="folder" name="backends" note="JWT / session implementations" />
            <TreeRow depth={1} type="folder" name="auth" note="Cookies, tokens, TOTP, lockout" />
            <TreeRow depth={1} type="folder" name="services" note="Email and activity boundaries" />
            <TreeRow depth={1} type="file" name="models.py" note="Durable identity schema" />
            <TreeRow depth={0} type="folder" name="frontend" note="Next.js docs and client" />
            <TreeRow depth={1} type="folder" name="app/docs" note="Implementation guides" />
            <TreeRow depth={1} type="file" name="route-catalog.js" note="39 executable route definitions" />
          </div>
        </div>

        <div className="choose-strategy-card">
          <div className="docs-card-head"><div><span className="eyebrow">Core abstraction</span><h3>Choose the credential strategy</h3></div><RefreshCw size={21} /></div>
          <p>Routes call one AuthBackend interface. Configuration selects the implementation without rewriting your account logic.</p>
          <div className="strategy-option">
            <span className="strategy-icon"><KeyRound size={18} /></span>
            <div><strong>JWT + refresh rotation</strong><p>Signed short-lived access with hashed, single-use refresh-token families.</p></div>
            <code>AUTH_STRATEGY=JWT</code>
          </div>
          <div className="strategy-option">
            <span className="strategy-icon"><Database size={18} /></span>
            <div><strong>Server-side sessions</strong><p>Opaque browser ids backed by Redis cache and durable session records.</p></div>
            <code>AUTH_STRATEGY=SESSION</code>
          </div>
          <Link href="/docs/sessions">Compare both strategies <ArrowRight size={14} /></Link>
        </div>
      </section>

      <section className="docs-workbench-cta">
        <div className="workbench-cta-icon"><TerminalSquare size={26} /></div>
        <div><span className="eyebrow">Interactive reference</span><h2>Read the explanation. Send the request. Inspect the result.</h2><p>The route workbench documents all 39 endpoints with editable fields, exact HTTP transport, parsed responses, timing, history, and a server-side execution trace.</p></div>
        <Link className="button button-primary" href="/playground">Open API workbench <ArrowRight size={16} /></Link>
      </section>
    </div>
  );
}

function ExecutionLine({ icon: Icon, label, text, state }) {
  return <div className="execution-code-line"><span className={`execution-code-icon execution-${state}`}><Icon size={14} /></span><div><strong>{label}</strong><small>{text}</small></div><b>{state === "done" ? "✓" : "—"}</b></div>;
}

function GuideCard({ guide }) {
  const Icon = guide.icon;
  return <Link className="guide-card" href={guide.href}><div className="guide-card-top"><span>{guide.number}</span><i><Icon size={19} /></i></div><h3>{guide.title}</h3><p>{guide.text}</p><span className="guide-link">Read guide <ChevronRight size={14} /></span></Link>;
}

function SystemNode({ icon: Icon, overline, title, details, accent, primary = false }) {
  return <div className={`system-node system-${accent} ${primary ? "system-primary" : ""}`}><div className="system-node-head"><span><Icon size={20} /></span><div><small>{overline}</small><strong>{title}</strong></div>{primary && <b>AUTHORITY</b>}</div><ul>{details.map((detail) => <li key={detail}><CircleDot size={10} />{detail}</li>)}</ul></div>;
}

function SystemConnector({ label }) {
  return <div className="system-connector"><span /><code>{label}</code><ArrowRight size={16} /></div>;
}

function TreeRow({ depth, type, name, note }) {
  return <div className="tree-row" style={{ "--tree-depth": depth }}><span>{type === "folder" ? "▾" : "·"}</span><code>{name}</code><p>{note}</p></div>;
}
