"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { useAuth } from "@/lib/auth";

const LINKS = [
  { href: "/", label: "Audits" },
  { href: "/clients", label: "Kunden" },
  { href: "/watchlist", label: "Beobachtung" },
  { href: "/schedules", label: "Berichte" },
  { href: "/users", label: "Nutzer", admin: true },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { status, signOut, loading } = useAuth();
  const [navOpen, setNavOpen] = useState(false);
  const hideChrome = pathname === "/login";

  useEffect(() => {
    setNavOpen(false);
  }, [pathname]);

  if (hideChrome) return <>{children}</>;

  const nav = LINKS.filter((link) => {
    if (!link.admin) return true;
    if (loading || !status) return false;
    return status.is_admin || !status.auth_required;
  });

  return (
    <div className={`app-shell${navOpen ? " is-nav-open" : ""}`}>
      <header className="app-topbar" aria-label="Kopfzeile">
        <div className="navbar">
          <button
            type="button"
            className="navbar-toggler"
            aria-expanded={navOpen}
            aria-controls="workspace-nav"
            aria-label={navOpen ? "Navigation schließen" : "Navigation öffnen"}
            onClick={() => setNavOpen((open) => !open)}
          >
            <span aria-hidden="true">{navOpen ? "×" : "☰"}</span>
          </button>
          <a className="navbar-brand" href="/" aria-label="Sannetic Vision Audit, zur Übersicht">
            <img className="brand-lockup" src="/brand/lockup.svg" alt="Sannetic. Software. Intelligence." />
          </a>
          <div className="topbar-actions">
            {status?.authenticated ? <span className="navbar-text">{status.user_name}</span> : null}
            {status?.authenticated ? (
              <button type="button" className="btn btn-secondary btn-sm" onClick={signOut}>
                Abmelden
              </button>
            ) : (
              <a className="btn btn-secondary btn-sm" href="/login">
                Anmelden
              </a>
            )}
          </div>
        </div>
      </header>

      <aside className="app-sidebar" aria-label="Hauptnavigation" id="workspace-nav">
        <nav className="sidebar-nav">
          <p className="sidebar-heading">Workspace</p>
          {nav.map((link) => {
            const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <a
                key={link.href}
                href={link.href}
                className={`sidebar-link${active ? " active" : ""}`}
                aria-current={active ? "page" : undefined}
              >
                <span className="label">{link.label}</span>
              </a>
            );
          })}
        </nav>
      </aside>

      <div className="app-content">
        {loading && !status ? <p className="empty-text">Sitzung wird geprüft …</p> : children}
      </div>
    </div>
  );
}
