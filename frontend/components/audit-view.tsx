"use client";

import { useEffect, useState } from "react";

import { AuditDetail, getAudit, openReport } from "@/lib/api";
import { scoreBand, severityBadge, severityLabel, statusLabel } from "@/lib/labels";

export function AuditView({ id }: { id: string }) {
  const [audit, setAudit] = useState<AuditDetail | null>(null);
  const [error, setError] = useState("");
  const [reportError, setReportError] = useState("");

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
    <>
      <main className="container section-sm">
        {!audit && !error ? <p>Audit wird geladen …</p> : null}
        {error ? (
          <p className="form-error">
            <span className="pill pill-critical">Fehler</span> {error}
          </p>
        ) : null}
        {audit ? (
          <AuditBody
            audit={audit}
            reportError={reportError}
            onOpenReport={async (format) => {
              setReportError("");
              try {
                await openReport(audit.id, format);
              } catch (reason: unknown) {
                setReportError(reason instanceof Error ? reason.message : "Bericht konnte nicht geladen werden.");
              }
            }}
          />
        ) : null}
      </main>
    </>
  );
}

function AuditBody({
  audit,
  reportError,
  onOpenReport,
}: {
  audit: AuditDetail;
  reportError: string;
  onOpenReport: (format: "html" | "pdf") => Promise<void>;
}) {
  const running = audit.status === "pending" || audit.status === "running";
  return (
    <>
      <p className="text-sm">{audit.client_name}</p>
      <h1>{statusLabel[audit.status]}</h1>
      <p className="break-url">
        <a href={audit.url}>{audit.url}</a>
      </p>
      {running ? <p>Seiten werden gelesen. Diese Ansicht aktualisiert sich von selbst.</p> : null}
      {audit.status === "failed" ? (
        <p className="form-error">
          <span className="pill pill-critical">Fehler</span> {audit.error_message}
        </p>
      ) : null}

      <section className="grid grid-3 mt-8">
        <Score label="Gesamt" value={audit.overall_score} />
        <Score label="SEO" value={audit.seo_score} />
        <Score label="GEO" value={audit.geo_score} />
      </section>

      {audit.status === "completed" ? (
        <p className="mt-8 flex gap-2" style={{ flexWrap: "wrap" }}>
          <button type="button" className="btn btn-primary" onClick={() => void onOpenReport("html")}>
            HTML-Bericht öffnen
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => void onOpenReport("pdf")}>
            PDF herunterladen
          </button>
        </p>
      ) : null}
      {reportError ? (
        <p className="form-error">
          <span className="pill pill-critical">Fehler</span> {reportError}
        </p>
      ) : null}

      {audit.llm_summary ? (
        <section className="card mt-8">
          <h2>Inhaltliche Einschätzung</h2>
          <p className="mb-0">{audit.llm_summary}</p>
        </section>
      ) : null}

      {audit.gsc_notes && audit.gsc_notes.length > 0 ? (
        <section className="card mt-8">
          <h2>Search Console</h2>
          {audit.gsc_notes.map((note) => (
            <p key={note}>{note}</p>
          ))}
        </section>
      ) : null}

      <h2 className="mt-8">Hinweise</h2>
      {audit.issues.length === 0 ? (
        <p className="card">
          {audit.status === "completed" ? "Keine offenen Punkte in den geprüften Checks." : "Noch keine Befunde."}
        </p>
      ) : (
        <ul className="issue-list">
          {audit.issues.map((issue) => (
            <li key={issue.id} className="card">
              <p className="flex gap-2">
                <span className={severityBadge(issue.severity)}>{severityLabel[issue.severity]}</span>
                {issue.quick_win ? <span className="pill pill-neutral">Schnell umsetzbar</span> : null}
                {issue.impact_score != null ? <span className="pill pill-neutral">Wirkung {issue.impact_score}</span> : null}
              </p>
              <h3>{issue.title}</h3>
              <p>{issue.description}</p>
              <p>
                <strong>Empfehlung. </strong>
                {issue.recommendation}
              </p>
              {issue.affected_urls.length > 0 ? (
                <ul>
                  {issue.affected_urls.slice(0, 8).map((url) => (
                    <li key={url} className="break-url">
                      <a href={url}>{url}</a>
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
          <h2 className="mt-8">Seiten</h2>
          <div className="table-responsive">
            <table className="table table-hover">
              <thead>
                <tr>
                  <th>Seite</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {audit.pages.map((page) => (
                  <tr key={page.id}>
                    <td className="break-url">{page.title || page.url}</td>
                    <td className="code">{page.status_code ?? "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </>
  );
}

function Score({ label, value }: { label: string; value: number | null }) {
  const band = scoreBand(value);
  return (
    <article className={`card ${band.className}`}>
      <p className="text-sm">{label}</p>
      <p className="score-value">{value ?? "–"}</p>
      <p className="text-sm mb-0">{band.label}</p>
    </article>
  );
}
