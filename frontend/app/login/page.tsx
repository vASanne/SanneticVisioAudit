"use client";

import { FormEvent, Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/lib/auth";

function safeNextPath(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("://")) {
    return "/";
  }
  return value;
}

function LoginForm() {
  const { signIn, status } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("admin@sannetic.local");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      await signIn(email, password);
      router.replace(safeNextPath(params.get("next")));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Anmeldung fehlgeschlagen.");
      setPending(false);
    }
  }

  return (
    <main className="container section-sm login-narrow">
      <h1>Anmelden</h1>
      <p className="text-muted">Zugang zur Agentur-Oberfläche für Audits, Kunden und Berichte.</p>
      <form onSubmit={onSubmit} className="card mt-8">
        <div className="form-group">
          <label htmlFor="email">E-Mail</label>
          <input id="email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
        </div>
        <div className="form-group">
          <label htmlFor="password">Passwort</label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        {error ? (
          <p className="form-error">
            <span className="pill pill-critical">Fehler</span> {error}
          </p>
        ) : null}
        <button type="submit" className="btn btn-gradient" disabled={pending}>
          {pending ? "Wird geprüft …" : "Login"}
        </button>
        {!status?.auth_required ? (
          <p className="text-muted mt-4 mb-0">Login ist optional, solange Auth in der Umgebung nicht erzwungen wird.</p>
        ) : null}
      </form>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="container section-sm"><p>Login wird geladen …</p></main>}>
      <LoginForm />
    </Suspense>
  );
}
