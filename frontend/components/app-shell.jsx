"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Activity,
  BookOpenText,
  ChevronRight,
  CircleUserRound,
  Command,
  FileCode2,
  Github,
  KeyRound,
  Menu,
  Network,
  PanelLeftClose,
  RefreshCw,
  Rocket,
  ServerCog,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { useAuth } from "@/app/providers";
import { BrandMark } from "./brand-mark";

const navigationSections = [
  {
    label: "Start here",
    items: [
      { href: "/", label: "Platform overview", icon: BookOpenText },
      { href: "/docs/quickstart", label: "Quickstart", icon: Rocket },
      { href: "/docs/architecture", label: "Architecture", icon: Network },
    ],
  },
  {
    label: "Core concepts",
    items: [
      { href: "/docs/authentication", label: "Authentication", icon: KeyRound },
      { href: "/docs/sessions", label: "Sessions & tokens", icon: RefreshCw },
      { href: "/docs/security", label: "Security & recovery", icon: ShieldCheck },
      { href: "/docs/operations", label: "Operations", icon: ServerCog },
    ],
  },
  {
    label: "Reference",
    items: [
      { href: "/playground", label: "API workbench", icon: Command },
    ],
  },
  {
    label: "Live demo",
    items: [
      { href: "/account", label: "Account console", icon: CircleUserRound },
      { href: "/security", label: "Security console", icon: FileCode2 },
    ],
  },
];

const navigation = navigationSections.flatMap((section) => section.items);

export function AppShell({ children }) {
  const pathname = usePathname();
  const { user, authLoading } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const current = navigation.find((item) => item.href === pathname) || navigation[0];
  const CurrentIcon = current.icon;

  return (
    <div className={`shell ${collapsed ? "shell-collapsed" : ""}`}>
      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-head">
          <BrandMark compact={collapsed} />
          <button className="icon-button desktop-collapse" onClick={() => setCollapsed(!collapsed)} aria-label="Toggle sidebar">
            <PanelLeftClose size={18} />
          </button>
          <button className="icon-button mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
            <X size={19} />
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navigationSections.map((section) => (
            <div className="nav-section" key={section.label}>
              <p className="nav-label">{section.label}</p>
              {section.items.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link className={`nav-item ${active ? "nav-item-active" : ""}`} href={item.href} key={item.href} onClick={() => setMobileOpen(false)} title={collapsed ? item.label : undefined}>
                    <Icon size={18} strokeWidth={active ? 2.4 : 1.8} />
                    <span>{item.label}</span>
                    {!collapsed && active && <ChevronRight size={15} />}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {!collapsed && (
          <div className="sidebar-insight">
            <span className="insight-icon"><Sparkles size={16} /></span>
            <p>Learn the architecture, then send the real request from the same documentation.</p>
            <Link href="/docs/quickstart">Start building <ChevronRight size={14} /></Link>
          </div>
        )}

        <div className="sidebar-footer">
          <div className="api-status"><span /><span className="footer-label">API target</span></div>
          {!collapsed && <code>localhost:8000</code>}
        </div>
      </aside>

      {mobileOpen && <button className="sidebar-scrim" onClick={() => setMobileOpen(false)} aria-label="Close navigation overlay" />}

      <div className="shell-content">
        <header className="topbar">
          <div className="topbar-title">
            <button className="icon-button mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20} /></button>
            <CurrentIcon size={18} />
            <span>{current.label}</span>
          </div>
          <div className="topbar-actions">
            <a className="topbar-link" href="http://localhost:8000/docs" target="_blank" rel="noreferrer"><BookOpenText size={16} /> API docs</a>
            <a className="icon-button" href="https://github.com" target="_blank" rel="noreferrer" aria-label="GitHub"><Github size={18} /></a>
            <div className={`identity-chip ${user ? "identity-online" : ""}`}>
              <span className="identity-avatar">{user?.name?.[0] || user?.username?.[0] || <Activity size={15} />}</span>
              <span className="identity-copy">
                <strong>{authLoading ? "Checking session" : user?.name || user?.username || "Guest mode"}</strong>
                <small>{user ? user.role : "Not authenticated"}</small>
              </span>
            </div>
          </div>
        </header>
        <main className="page-stage">{children}</main>
      </div>
    </div>
  );
}
