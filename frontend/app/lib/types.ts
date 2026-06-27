/** Health status level for factories, lines, and machines. */
export type StatusLevel = "good" | "warn" | "crit";

/** Tone level for IA indicators. */
export type IaIndicatorTone = "neutral" | "good" | "warn" | "crit" | "brand";

/** Production factory/site. */
export interface Factory {
  id: string;
  code: string;
  name: string;
  country: string;
  status: StatusLevel;
  trs: number;
  map: { x: number; y: number };
}

/** Production line within a factory. */
export interface ProductionLine {
  id: string;
  name: string;
  trs: number;
  production: number;
  target: number;
  status: StatusLevel;
}

/** Machine at risk. */
export interface RiskMachine {
  id: string;
  name: string;
  lastIntervention: string;
  incidents: number;
  riskScore: number;
}

/** A single data point in a time series chart. */
export interface SeriesPoint {
  label: string;
  value: number;
}

/** Key performance indicator. */
export interface Kpi {
  label: string;
  value: number | string;
  unit?: string;
  trend?: "up" | "down" | "flat";
  trendIsGood?: boolean;
  accent?: boolean;
}

/** Data point for bar charts. */
export interface BarDatum {
  label: string;
  value: number;
  status: StatusLevel;
}

/** Severity level for alerts. */
export type AlertSeverity = "mineur" | "majeur" | "critique";

/** Status level for alerts. */
export type AlertStatus = "active" | "en_cours";

/** Operational alert. */
export interface Alert {
  id: string;
  title: string;
  severity: AlertSeverity;
  description: string;
  factory: string;
  date: string;
  status: AlertStatus;
}

/** IA-ready indicator. */
export interface IaIndicator {
  label: string;
  value: string | number;
  tone: IaIndicatorTone;
}

/** Complete data set for a site. */
export interface SiteData {
  factoryId: string;
  kpis: Kpi[];
  trsSeries: SeriesPoint[];
  energySeries: SeriesPoint[];
  lines: ProductionLine[];
  riskMachines: RiskMachine[];
  alerts: Alert[];
  iaIndicators: IaIndicator[];
}
