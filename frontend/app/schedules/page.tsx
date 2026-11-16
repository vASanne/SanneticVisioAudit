"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  ClientRow,
  ScheduleRow,
  createSchedule,
  deleteSchedule,
  listClients,
  listSchedules,
  updateSchedule,
} from "@/lib/api";

export default function SchedulesPage() {
  const [rows, setRows] = useState<ScheduleRow[]>([]);
  const [clients, setClients] = useState<ClientRow[]>([]);
  const [error, setError] = useState("");
  const [clientId, setClientId] = useState("");
  const [url, setUrl] = useState("");
  const [cron, setCron] = useState("0 6 * * *");
  const [maxPages, setMaxPages] = useState(25);
  const [followLinks, setFollowLinks] = useState(true);
  const [probeLinks, setProbeLinks] = useState(true);
  const [renderJs, setRenderJs] = useState(false);
  const [llmSummary, setLlmSummary] = useState(false);

  async function reload() {
    const [scheduleRows, clientRows] = await Promise.all([listSchedules(), listClients()]);
    setRows(scheduleRows);
    setClients(clientRows);
    if (!clientId && clientRows[0]) setClientId(clientRows[0].id);
  }

  useEffect(() => {
    reload().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Zeitpläne konnten nicht geladen werden."));
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await createSchedule({
        client_id: clientId,
        url,
        cron,
        enabled: true,
        config: {
          max_pages: maxPages,
          follow_links: followLinks,
          probe_internal_links: probeLinks,
          render_js: renderJs,
          llm_summary: llmSummary,
        },
      });
      setUrl("");
      await reload();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Zeitplan konnte nicht angelegt werden.");
    }
  }

  return (
    <main className="container section-sm">
      <h1>Regelmäßige Berichte</h1>
      <p>Konfiguration für wiederkehrende Audits und Berichtserneuerungen je Kundenseite.</p>

      <form onSubmit={onCreate} className="card mt-8">
        <div className="grid grid-2">
          <div className="form-group">
            <label htmlFor="sc-client">Kunde</label>
            <select id="sc-client" required value={clientId} onChange={(event) => setClientId(event.target.value)}>
              <option value="" disabled>
                Kunde wählen
              </option>
              {clients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="sc-cron">Cron (UTC)</label>
            <input id="sc-cron" required value={cron} onChange={(event) => setCron(event.target.value)} />
          </div>
        </div>
        <div className="form-group">
          <label htmlFor="sc-url">URL</label>
          <input id="sc-url" required value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://kunde.example/" />
        </div>
        <div className="form-group">
          <label htmlFor="sc-pages">Seiten</label>
          <input
            id="sc-pages"
            type="number"
            min={1}
            max={500}
            value={maxPages}
            onChange={(event) => setMaxPages(Number(event.target.value))}
          />
        </div>
        <div className="form-group flex gap-2" style={{ alignItems: "center" }}>
          <input id="sc-follow" type="checkbox" checked={followLinks} onChange={(event) => setFollowLinks(event.target.checked)} />
          <label htmlFor="sc-follow" className="check-label">
            Interne Links folgen
          </label>
        </div>
        <div className="form-group flex gap-2" style={{ alignItems: "center" }}>
          <input id="sc-probe" type="checkbox" checked={probeLinks} onChange={(event) => setProbeLinks(event.target.checked)} />
          <label htmlFor="sc-probe" className="check-label">
            Unbesuchte Links prüfen
          </label>
        </div>
        <div className="form-group flex gap-2" style={{ alignItems: "center" }}>
          <input id="sc-js" type="checkbox" checked={renderJs} onChange={(event) => setRenderJs(event.target.checked)} />
          <label htmlFor="sc-js" className="check-label">
            JavaScript rendern
          </label>
        </div>
        <div className="form-group flex gap-2" style={{ alignItems: "center" }}>
          <input id="sc-llm" type="checkbox" checked={llmSummary} onChange={(event) => setLlmSummary(event.target.checked)} />
          <label htmlFor="sc-llm" className="check-label">
            LLM-Einschätzung
          </label>
        </div>
        <button type="submit" className="btn btn-gradient" disabled={!clientId}>
          Zeitplan speichern
        </button>
      </form>

      {error ? (
        <p className="form-error mt-8">
          <span className="pill pill-critical">Fehler</span> {error}
        </p>
      ) : null}

      <div className="table-responsive mt-8">
        <table className="table table-hover">
          <thead>
            <tr>
              <th>Kunde</th>
              <th>URL</th>
              <th>Zeitplan</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.client_name}</td>
                <td className="break-url">{row.url}</td>
                <td>
                  {row.cron}
                  <div className="text-sm text-muted">
                    nächster Lauf {row.next_run_at ? new Date(row.next_run_at).toLocaleString("de-DE") : "–"}
                  </div>
                </td>
                <td>{row.enabled ? "aktiv" : "pausiert"}</td>
                <td>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() =>
                      void updateSchedule(row.id, { enabled: !row.enabled })
                        .then(reload)
                        .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Update fehlgeschlagen."))
                    }
                  >
                    {row.enabled ? "Pausieren" : "Aktivieren"}
                  </button>{" "}
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() =>
                      void deleteSchedule(row.id)
                        .then(reload)
                        .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Löschen fehlgeschlagen."))
                    }
                  >
                    Löschen
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
