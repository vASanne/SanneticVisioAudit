"use client";

import { FormEvent, useEffect, useState } from "react";

import { ClientRow, createClient, deleteClient, listClients } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function ClientsPage() {
  const { status } = useAuth();
  const [clients, setClients] = useState<ClientRow[]>([]);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [logoUrl, setLogoUrl] = useState("");

  async function reload() {
    setClients(await listClients());
  }

  useEffect(() => {
    reload().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Kunden konnten nicht geladen werden."));
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await createClient({
        name,
        domain: domain || null,
        logo_url: logoUrl || null,
        settings: { white_label: Boolean(logoUrl) },
      });
      setName("");
      setDomain("");
      setLogoUrl("");
      await reload();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Kunde konnte nicht angelegt werden.");
    }
  }

  return (
    <main className="container section-sm">
      <h1>Kundenverwaltung</h1>
      <p>Mandanten mit Domain, Logo und White-Label-Einstellungen pflegen.</p>

      {(status?.is_admin || !status?.auth_required) && (
        <form onSubmit={onCreate} className="card mt-8">
          <div className="grid grid-2">
            <div className="form-group">
              <label htmlFor="client-name">Name</label>
              <input id="client-name" required value={name} onChange={(event) => setName(event.target.value)} />
            </div>
            <div className="form-group">
              <label htmlFor="client-domain">Domain</label>
              <input id="client-domain" value={domain} onChange={(event) => setDomain(event.target.value)} placeholder="kunde.example" />
            </div>
          </div>
          <div className="form-group">
            <label htmlFor="client-logo">Logo-URL</label>
            <input id="client-logo" value={logoUrl} onChange={(event) => setLogoUrl(event.target.value)} placeholder="https://…" />
          </div>
          <button type="submit" className="btn btn-gradient">
            Kunde anlegen
          </button>
        </form>
      )}

      {error ? (
        <p className="form-error mt-8">
          <span className="pill pill-critical">Fehler</span> {error}
        </p>
      ) : null}

      <div className="table-responsive mt-8">
        <table className="table table-hover">
          <thead>
            <tr>
              <th>Name</th>
              <th>Domain</th>
              <th>Logo</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {clients.map((client) => (
              <tr key={client.id}>
                <td>
                  <a href={`/clients/${client.id}`}>{client.name}</a>
                </td>
                <td>{client.domain || "–"}</td>
                <td className="break-url">{client.logo_url || "–"}</td>
                <td>
                  <a className="btn btn-secondary" href={`/clients/${client.id}`}>
                    Bearbeiten
                  </a>{" "}
                  {(status?.is_admin || !status?.auth_required) && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() =>
                        void deleteClient(client.id)
                          .then(reload)
                          .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Löschen fehlgeschlagen."))
                      }
                    >
                      Löschen
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
