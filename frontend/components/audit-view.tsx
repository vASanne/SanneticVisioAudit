"use client";

import { useEffect, useState } from "react";

import { AuditDetail, apiBase, getAudit } from "@/lib/api";
import { scoreTone, severityLabel, statusLabel } from "@/lib/labels";

export function AuditView({ id }: { id: string }) {
  const [audit, setAudit] = useState<AuditDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let timer = 0;
    const tick = async () => {
      try {
        const next = await getAudit(id);
        if (!active) return;
        setAudit(next);
        setError("");
        if (next.status === "pending" || next.status === "running") {
          timer = window.setTimeout(() => void tick(), 2000);
        }
      } catch (reason: unknown) {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : "Audit konnte nicht geladen werden.");
        timer = window.setTimeout(() => void tick(), 4000);
      }
    };
    void tick();
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [id]);

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <a href="/" className="text-sm uppercase tracking-[0.14em]">
        Zur Übersicht
      </a>
      {!audit && !error ? <p className="mt-8">Audit wird geladen …</p> : null}
      {error ? <p className="mt-8 text-[#8e1b2a]">{error}</p> : null}
      {audit ? <AuditBody audit={audit} /> : null}
    </main>
  );
}

function AuditBody({ audit }: { audit: AuditDetail }) {
  const running = audit.status === "pending" || audit.status === "running";
  return (
    <>
      <p className="mt-6 text-xs uppercase tracking-[0.18em]">{audit.client_name}</p>
      <h1 className="mt-2 font-serif text-4xl font-medium">{statusLabel[audit.status]}</h1>
      <p className="mt-2 break-all text-ink/70">{audit.url}</p>
      {running ? <p className="mt-6">Seiten werden gelesen. Diese Ansicht aktualisiert sich von selbst.</p> : null}
      {audit.status === "failed" ? <p className="mt-6 text-[#8e1b2a]">{audit.error_message}</p> : null}

      <section className="mt-8 grid gap-3 sm:grid-cols-3">
        <Score label="Gesamt" value={audit.overall_score} />
        <Score label="SEO" value={audit.seo_score} />
        <Score label="GEO" value={audit.geo_score} />
      </section>

      {audit.status === "completed" ? (
        <a
          className="mt-6 inline-block bg-ink px-4 py-2 text-paper"
          href={`${apiBase()}/api/v1/audits/${audit.id}/report`}
          target="_blank"
          rel="noreferrer"
        >
          HTML-Bericht öffnen
        </a>
      ) : null}

      <h2 className="mt-10 font-serif text-2xl">Hinweise</h2>
      {audit.issues.length === 0 ? (
        <p className="mt-3 bg-moss px-4 py-3">
          {audit.status === "completed" ? "Keine offenen Punkte in den geprüften Checks." : "Noch keine Befunde."}
        </p>
      ) : (
        <ul className="mt-4 space-y-3">
          {audit.issues.map((issue) => (
            <li key={issue.id} className="border border-line border-l-4 border-l-ember bg-card px-4 py-3">
              <p className="text-xs uppercase tracking-[0.08em]">
                {severityLabel[issue.severity]}
                {issue.quick_win ? " · Schnell umsetzbar" : ""}
              </p>
              <h3 className="mt-1 text-lg">{issue.title}</h3>
              <p className="mt-1">{issue.description}</p>
              <p className="mt-2">
                <span className="font-medium">Empfehlung. </span>
                {issue.recommendation}
              </p>
              {issue.affected_urls.length > 0 ? (
                <ul className="mt-2 list-disc pl-5 text-sm text-ink/80">
                  {issue.affected_urls.slice(0, 8).map((url) => (
                    <li key={url} className="break-all">
                      {url}
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {audit.pages.length > 0 ? (
        <>
          <h2 className="mt-10 font-serif text-2xl">Seiten</h2>
          <ul className="mt-3 divide-y divide-line border-y border-line">
            {audit.pages.map((page) => (
              <li key={page.id} className="flex items-baseline justify-between gap-4 py-2 text-sm">
                <span className="break-all">{page.title || page.url}</span>
                <span>{page.status_code ?? "–"}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </>
  );
}

function Score({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="border border-line bg-card px-4 py-3">
      <p className="text-xs uppercase tracking-[0.08em] text-ink/60">{label}</p>
      <p className={`font-serif text-4xl ${scoreTone(value)}`}>{value ?? "–"}</p>
    </div>
  );
}
