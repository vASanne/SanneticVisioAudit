import type { AuditStatus, Severity } from "@/lib/api";

export const severityLabel: Record<Severity, string> = {
  critical: "Kritisch",
  high: "Hoch",
  medium: "Mittel",
  low: "Niedrig",
};

export const statusLabel: Record<AuditStatus, string> = {
  pending: "Wartet",
  running: "Läuft",
  completed: "Fertig",
  failed: "Fehlgeschlagen",
};

export function severityBadge(severity: Severity): string {
  const map: Record<Severity, string> = {
    critical: "pill pill-critical",
    high: "pill pill-high",
    medium: "pill pill-medium",
    low: "pill pill-low",
  };
  return map[severity];
}

export function scoreBand(score: number | null): { className: string; label: string } {
  if (score === null) return { className: "score-card score-empty", label: "Offen" };
  if (score >= 80) return { className: "score-card score-good", label: "Gut" };
  if (score >= 50) return { className: "score-card score-mid", label: "Ausreichend" };
  return { className: "score-card score-poor", label: "Schwach" };
}
