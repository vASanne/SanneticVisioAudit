"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ClientRow, listClients, updateClient } from "@/lib/api";

export default function ClientDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [client, setClient] = useState<ClientRow | null>(null);
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [importantPaths, setImportantPaths] = useState("");
  const [whiteLabel, setWhiteLabel] = useState(false);
  const [primary, setPrimary] = useState("");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  useEffect(() => {
    listClients()
      .then((rows) => {
        const match = rows.find((item) => item.id === params.id);
        if (!match) {
          setError("Kunde nicht gefunden.");
          return;
        }
        setClient(match);
        setName(match.name);
        setDomain(match.domain || "");
        setLogoUrl(match.logo_url || "");
        const settings = match.settings || {};
        const paths = Array.isArray(settings.important_paths) ? settings.important_paths.map(String) : [];
        setImportantPaths(paths.join("\n"));
        setWhiteLabel(Boolean(settings.white_label));
        const vars = settings.css_vars && typeof settings.css_vars === "object" ? (settings.css_vars as Record<string, string>) : {};
        setPrimary(vars["--color-primary"] || "");
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Kunde konnte nicht geladen werden."));
  }, [params.id]);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    if (!client) return;
    setError("");
    setSaved("");
    try {
      const css_vars: Record<string, string> = {};
      if (primary.trim()) css_vars["--color-primary"] = primary.trim();
      const updated = await updateClient(client.id, {
        name,
        domain: domain || null,
        logo_url: logoUrl || null,
        settings: {
          ...client.settings,
          white_label: whiteLabel || Boolean(logoUrl),
          important_paths: importantPaths
            .split("\n")
            .map((item) => item.trim())
            .filter(Boolean),
          css_vars,
        },
      });
      setClient(updated);
      setSaved("Gespeichert.");
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Speichern fehlgeschlagen.");
    }
  }

  return (
    <main className="container section-sm">
      <p>
        <a href="/clients">← Kunden</a>
      </p>
      <h1>{client?.name || "Kunde"}</h1>
      <p>White-Label, Logo und wichtige Pfade für die Priorisierung.</p>

      {client ? (
        <form onSubmit={onSave} className="card mt-8">
          <div className="grid grid-2">
            <div className="form-group">
              <label htmlFor="name">Name</label>
              <input id="name" required value={name} onChange={(event) => setName(event.target.value)} />
            </div>
            <div className="form-group">
              <label htmlFor="domain">Domain</label>
              <input id="domain" value={domain} onChange={(event) => setDomain(event.target.value)} />
            </div>
          </div>
          <div className="form-group">
            <label htmlFor="logo">Logo-URL</label>
            <input id="logo" value={logoUrl} onChange={(event) => setLogoUrl(event.target.value)} />
          </div>
          <div className="form-group flex gap-2" style={{ alignItems: "center" }}>
            <input id="wl" type="checkbox" checked={whiteLabel} onChange={(event) => setWhiteLabel(event.target.checked)} />
            <label htmlFor="wl" className="check-label">
              White-Label im Bericht
            </label>
          </div>
          <div className="form-group">
            <label htmlFor="primary">Primärfarbe (--color-primary)</label>
            <input id="primary" value={primary} onChange={(event) => setPrimary(event.target.value)} placeholder="#1CC4A0" />
          </div>
          <div className="form-group">
            <label htmlFor="paths">Wichtige Pfade (eine Zeile je Pfad)</label>
            <textarea id="paths" rows={5} value={importantPaths} onChange={(event) => setImportantPaths(event.target.value)} />
          </div>
          {error ? (
            <p className="form-error">
              <span className="pill pill-critical">Fehler</span> {error}
            </p>
          ) : null}
          {saved ? <p className="text-muted">{saved}</p> : null}
          <div className="flex gap-2">
            <button type="submit" className="btn btn-gradient">
              Speichern
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => router.push("/watchlist")}>
              Zur Beobachtungsliste
            </button>
          </div>
        </form>
      ) : null}
    </main>
  );
}
