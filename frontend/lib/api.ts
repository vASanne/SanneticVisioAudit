export type AuditStatus = "pending" | "running" | "completed" | "failed";
export type Severity = "critical" | "high" | "medium" | "low";
export type CheckStatus = "pass" | "warning" | "fail";

export interface AuditSummary {
  id: string;
  client_name: string;
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
}

export interface AuditInput {
  url: string;
  max_pages: number;
  follow_links: boolean;
  client_name: string;
}

export function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
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

export async function createAudit(input: AuditInput): Promise<AuditDetail> {
  const response = await fetch(`${apiBase()}/api/v1/audits`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as AuditDetail;
}

export async function listAudits(): Promise<AuditSummary[]> {
  const response = await fetch(`${apiBase()}/api/v1/audits`, { cache: "no-store" });
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as AuditSummary[];
}

export async function getAudit(id: string): Promise<AuditDetail> {
  const response = await fetch(`${apiBase()}/api/v1/audits/${id}`, { cache: "no-store" });
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as AuditDetail;
}
