/**
 * Client HTTP minimal vers le backend FastAPI (MECHA Supervision API).
 *
 * Les loaders React Router s'executent cote serveur (Node) : on lit donc
 * l'URL du backend dans process.env. Valeur par defaut : backend local.
 * Surcharge possible via la variable d'environnement API_BASE_URL.
 */
export const API_BASE_URL =
  (typeof process !== "undefined" && process.env.API_BASE_URL) ||
  "http://localhost:8000";

/** Effectue un GET JSON et leve une erreur si le statut n'est pas 2xx. */
export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!res.ok) {
    throw new Error(`Backend ${path} a repondu ${res.status}`);
  }
  return (await res.json()) as T;
}

// --- Types renvoyes par les endpoints /analytics ---------------------------

import type {
  Alert,
  BarDatum,
  IaIndicator,
  Kpi,
  MaintenanceItem,
  ProductionLine,
  RiskMachine,
  SeriesPoint,
  StatusLevel,
} from "./types";

/** Resume d'un site renvoye par /analytics/sites. */
export interface SiteSummary {
  id: string;
  code: string;
  name: string;
  country: string;
  trs: number;
  status: StatusLevel;
}

/** Reponse complete de /analytics/site/{plant_id}. */
export interface SiteAnalytics {
  factory: SiteSummary;
  kpis: Kpi[];
  trsSeries: SeriesPoint[];
  energySeries: SeriesPoint[];
  lines: ProductionLine[];
  riskMachines: RiskMachine[];
  maintenancePlan: MaintenanceItem[];
  alerts: Alert[];
  iaIndicators: IaIndicator[];
  /** true si les indicateurs proviennent du modele IA (false = repli local). */
  iaOnline: boolean;
}

/** Reponse de /analytics/group (vue Groupe consolidee). */
export interface GroupAnalytics {
  kpis: Kpi[];
  trsBySite: BarDatum[];
  scrapBySite: BarDatum[];
  energyBySite: BarDatum[];
  alertsBySite: BarDatum[];
  alerts: Alert[];
  siteCount: number;
}

export const getSites = (signal?: AbortSignal) =>
  apiGet<SiteSummary[]>("/analytics/sites", signal);

export const getGroup = (signal?: AbortSignal) =>
  apiGet<GroupAnalytics>("/analytics/group", signal);

export const getSiteAnalytics = (plantId: string, signal?: AbortSignal) =>
  apiGet<SiteAnalytics>(`/analytics/site/${encodeURIComponent(plantId)}`, signal);
