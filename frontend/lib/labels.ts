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

export function scoreTone(score: number | null): string {
  if (score === null) return "text-ink";
  if (score >= 80) return "text-pine";
  if (score >= 50) return "text-ember";
  return "text-[#8e1b2a]";
}
