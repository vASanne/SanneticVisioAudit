"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  ClientRow,
  WatchlistRow,
  createAudit,
  createWatchlistItem,
  deleteWatchlistItem,
  listClients,
  listWatchlist,
  updateWatchlistItem,
} from "@/lib/api";
import { scoreBand } from "@/lib/labels";

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistRow[]>([]);
  const [clients, setClients] = useState<ClientRow[]>([]);
  const [error, setError] = useState("");
  const [clientId, setClientId] = useState("");
  const [url, setUrl] = useState("");
  const [label, setLabel] = useState("");
  const [notes, setNotes] = useState("");
  const [renew, setRenew] = useState(true);
  const [cron, setCron] = useState("0 6 * * *");
  const [maxPages, setMaxPages] = useState(25);

  async function reload() {
    const [rows, clientRows] = await Promise.all([listWatchlist(), listClients()]);
    setItems(rows);
    setClients(clientRows);
    if (!clientId && clientRows[0]) setClientId(clientRows[0].id);
  }

  useEffect(() => {
    reload().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Liste konnte nicht geladen werden."));
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await createWatchlistItem({
        client_id: clientId,
        url,
        label,
        notes,
        renew_enabled: renew,
        cron,
        config: { max_pages: maxPages, follow_links: true, probe_internal_links: true },
      });
      setUrl("");
      setLabel("");
      setNotes("");
      await reload();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Eintrag konnte nicht angelegt werden.");
    }
  }

  return (
    <main className="container section-sm">
      <h1>Beobachtungsliste</h1>
      <p>Kundenseiten im Blick behalten und bei Bedarf regelmäßig neu prüfen lassen.</p>

      <form onSubmit={onCreate} className="card mt-8">
        <div className="grid grid-2">
          <div className="form-group">
            <label htmlFor="wl-client">Kunde</label>
            <select id="wl-client" required value={clientId} onChange={(event) => setClientId(event.target.value)}>
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
            <label htmlFor="wl-label">Bezeichnung</label>
            <input id="wl-label" value={label} onChange={(event) => setLabel(event.target.value)} placeholder="Startseite" />
          </div>
        </div>
        <div className="form-group">
          <label htmlFor="wl-url">URL</label>
          <input id="wl-url" required value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://kunde.example/" />
        </div>
        <div className="form-group">
          <label htmlFor="wl-notes">Notiz</label>
          <textarea id="wl-notes" rows={2} value={notes} onChange={(event) => setNotes(event.target.value)} />
        </div>
        <div className="form-group flex gap-2 form-check-row">
          <input id="wl-renew" type="checkbox" checked={renew} onChange={(event) => setRenew(event.target.checked)} />
          <label htmlFor="wl-renew" className="check-label">
            Regelmäßige Berichterneuerung
          </label>
        </div>
        {renew ? (
          <div className="grid grid-2">
            <div className="form-group">
              <label htmlFor="wl-cron">Cron (UTC)</label>
              <input id="wl-cron" value={cron} onChange={(event) => setCron(event.target.value)} />
            </div>
            <div className="form-group">
              <label htmlFor="wl-pages">Seiten je Lauf</label>
              <input
                id="wl-pages"
                type="number"
                min={1}
                max={500}
                value={maxPages}
                onChange={(event) => setMaxPages(Number(event.target.value))}
              />
            </div>
          </div>
        ) : null}
        <button type="submit" className="btn btn-gradient" disabled={!clientId}>
          Zur Beobachtung hinzufügen
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
              <th>Score</th>
              <th>Erneuerung</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const band = scoreBand(item.last_overall_score);
              return (
                <tr key={item.id}>
                  <td>
                    {item.client_name}
                    {item.label ? <span className="text-muted"> · {item.label}</span> : null}
                  </td>
                  <td className="break-url">{item.url}</td>
                  <td>
                    {item.last_overall_score ?? "–"} <span className="text-sm">{band.label}</span>
                    {item.last_audit_id ? (
                      <>
                        {" "}
                        <a href={`/audits/${item.last_audit_id}`}>Bericht</a>
                      </>
                    ) : null}
                  </td>
                  <td>
                    {item.renew_enabled ? (
                      <>
                        {item.cron}
                        <div className="text-sm text-muted">
                          nächster Lauf {item.next_run_at ? new Date(item.next_run_at).toLocaleString("de-DE") : "–"}
                        </div>
                      </>
                    ) : (
                      "aus"
                    )}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() =>
                        void createAudit({
                          url: item.url,
                          client_id: item.client_id,
                          client_name: item.client_name,
                          max_pages: Number(item.config.max_pages || 25),
                          follow_links: true,
                          render_js: false,
                          probe_internal_links: true,
                          llm_summary: false,
                        })
                          .then((audit) => {
                            window.location.href = `/audits/${audit.id}`;
                          })
                          .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Audit fehlgeschlagen."))
                      }
                    >
                      Jetzt prüfen
                    </button>{" "}
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() =>
                        void updateWatchlistItem(item.id, { renew_enabled: !item.renew_enabled, cron: item.cron || "0 6 * * *" })
                          .then(reload)
                          .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Update fehlgeschlagen."))
                      }
                    >
                      {item.renew_enabled ? "Pause" : "Erneuern"}
                    </button>{" "}
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() =>
                        void deleteWatchlistItem(item.id)
                          .then(reload)
                          .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Löschen fehlgeschlagen."))
                      }
                    >
                      Entfernen
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </main>
  );
}
