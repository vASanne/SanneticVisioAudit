"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AuditSummary, createAudit, listAudits } from "@/lib/api";
import { scoreTone, statusLabel } from "@/lib/labels";

export function HomeScreen() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [clientName, setClientName] = useState("Intern");
  const [maxPages, setMaxPages] = useState(25);
  const [followLinks, setFollowLinks] = useState(true);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [audits, setAudits] = useState<AuditSummary[]>([]);
  const [listError, setListError] = useState("");

  useEffect(() => {
    let active = true;
    listAudits()
      .then((rows) => {
        if (active) setAudits(rows);
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
        max_pages: maxPages,
        follow_links: followLinks,
      });
      router.push(`/audits/${audit.id}`);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Das Audit konnte nicht gestartet werden.");
      setPending(false);
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <p className="text-xs uppercase tracking-[0.18em] text-ink/70">Sannetic Vision Audit</p>
      <h1 className="mt-3 max-w-2xl font-serif text-5xl font-medium leading-tight">
        SEO und GEO in einem Befund.
      </h1>
      <p className="mt-4 max-w-2xl text-lg text-ink/80">
        Eine URL prüfen, priorisierte Hinweise lesen und einen kundenfähigen HTML-Bericht öffnen.
      </p>

      <form onSubmit={onSubmit} className="mt-10 border border-ink bg-card p-6">
        <label className="block text-sm" htmlFor="url">
          Start-URL
        </label>
        <input
          id="url"
          required
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://kunde.example"
          className="mt-2 w-full border border-line bg-paper px-3 py-3 text-lg outline-none focus:border-ink"
        />
        <div className="mt-4 grid gap-4 sm:grid-cols-[1fr_140px]">
          <div>
            <label className="block text-sm" htmlFor="client">
              Kunde
            </label>
            <input
              id="client"
              value={clientName}
              onChange={(event) => setClientName(event.target.value)}
              className="mt-2 w-full border border-line bg-paper px-3 py-2 outline-none focus:border-ink"
            />
          </div>
          <div>
            <label className="block text-sm" htmlFor="pages">
              Seiten
            </label>
            <input
              id="pages"
              type="number"
              min={1}
              max={100}
              value={maxPages}
              onChange={(event) => setMaxPages(Number(event.target.value))}
              className="mt-2 w-full border border-line bg-paper px-3 py-2 outline-none focus:border-ink"
            />
          </div>
        </div>
        <label className="mt-4 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={followLinks} onChange={(event) => setFollowLinks(event.target.checked)} />
          Interne Links folgen
        </label>
        {error ? <p className="mt-4 text-sm text-[#8e1b2a]">{error}</p> : null}
        <button
          type="submit"
          disabled={pending}
          className="mt-6 bg-ink px-5 py-3 text-paper disabled:opacity-60"
        >
          {pending ? "Wird angelegt …" : "Audit starten"}
        </button>
      </form>

      <section className="mt-12">
        <h2 className="font-serif text-2xl">Letzte Audits</h2>
        {listError ? <p className="mt-3 text-sm text-[#8e1b2a]">{listError}</p> : null}
        {!listError && audits.length === 0 ? <p className="mt-3 text-ink/70">Noch keine Audits.</p> : null}
        <ul className="mt-4 divide-y divide-line border-y border-line">
          {audits.map((audit) => (
            <li key={audit.id}>
              <a href={`/audits/${audit.id}`} className="flex items-baseline justify-between gap-4 py-3 hover:text-ember">
                <span>
                  <span className="block font-medium">{audit.client_name}</span>
                  <span className="text-sm text-ink/70">{audit.url}</span>
                </span>
                <span className="text-right text-sm">
                  <span className={`block font-serif text-2xl ${scoreTone(audit.overall_score)}`}>
                    {audit.overall_score ?? "–"}
                  </span>
                  {statusLabel[audit.status]}
                </span>
              </a>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
