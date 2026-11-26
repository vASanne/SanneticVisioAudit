"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AuditSummary, ClientRow, createAudit, listAudits, listClients } from "@/lib/api";
import { scoreBand, statusLabel } from "@/lib/labels";

export function HomeScreen() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [clientName, setClientName] = useState("Intern");
  const [clientId, setClientId] = useState("");
  const [maxPages, setMaxPages] = useState(25);
  const [followLinks, setFollowLinks] = useState(true);
  const [renderJs, setRenderJs] = useState(false);
  const [probeLinks, setProbeLinks] = useState(true);
  const [llmSummary, setLlmSummary] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [audits, setAudits] = useState<AuditSummary[]>([]);
  const [clients, setClients] = useState<ClientRow[]>([]);
  const [listError, setListError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([listAudits(), listClients().catch(() => [] as ClientRow[])])
      .then(([rows, clientRows]) => {
        if (!active) return;
        setAudits(rows);
        setClients(clientRows);
      })
      .catch((reason: unknown) => {
        if (active) setListError(reason instanceof Error ? reason.message : "Audits konnten nicht geladen werden.");
      });
    return () => {
      active = false;
    };
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      const audit = await createAudit({
        url,
        client_name: clientName,
        client_id: clientId || null,
        max_pages: maxPages,
        follow_links: followLinks,
        render_js: renderJs,
        probe_internal_links: probeLinks,
        llm_summary: llmSummary,
      });
      router.push(`/audits/${audit.id}`);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Das Audit konnte nicht gestartet werden.");
      setPending(false);
    }
  }

  return (
    <main>
      <section className="container section-sm">
        <h1 className="mb-4">SEO und GEO in einem Befund.</h1>
        <p>Eine URL prüfen, priorisierte Hinweise lesen und einen kundenfähigen Bericht öffnen.</p>

        <form onSubmit={onSubmit} className="card mt-8">
          <div className="form-group">
            <label htmlFor="url">Start-URL</label>
            <input
              id="url"
              required
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://kunde.example"
            />
          </div>
          <div className="grid grid-2">
            <div className="form-group">
              <label htmlFor="client">Kunde</label>
              <input id="client" value={clientName} onChange={(event) => setClientName(event.target.value)} />
            </div>
            <div className="form-group">
              <label htmlFor="pages">Seiten</label>
              <input
                id="pages"
                type="number"
                min={1}
                max={500}
                value={maxPages}
                onChange={(event) => setMaxPages(Number(event.target.value))}
              />
            </div>
          </div>
          {clients.length > 0 ? (
            <div className="form-group">
              <label htmlFor="client-id">Mandant</label>
              <select
                id="client-id"
                value={clientId}
                onChange={(event) => {
                  setClientId(event.target.value);
                  const match = clients.find((item) => item.id === event.target.value);
                  if (match) setClientName(match.name);
                }}
              >
                <option value="">Neu über Kundenname</option>
                {clients.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </div>
          ) : null}
          <div className="form-group flex gap-2 form-check-row">
            <input id="follow" type="checkbox" checked={followLinks} onChange={(event) => setFollowLinks(event.target.checked)} />
            <label htmlFor="follow" className="check-label">
              Interne Links folgen
            </label>
          </div>
          <div className="form-group flex gap-2 form-check-row-start">
            <input id="render-js" type="checkbox" checked={renderJs} onChange={(event) => setRenderJs(event.target.checked)} />
            <label htmlFor="render-js" className="check-label">
              JavaScript rendern
              <span className="text-muted check-hint">
                Nur für Seiten, deren Roh-HTML kaum Text enthält.
              </span>
            </label>
          </div>
          <div className="form-group flex gap-2 form-check-row">
            <input id="probe-links" type="checkbox" checked={probeLinks} onChange={(event) => setProbeLinks(event.target.checked)} />
            <label htmlFor="probe-links" className="check-label">
              Unbesuchte interne Links prüfen
            </label>
          </div>
          <div className="form-group flex gap-2 form-check-row-start">
            <input id="llm-summary" type="checkbox" checked={llmSummary} onChange={(event) => setLlmSummary(event.target.checked)} />
            <label htmlFor="llm-summary" className="check-label">
              Inhaltliche Einschätzung (LLM)
            </label>
          </div>
          {error ? (
            <p className="form-error">
              <span className="pill pill-critical">Fehler</span> {error}
            </p>
          ) : null}
          <button type="submit" className="btn btn-gradient" disabled={pending}>
            {pending ? "Wird angelegt …" : "Audit starten"}
          </button>
        </form>
      </section>

      <section className="container section-sm">
        <h2>Letzte Audits</h2>
        {listError ? (
          <p className="form-error">
            <span className="pill pill-critical">Fehler</span> {listError}
          </p>
        ) : null}
        {!listError && audits.length === 0 ? <p className="text-muted">Noch keine Audits.</p> : null}
        {audits.length > 0 ? (
          <div className="table-responsive">
            <table className="table table-hover">
              <thead>
                <tr>
                  <th>Kunde</th>
                  <th>URL</th>
                  <th>Status</th>
                  <th>Gesamt</th>
                </tr>
              </thead>
              <tbody>
                {audits.map((audit) => {
                  const band = scoreBand(audit.overall_score);
                  return (
                    <tr key={audit.id}>
                      <td>
                        <a href={`/audits/${audit.id}`}>{audit.client_name}</a>
                      </td>
                      <td className="break-url">{audit.url}</td>
                      <td>{statusLabel[audit.status]}</td>
                      <td>
                        {audit.overall_score ?? "–"} <span className="text-sm">{band.label}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </main>
  );
}
