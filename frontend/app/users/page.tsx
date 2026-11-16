"use client";

import { FormEvent, useEffect, useState } from "react";

import { ClientRow, UserRow, createUser, deleteUser, listClients, listUsers, updateUser } from "@/lib/api";
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
  const [clientIds, setClientIds] = useState<string[]>([]);
  const canManage = Boolean(status && (!status.auth_required || status.is_admin));

  async function reload() {
    const [userRows, clientRows] = await Promise.all([listUsers(), listClients()]);
    setUsers(userRows);
    setClients(clientRows);
  }

  useEffect(() => {
    if (loading || !status || !canManage) return;
    reload().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Nutzer konnten nicht geladen werden."));
  }, [loading, status, canManage]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await createUser({ email, name, password, is_admin: isAdmin, client_ids: clientIds });
      setEmail("");
      setName("");
      setPassword("");
      setIsAdmin(false);
      setClientIds([]);
      await reload();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Nutzer konnte nicht angelegt werden.");
    }
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
      <p>Agenturnutzer anlegen, Rechte setzen und Mandanten zuordnen.</p>

      <form onSubmit={onCreate} className="card mt-8">
        <div className="grid grid-2">
          <div className="form-group">
            <label htmlFor="user-name">Name</label>
            <input id="user-name" required value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <div className="form-group">
            <label htmlFor="user-email">E-Mail</label>
            <input id="user-email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
          </div>
        </div>
        <div className="form-group">
          <label htmlFor="user-password">Passwort</label>
          <input
            id="user-password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        <div className="form-group flex gap-2" style={{ alignItems: "center" }}>
          <input id="user-admin" type="checkbox" checked={isAdmin} onChange={(event) => setIsAdmin(event.target.checked)} />
          <label htmlFor="user-admin" className="check-label">
            Administrator
          </label>
        </div>
        <div className="form-group">
          <label htmlFor="user-clients">Mandanten</label>
          <select
            id="user-clients"
            multiple
            value={clientIds}
            onChange={(event) => setClientIds(Array.from(event.target.selectedOptions).map((item) => item.value))}
            style={{ minHeight: "8rem" }}
          >
            {clients.map((client) => (
              <option key={client.id} value={client.id}>
                {client.name}
              </option>
            ))}
          </select>
        </div>
        <button type="submit" className="btn btn-gradient">
          Nutzer anlegen
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
              <th>Name</th>
              <th>E-Mail</th>
              <th>Rolle</th>
              <th>Mandanten</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.name}</td>
                <td>{user.email}</td>
                <td>{user.is_admin ? "Admin" : "Mitglied"}</td>
                <td>{user.client_ids.length}</td>
                <td>
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
                  </button>{" "}
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
