"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  ApiCredential,
  ClientRow,
  UserRow,
  createApiKey,
  createUser,
  deleteUser,
  listClients,
  listUsers,
  revokeApiKey,
  rotateApiKey,
  updateUser,
} from "@/lib/api";
import { API_SCOPES, buildUserCreateRequest, formFields, validateUserForm } from "@/lib/api-user-form";
import { useAuth } from "@/lib/auth";

export default function UsersPage() {
  const { status, loading } = useAuth();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [clients, setClients] = useState<ClientRow[]>([]);
  const [error, setError] = useState("");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [apiUser, setApiUser] = useState(false);
  const [clientIds, setClientIds] = useState<string[]>([]);
  const [scopes, setScopes] = useState<string[]>([...API_SCOPES]);
  const [expiresOn, setExpiresOn] = useState("");
  const [revealed, setRevealed] = useState<ApiCredential | null>(null);
  const [copied, setCopied] = useState("");
  const canManage = Boolean(status && (!status.auth_required || status.is_admin));
  const fields = formFields(apiUser);

  async function reload() {
    const [userRows, clientRows] = await Promise.all([listUsers(), listClients()]);
    setUsers(userRows);
    setClients(clientRows);
  }

  useEffect(() => {
    if (loading || !status || !canManage) return;
    reload().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Nutzer konnten nicht geladen werden."));
  }, [loading, status, canManage]);

  async function copyValue(label: string, value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(label);
    } catch {
      setCopied("");
      setError("Kopieren ist in diesem Browser nicht verfügbar. Bitte das Feld markieren.");
    }
  }

  function showSecret(credential: ApiCredential) {
    setRevealed(credential);
    setCopied("");
  }

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError("");
    const input = { apiUser, name, email, password, isAdmin, clientIds, scopes, expiresOn };
    const problem = validateUserForm(input);
    if (problem) {
      setError(problem);
      return;
    }
    try {
      const created = await createUser(buildUserCreateRequest(input));
      setEmail("");
      setName("");
      setPassword("");
      setIsAdmin(false);
      setClientIds([]);
      setExpiresOn("");
      setScopes([...API_SCOPES]);
      if (created.api_credential) showSecret(created.api_credential);
      await reload();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Nutzer konnte nicht angelegt werden.");
    }
  }

  function toggleScope(scope: string) {
    setScopes((current) => (current.includes(scope) ? current.filter((item) => item !== scope) : [...current, scope]));
  }

  if (loading || !status) {
    return (
      <main className="container section-sm">
        <p>Sitzung wird geprüft …</p>
      </main>
    );
  }

  if (status.auth_required && !status.is_admin) {
    return (
      <main className="container section-sm">
        <h1>Nutzerverwaltung</h1>
        <p className="form-error">Nur Admins können Nutzer verwalten.</p>
      </main>
    );
  }

  return (
    <main className="container section-sm">
      <h1>Nutzerverwaltung</h1>
      <p>Agenturnutzer anlegen, Rechte setzen und Mandanten zuordnen. API-Nutzer haben kein Passwort und keinen Browser-Login.</p>

      <form onSubmit={onCreate} className="card mt-8">
        <div className="form-group flex gap-2 form-check-row">
          <input
            id="user-api"
            type="checkbox"
            role="switch"
            aria-checked={apiUser}
            checked={apiUser}
            onChange={(event) => {
              setApiUser(event.target.checked);
              setPassword("");
              setClientIds([]);
            }}
          />
          <label htmlFor="user-api" className="check-label">
            API-Nutzer (kein Passwort, kein Browser-Login)
          </label>
        </div>
        <div className="grid grid-2">
          <div className="form-group">
            <label htmlFor="user-name">Name</label>
            <input id="user-name" required value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          {fields.showEmail ? (
            <div className="form-group">
              <label htmlFor="user-email">E-Mail</label>
              <input id="user-email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
            </div>
          ) : null}
        </div>
        {fields.loginFields ? (
          <div className="form-group">
            <label htmlFor="user-password">Passwort</label>
            <input
              id="user-password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="new-password"
            />
          </div>
        ) : null}
        {fields.showAdmin ? (
          <div className="form-group flex gap-2 form-check-row">
            <input id="user-admin" type="checkbox" checked={isAdmin} onChange={(event) => setIsAdmin(event.target.checked)} />
            <label htmlFor="user-admin" className="check-label">
              Administrator
            </label>
          </div>
        ) : null}
        <div className="form-group">
          <label htmlFor="user-clients">Mandanten</label>
          {fields.clientSelection === "single" ? (
            <select
              id="user-clients"
              required
              value={clientIds[0] ?? ""}
              onChange={(event) => setClientIds(event.target.value ? [event.target.value] : [])}
            >
              <option value="">Mandant wählen</option>
              {clients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
          ) : (
            <select
              id="user-clients"
              multiple
              value={clientIds}
              onChange={(event) => setClientIds(Array.from(event.target.selectedOptions).map((item) => item.value))}
              className="multi-select"
            >
              {clients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
          )}
        </div>
        {fields.showScopes ? (
          <fieldset className="form-group">
            <legend>Scopes</legend>
            {API_SCOPES.map((scope) => (
              <label key={scope} className="check-label form-check-row">
                <input
                  type="checkbox"
                  checked={scopes.includes(scope)}
                  onChange={() => toggleScope(scope)}
                />{" "}
                {scope}
              </label>
            ))}
          </fieldset>
        ) : null}
        {fields.showExpiry ? (
          <div className="form-group">
            <label htmlFor="user-expires">Ablauf (optional)</label>
            <input id="user-expires" type="date" value={expiresOn} onChange={(event) => setExpiresOn(event.target.value)} />
          </div>
        ) : null}
        <button type="submit" className="btn btn-gradient">
          {apiUser ? "API-Nutzer anlegen" : "Nutzer anlegen"}
        </button>
      </form>

      {revealed ? (
        <div className="card mt-8" role="status">
          <p className="form-error">
            Das Secret wird nur dieses eine Mal angezeigt. Es kann später nicht erneut geladen werden. Bitte jetzt kopieren
            und sicher ablegen.
          </p>
          <div className="form-group">
            <label htmlFor="revealed-key">Key-ID</label>
            <input id="revealed-key" readOnly value={revealed.key_id} spellCheck={false} autoComplete="off" />
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => void copyValue("Key", revealed.key_id)}>
              Key kopieren
            </button>
          </div>
          <div className="form-group">
            <label htmlFor="revealed-secret">Secret</label>
            <input id="revealed-secret" readOnly value={revealed.secret} spellCheck={false} autoComplete="off" />
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => void copyValue("Secret", revealed.secret)}>
              Secret kopieren
            </button>
          </div>
          {copied ? <p>{copied} kopiert.</p> : null}
          <button type="button" className="btn btn-secondary" onClick={() => setRevealed(null)}>
            Ich habe das Secret gespeichert
          </button>
        </div>
      ) : null}

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
              <th>E-Mail</th>
              <th>Art</th>
              <th>Mandanten</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>
                  {user.name}
                  {user.is_api_user
                    ? user.api_keys.map((key) => (
                        <div key={key.id}>
                          <code>{key.key_id}</code> {key.revoked_at ? "widerrufen" : "aktiv"}
                          {key.last_used_at ? ` · zuletzt ${key.last_used_at.slice(0, 16).replace("T", " ")}` : ""}
                        </div>
                      ))
                    : null}
                </td>
                <td>{user.email ?? "—"}</td>
                <td>{user.is_api_user ? "API-Nutzer" : user.is_admin ? "Admin" : "Mitglied"}</td>
                <td>{user.client_ids.length}</td>
                <td>
                  {user.is_api_user ? (
                    <>
                      {user.api_keys.filter((key) => !key.revoked_at).map((key) => (
                        <span key={key.id}>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => {
                              if (!window.confirm("Schlüssel rotieren? Das bisherige Secret gilt sofort nicht mehr.")) return;
                              void rotateApiKey(key.id)
                                .then((credential) => {
                                  showSecret(credential);
                                  return reload();
                                })
                                .catch((reason: unknown) =>
                                  setError(reason instanceof Error ? reason.message : "Rotation fehlgeschlagen."),
                                );
                            }}
                          >
                            Rotieren
                          </button>{" "}
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => {
                              if (!window.confirm("Schlüssel widerrufen? Agenten können ihn danach nicht mehr verwenden.")) return;
                              void revokeApiKey(key.id)
                                .then(reload)
                                .catch((reason: unknown) =>
                                  setError(reason instanceof Error ? reason.message : "Widerruf fehlgeschlagen."),
                                );
                            }}
                          >
                            Widerrufen
                          </button>{" "}
                        </span>
                      ))}
                      {user.api_keys.every((key) => key.revoked_at) ? (
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() =>
                            void createApiKey({ user_id: user.id, scopes: [...API_SCOPES] })
                              .then((credential) => {
                                showSecret(credential);
                                return reload();
                              })
                              .catch((reason: unknown) =>
                                setError(reason instanceof Error ? reason.message : "Schlüssel konnte nicht angelegt werden."),
                              )
                          }
                        >
                          Neuen Schlüssel
                        </button>
                      ) : null}{" "}
                    </>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() =>
                        void updateUser(user.id, { is_admin: !user.is_admin })
                          .then(reload)
                          .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Update fehlgeschlagen."))
                      }
                    >
                      {user.is_admin ? "Admin entziehen" : "Zum Admin"}
                    </button>
                  )}{" "}
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() =>
                      void deleteUser(user.id)
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
