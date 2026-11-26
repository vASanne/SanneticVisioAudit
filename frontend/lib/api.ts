export type AuditStatus = "pending" | "running" | "completed" | "failed";
export type Severity = "critical" | "high" | "medium" | "low";
export type CheckStatus = "pass" | "warning" | "fail";

export interface AuditSummary {
  id: string;
  client_name: string;
  client_id?: string | null;
  url: string;
  status: AuditStatus;
  created_at: string;
  finished_at: string | null;
  pages_crawled: number;
  overall_score: number | null;
  seo_score: number | null;
  geo_score: number | null;
}

export interface PageRow {
  id: string;
  url: string;
  final_url: string | null;
  status_code: number | null;
  title: string | null;
}

export interface Issue {
  id: string;
  check_id: string;
  severity: Severity;
  title: string;
  description: string;
  recommendation: string;
  affected_urls: string[];
  status: CheckStatus;
  quick_win: boolean;
  impact_score?: number | null;
}

export interface Score {
  category: string;
  score: number;
  details: Record<string, unknown>;
}

export interface AuditDetail extends AuditSummary {
  started_at: string | null;
  error_message: string | null;
  pages: PageRow[];
  issues: Issue[];
  scores: Score[];
  llm_summary?: string | null;
  gsc_notes?: string[];
}

export interface AuditInput {
  url: string;
  max_pages: number;
  follow_links: boolean;
  render_js: boolean;
  probe_internal_links: boolean;
  llm_summary: boolean;
  client_name: string;
  client_id?: string | null;
}

export interface ClientRow {
  id: string;
  name: string;
  domain: string | null;
  logo_url: string | null;
  settings: Record<string, unknown>;
  created_at: string;
}

export interface ScheduleRow {
  id: string;
  client_id: string;
  client_name: string;
  url: string;
  cron: string;
  enabled: boolean;
  config: Record<string, unknown>;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at?: string;
}

export interface WatchlistRow {
  id: string;
  client_id: string;
  client_name: string;
  url: string;
  label: string;
  notes: string;
  enabled: boolean;
  schedule_id: string | null;
  renew_enabled: boolean;
  cron: string | null;
  config: Record<string, unknown>;
  last_audit_id: string | null;
  last_overall_score: number | null;
  last_checked_at: string | null;
  next_run_at: string | null;
  created_at: string;
}

export interface UserRow {
  id: string;
  email: string;
  name: string;
  is_admin: boolean;
  client_ids: string[];
  created_at: string;
}

export interface AuthStatus {
  auth_required: boolean;
  authenticated: boolean;
  user_name: string | null;
  email: string | null;
  is_admin: boolean;
}

export interface LoginResult {
  user_name: string;
  email: string;
  is_admin: boolean;
  csrf_token: string;
}

const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const LEGACY_TOKEN_KEY = "visioaudit-token";

let csrfToken: string | null = null;
let csrfRequest: Promise<string> | null = null;

export function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
}

export function clearLegacyTokenStorage(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(LEGACY_TOKEN_KEY);
  window.sessionStorage.removeItem(LEGACY_TOKEN_KEY);
}

function rememberCsrf(token: string): void {
  if (token) csrfToken = token;
}

async function fetchCsrf(): Promise<string> {
  const response = await fetch(`${apiBase()}/api/v1/auth/csrf`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await readError(response));
  const body = (await response.json()) as { csrf_token: string };
  rememberCsrf(body.csrf_token);
  return body.csrf_token;
}

export async function ensureCsrf(): Promise<string> {
  if (csrfToken) return csrfToken;
  if (!csrfRequest) {
    csrfRequest = fetchCsrf().finally(() => {
      csrfRequest = null;
    });
  }
  return csrfRequest;
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : "Ungültige Eingabe"))
        .join(" ");
    }
  } catch {
    return `Anfrage fehlgeschlagen (${response.status}).`;
  }
  return `Anfrage fehlgeschlagen (${response.status}).`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (UNSAFE.has(method)) headers.set("X-CSRF-Token", await ensureCsrf());
  const response = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  if (response.status === 204) return undefined as T;
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as T;
}

export async function getAuthStatus(): Promise<AuthStatus> {
  return request<AuthStatus>("/api/v1/auth/status");
}

