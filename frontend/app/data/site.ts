import type {
  Alert,
  Factory,
  IaIndicator,
  Kpi,
  ProductionLine,
  RiskMachine,
  SeriesPoint,
  SiteData,
  StatusLevel,
} from "~/lib/types";
import { factoriesById, DEFAULT_FACTORY_ID } from "./factories";
import { groupAlerts } from "./group";

/** Site-level figures that stay aligned with the consolidated group data. */
const SITE_CONFIG: Record<string, { scrap: number; energyKwh: number }> = {
  fr1: { scrap: 1.8, energyKwh: 4250 },
  fr2: { scrap: 3.2, energyKwh: 4080 },
  esp1: { scrap: 1.2, energyKwh: 3950 },
  esp2: { scrap: 4.5, energyKwh: 4520 },
  de1: { scrap: 2.6, energyKwh: 4680 },
};

const round1 = (n: number) => Math.round(n * 10) / 10;

function lineStatus(reach: number): StatusLevel {
  if (reach >= 90) return "good";
  if (reach >= 80) return "warn";
  return "crit";
}

/** Shape of the TRS curve over the last 14 hours, relative to the site TRS. */
const TRS_WAVE = [-2.2, -1.5, 0.3, 0.8, 1.8, 0.8, -0.7, -0.2];
/** Reference energy curve (kWh/h) for FR1, scaled per site. */
const ENERGY_WAVE = [370, 330, 420, 470, 510, 500, 480, 470];
const HOURS = ["00h", "02h", "04h", "06h", "08h", "10h", "12h", "14h"];

/** Reference production lines for FR1, scaled to each site's TRS. */
const BASE_LINES = [
  { id: "l1", name: "Ligne 1", trs: 92.5, production: 1850, target: 2000 },
  { id: "l2", name: "Ligne 2", trs: 88.3, production: 1420, target: 1600 },
  { id: "l3", name: "Ligne 3", trs: 85.1, production: 1710, target: 2000 },
  { id: "l4", name: "Ligne 4", trs: 91.7, production: 2200, target: 2400 },
];

const BASE_MACHINES: RiskMachine[] = [
  { id: "m1", name: "Presse 250T L3", lastIntervention: "03/02/2026", incidents: 4, riskScore: 85 },
  { id: "m2", name: "Tour CNC L2", lastIntervention: "05/02/2026", incidents: 3, riskScore: 72 },
  { id: "m3", name: "Fraiseuse L1", lastIntervention: "01/02/2026", incidents: 2, riskScore: 68 },
  { id: "m4", name: "Robot soudure L4", lastIntervention: "07/02/2026", incidents: 1, riskScore: 45 },
];

function buildKpis(factory: Factory): Kpi[] {
  const cfg = SITE_CONFIG[factory.id];
  const stops = factory.status === "crit" ? 6 : factory.status === "warn" ? 4 : 2;
  const interventions = factory.status === "crit" ? 5 : factory.status === "warn" ? 3 : 2;
  return [
    { label: "TRS", value: round1(factory.trs), unit: "%", trend: "up", trendIsGood: true },
    {
      label: "Disponibilité",
      value: round1(Math.min(99, factory.trs + 8.6)),
      unit: "%",
      trend: "flat",
    },
    { label: "Taux de rebut", value: cfg.scrap, unit: "%", trend: "down", trendIsGood: true },
    {
      label: "Consommation énergie",
      value: cfg.energyKwh,
      unit: "kWh",
      trend: "up",
      trendIsGood: false,
    },
    { label: "Arrêts aujourd'hui", value: stops, trend: "flat" },
    { label: "Interventions maintenance", value: interventions, trend: "down", trendIsGood: true },
    {
      label: "Taux d'utilisation",
      value: round1(Math.min(99, factory.trs + 4.3)),
      unit: "%",
      trend: "up",
      trendIsGood: true,
    },
    { label: "Non-conformités", value: Math.round(cfg.scrap * 2.8), trend: "down", trendIsGood: true },
  ];
}

function buildTrsSeries(factory: Factory): SeriesPoint[] {
  return TRS_WAVE.map((delta, i) => ({
    label: HOURS[i],
    value: round1(factory.trs + delta),
  }));
}

function buildEnergySeries(factory: Factory): SeriesPoint[] {
  const factor = SITE_CONFIG[factory.id].energyKwh / SITE_CONFIG.fr1.energyKwh;
  return ENERGY_WAVE.map((v, i) => ({ label: HOURS[i], value: Math.round(v * factor) }));
}

function buildLines(factory: Factory): ProductionLine[] {
  const ratio = factory.trs / factoriesById.fr1.trs;
  return BASE_LINES.map((line) => {
    const trs = round1(Math.min(99, line.trs * ratio));
    const production = Math.round(line.production * ratio);
    const reach = Math.round((production / line.target) * 100);
    return {
      id: line.id,
      name: line.name,
      trs,
      production,
      target: line.target,
      status: lineStatus(reach),
    };
  });
}

function buildMachines(factory: Factory): RiskMachine[] {
  const offset = factory.status === "crit" ? 8 : factory.status === "warn" ? 3 : 0;
  return BASE_MACHINES.map((m) => ({
    ...m,
    riskScore: Math.min(98, m.riskScore + offset),
  }));
}

function buildAlerts(factory: Factory): Alert[] {
  return groupAlerts.filter((a) => a.factory === factory.name);
}

function buildIaIndicators(factory: Factory): IaIndicator[] {
  const crit = factory.status === "crit";
  const warn = factory.status === "warn";
  const stability = round1(Math.min(99, factory.trs + 7.1));
  const driftProb = crit ? 38 : warn ? 21 : 12;
  const anomalies = crit ? 5 : warn ? 3 : 2;
  const driftTrend = crit ? "Élevée" : warn ? "Modérée" : "Faible";
  const delayRisk = crit ? "Élevé" : warn ? "Modéré" : "Faible";
  return [
    { label: "Stabilité temps cycle", value: `${stability}%`, tone: "brand" },
    {
      label: "Tendance dérive qualité",
      value: driftTrend,
      tone: crit ? "crit" : warn ? "warn" : "good",
    },
    { label: "Comportements anormaux", value: String(anomalies), tone: "neutral" },
    {
      label: "Prob. dérive qualité",
      value: `${driftProb}%`,
      tone: crit ? "crit" : warn ? "warn" : "warn",
    },
    {
      label: "Risque retard production",
      value: delayRisk,
      tone: crit ? "crit" : warn ? "warn" : "good",
    },
  ];
}

/** Build the full detailed dataset for a single site. */
export function getSiteData(factoryId: string): SiteData {
  const factory = factoriesById[factoryId] ?? factoriesById[DEFAULT_FACTORY_ID];
  return {
    factoryId: factory.id,
    kpis: buildKpis(factory),
    trsSeries: buildTrsSeries(factory),
    energySeries: buildEnergySeries(factory),
    lines: buildLines(factory),
    riskMachines: buildMachines(factory),
    alerts: buildAlerts(factory),
    iaIndicators: buildIaIndicators(factory),
  };
}
