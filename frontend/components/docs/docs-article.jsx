import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock3,
  Code2,
  ExternalLink,
  FileText,
  Github,
  Info,
  ListTree,
} from "lucide-react";
import { getAdjacentDocs } from "@/lib/docs";

const noteIcons = {
  info: Info,
  warning: AlertTriangle,
  success: CheckCircle2,
};

export function DocsArticle({ doc, slug }) {
  const adjacent = getAdjacentDocs(slug);

  return (
    <div className="docs-page">
      <div className="docs-breadcrumb">
        <Link href="/">Documentation</Link>
        <span>/</span>
        <span>{doc.title}</span>
      </div>

      <div className="docs-layout">
        <article className="docs-article">
          <header className="docs-article-header">
            <span className="docs-category">{doc.eyebrow}</span>
            <h1>{doc.title}</h1>
            <p>{doc.description}</p>
            <div className="docs-meta">
              <span><Clock3 size={14} /> {doc.readingTime} read</span>
              <span><FileText size={14} /> Implementation guide</span>
              <span><Github size={14} /> Open source reference</span>
            </div>
          </header>

          <div className="docs-open-source-callout">
            <span><Code2 size={20} /></span>
            <div>
              <strong>Read the guide, then inspect the running implementation.</strong>
              <p>Every concept maps to a real FastAPI route, SQLAlchemy model, Redis key, or browser request in this repository.</p>
            </div>
            <Link href="/playground">Open workbench <ArrowRight size={15} /></Link>
          </div>

          {doc.sections.map((section) => (
            <DocsSection section={section} key={section.id} />
          ))}

          <nav className="docs-pagination" aria-label="Documentation pagination">
            {adjacent.previous ? (
              <Link href={`/docs/${adjacent.previous.slug}`}>
                <ArrowLeft size={17} />
                <span><small>Previous</small><strong>{adjacent.previous.title}</strong></span>
              </Link>
            ) : <span />}
            {adjacent.next ? (
              <Link className="docs-pagination-next" href={`/docs/${adjacent.next.slug}`}>
                <span><small>Next</small><strong>{adjacent.next.title}</strong></span>
                <ArrowRight size={17} />
              </Link>
            ) : <span />}
          </nav>
        </article>

        <aside className="docs-toc">
          <div className="docs-toc-title"><ListTree size={15} /> On this page</div>
          <nav>
            {doc.sections.map((section, index) => (
              <a href={`#${section.id}`} key={section.id}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                {section.title}
              </a>
            ))}
          </nav>
          <div className="docs-toc-help">
            <strong>Need the raw schema?</strong>
            <p>FastAPI publishes the generated OpenAPI document and interactive Swagger interface.</p>
            <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">Open Swagger UI <ExternalLink size={13} /></a>
          </div>
        </aside>
      </div>
    </div>
  );
}

function DocsSection({ section }) {
  return (
    <section className="docs-section" id={section.id}>
      <h2>{section.title}</h2>
      {section.body?.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
      {section.flow && <FlowDiagram items={section.flow} />}
      {section.steps && <StepList items={section.steps} />}
      {section.bullets && <BulletList items={section.bullets} />}
      {section.table && <DocsTable table={section.table} />}
      {section.code && <CodeBlock code={section.code} />}
      {section.note && <Note note={section.note} />}
    </section>
  );
}

function FlowDiagram({ items }) {
  return (
    <div className="docs-flow">
      {items.map((item, index) => (
        <div className="docs-flow-item" key={item.label}>
          <div><span>{String(index + 1).padStart(2, "0")}</span><strong>{item.label}</strong><small>{item.detail}</small></div>
          {index < items.length - 1 && <ArrowRight size={16} />}
        </div>
      ))}
    </div>
  );
}

function StepList({ items }) {
  return (
    <div className="docs-steps">
      {items.map((item, index) => (
        <div className="docs-step" key={item.title}>
          <span>{String(index + 1).padStart(2, "0")}</span>
          <div><strong>{item.title}</strong><p>{item.text}</p></div>
        </div>
      ))}
    </div>
  );
}

function BulletList({ items }) {
  return <ul className="docs-bullets">{items.map((item) => <li key={item}><span><Check size={13} /></span>{item}</li>)}</ul>;
}

function DocsTable({ table }) {
  return (
    <div className="docs-table-wrap">
      <table className="docs-table">
        <thead><tr>{table.headers.map((header) => <th key={header}>{header}</th>)}</tr></thead>
        <tbody>{table.rows.map((row) => <tr key={row.join("")}>{row.map((cell, index) => <td key={`${cell}-${index}`}>{cell}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

function CodeBlock({ code }) {
  return (
    <div className="docs-code">
      <div><span>{code.label}</span><small>{code.language}</small></div>
      <pre><code>{code.content}</code></pre>
    </div>
  );
}

function Note({ note }) {
  const Icon = noteIcons[note.tone] || Info;
  return (
    <div className={`docs-note docs-note-${note.tone || "info"}`}>
      <span><Icon size={18} /></span>
      <div><strong>{note.title}</strong><p>{note.text}</p>{note.href && <Link href={note.href}>{note.linkLabel} <ArrowRight size={13} /></Link>}</div>
    </div>
  );
}