export async function login(email: string, password: string): Promise<LoginResult> {
  const token = await ensureCsrf();
  const response = await fetch(`${apiBase()}/api/v1/auth/login`, {
    method: "POST",
    credentials: "include",
    cache: "no-store",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new Error(await readError(response));
  const body = (await response.json()) as LoginResult;
  rememberCsrf(body.csrf_token);
  return body;
}

export async function logout(): Promise<void> {
  const body = await request<{ csrf_token: string }>("/api/v1/auth/logout", { method: "POST" });
  rememberCsrf(body.csrf_token);
}

export async function createAudit(input: AuditInput): Promise<AuditDetail> {
  return request<AuditDetail>("/api/v1/audits", { method: "POST", body: JSON.stringify(input) });
}

export async function listAudits(): Promise<AuditSummary[]> {
  return request<AuditSummary[]>("/api/v1/audits");
}

export async function getAudit(id: string): Promise<AuditDetail> {
  return request<AuditDetail>(`/api/v1/audits/${id}`);
}

export async function listClients(): Promise<ClientRow[]> {
  return request<ClientRow[]>("/api/v1/clients");
}

export async function createClient(input: {
  name: string;
  domain?: string | null;
  logo_url?: string | null;
  settings?: Record<string, unknown>;
}): Promise<ClientRow> {
  return request<ClientRow>("/api/v1/clients", { method: "POST", body: JSON.stringify(input) });
}

export async function updateClient(
  id: string,
  input: {
    name?: string;
    domain?: string | null;
    logo_url?: string | null;
    settings?: Record<string, unknown>;
  },
): Promise<ClientRow> {
  return request<ClientRow>(`/api/v1/clients/${id}`, { method: "PATCH", body: JSON.stringify(input) });
}

export async function deleteClient(id: string): Promise<void> {
  await request<void>(`/api/v1/clients/${id}`, { method: "DELETE" });
}

export async function listUsers(): Promise<UserRow[]> {
  return request<UserRow[]>("/api/v1/users");
}

export async function createUser(input: {
  email: string;
  name: string;
  password: string;
  is_admin: boolean;
  client_ids: string[];
}): Promise<UserRow> {
  return request<UserRow>("/api/v1/users", { method: "POST", body: JSON.stringify(input) });
}

export async function updateUser(
  id: string,
  input: {
    email?: string;
    name?: string;
    password?: string;
    is_admin?: boolean;
    client_ids?: string[];
  },
): Promise<UserRow> {
  return request<UserRow>(`/api/v1/users/${id}`, { method: "PATCH", body: JSON.stringify(input) });
}

export async function deleteUser(id: string): Promise<void> {
  await request<void>(`/api/v1/users/${id}`, { method: "DELETE" });
}

export async function listWatchlist(): Promise<WatchlistRow[]> {
  return request<WatchlistRow[]>("/api/v1/watchlist");
}

export async function createWatchlistItem(input: {
  client_id: string;
  url: string;
  label?: string;
  notes?: string;
  enabled?: boolean;
  renew_enabled?: boolean;
  cron?: string;
  config?: Record<string, unknown>;
}): Promise<WatchlistRow> {
  return request<WatchlistRow>("/api/v1/watchlist", { method: "POST", body: JSON.stringify(input) });
}

export async function updateWatchlistItem(
  id: string,
  input: {
    label?: string;
    notes?: string;
    enabled?: boolean;
    renew_enabled?: boolean;
    cron?: string;
    config?: Record<string, unknown>;
    url?: string;
  },
): Promise<WatchlistRow> {
  return request<WatchlistRow>(`/api/v1/watchlist/${id}`, { method: "PATCH", body: JSON.stringify(input) });
}

export async function deleteWatchlistItem(id: string): Promise<void> {
  await request<void>(`/api/v1/watchlist/${id}`, { method: "DELETE" });
}

export async function listSchedules(): Promise<ScheduleRow[]> {
  return request<ScheduleRow[]>("/api/v1/schedules");
}

export async function createSchedule(input: {
  client_id: string;
  url: string;
  cron: string;
  enabled?: boolean;
  config?: Record<string, unknown>;
}): Promise<ScheduleRow> {
  return request<ScheduleRow>("/api/v1/schedules", {
    method: "POST",
    body: JSON.stringify({ enabled: true, config: { max_pages: 25 }, ...input }),
  });
}

export async function updateSchedule(
  id: string,
  input: {
    url?: string;
    cron?: string;
    enabled?: boolean;
    config?: Record<string, unknown>;
  },
): Promise<ScheduleRow> {
  return request<ScheduleRow>(`/api/v1/schedules/${id}`, { method: "PATCH", body: JSON.stringify(input) });
}

export async function deleteSchedule(id: string): Promise<void> {
  await request<void>(`/api/v1/schedules/${id}`, { method: "DELETE" });
}

export function reportHtmlUrl(id: string): string {
  return `${apiBase()}/api/v1/audits/${id}/report`;
}

export function reportPdfUrl(id: string): string {
  return `${apiBase()}/api/v1/audits/${id}/report.pdf`;
}

export async function openReport(id: string, format: "html" | "pdf"): Promise<void> {
  const url = format === "pdf" ? reportPdfUrl(id) : reportHtmlUrl(id);
  const response = await fetch(url, { credentials: "include", cache: "no-store" });
  if (!response.ok) throw new Error(await readError(response));
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const opened = window.open(objectUrl, "_blank", "noopener,noreferrer");
  if (!opened) {
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = format === "pdf" ? `audit-${id}.pdf` : `audit-${id}.html`;
    anchor.rel = "noopener";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  }
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
}
