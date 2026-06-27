import type { AlertSeverity, AlertStatus, StatusLevel, IaIndicatorTone } from "./types";

/** Color and styling utilities for status levels. */
export const statusColor: Record<
  StatusLevel,
  { dot: string; text: string; bar: string }
> = {
  good: {
    dot: "bg-status-good",
    text: "text-status-good",
    bar: "bg-status-good",
  },
  warn: {
    dot: "bg-status-warn",
    text: "text-status-warn",
    bar: "bg-status-warn",
  },
  crit: {
    dot: "bg-status-crit",
    text: "text-status-crit",
    bar: "bg-status-crit",
  },
};

/** Hex color values for status levels (used in charts). */
export const statusHex: Record<StatusLevel, string> = {
  good: "#10b981",
  warn: "#f59e0b",
  crit: "#ef4444",
};

/** Human-readable labels for factory status levels. */
export const factoryStatusLabel: Record<StatusLevel, string> = {
  good: "Bon",
  warn: "Attention",
  crit: "Critique",
};

/** Convert a risk score (0-100) to a status level. */
export function riskStatus(score: number): StatusLevel {
  if (score >= 75) return "crit";
  if (score >= 50) return "warn";
  return "good";
}

/** Labels for alert severity levels. */
export const severityLabel: Record<AlertSeverity, string> = {
  mineur: "Mineur",
  majeur: "Majeur",
  critique: "Critique",
};

/** Styling for alert severity levels. */
export const severityStyle: Record<
  AlertSeverity,
  { icon: string; accent: string; badge: string }
> = {
  mineur: {
    icon: "text-blue-500",
    accent: "border-blue-300 bg-blue-50",
    badge: "bg-blue-50 text-blue-700 ring-blue-200",
  },
  majeur: {
    icon: "text-yellow-600",
    accent: "border-yellow-300 bg-yellow-50",
    badge: "bg-yellow-50 text-yellow-700 ring-yellow-200",
  },
  critique: {
    icon: "text-red-600",
    accent: "border-red-300 bg-red-50",
    badge: "bg-red-50 text-red-700 ring-red-200",
  },
};

/** Status badge styling for alerts. */
export const statusBadge: Record<AlertStatus, string> = {
  active: "bg-slate-50 text-slate-600 ring-slate-200",
  en_cours: "bg-blue-50 text-blue-600 ring-blue-200",
};

/** Status label text for alerts. */
export const statusLabel: Record<AlertStatus, string> = {
  active: "Actif",
  en_cours: "En cours",
};

/** Color utilities for IA indicator tones. */
export const toneColor: Record<IaIndicatorTone, string> = {
  neutral: "text-slate-800",
  good: "text-status-good",
  warn: "text-status-warn",
  crit: "text-status-crit",
  brand: "text-brand-600",
};
