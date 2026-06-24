import type { Alert, BarDatum, Kpi } from "~/lib/types";

export const LAST_UPDATE = "09/02/2026 14:35";

/** Consolidated KPI cards for the group view. */
export const groupKpis: Kpi[] = [
  { label: "TRS Groupe", value: 83.1, unit: "%", trend: "up", trendIsGood: true },
  {
    label: "Disponibilité machines critiques",
    value: 94.3,
    unit: "%",
    trend: "flat",
  },
  { label: "Temps cycle moyen", value: 42.5, unit: "s", trend: "down", trendIsGood: true },
  { label: "Taux de production", value: 96.8, unit: "%", trend: "up", trendIsGood: true },
  { label: "Taux de rebut global", value: 2.6, unit: "%", trend: "down", trendIsGood: true },
  {
    label: "Consommation énergétique",
    value: 20490,
    unit: "kWh",
    trend: "up",
    trendIsGood: false,
  },
  { label: "Alertes actives", value: 7, trend: "flat" },
  { label: "Production journalière", value: "24 850", unit: "pièces", accent: true },
];

/** TRS comparison across the 5 sites. */
export const trsBySite: BarDatum[] = [
  { label: "FR1", value: 87.2, status: "good" },
  { label: "FR2", value: 78.5, status: "warn" },
  { label: "ESP1", value: 92.1, status: "good" },
  { label: "ESP2", value: 72.3, status: "crit" },
  { label: "DE1", value: 85.6, status: "good" },
];

/** Scrap rate comparison across the 5 sites (%). */
export const scrapBySite: BarDatum[] = [
  { label: "FR1", value: 1.8, status: "good" },
  { label: "FR2", value: 3.2, status: "warn" },
  { label: "ESP1", value: 1.2, status: "good" },
  { label: "ESP2", value: 4.5, status: "crit" },
  { label: "DE1", value: 2.6, status: "warn" },
];

/** Energy consumption per site (MWh). */
export const energyBySite: BarDatum[] = [
  { label: "FR1", value: 3.8, status: "good" },
  { label: "FR2", value: 3.6, status: "good" },
  { label: "ESP1", value: 3.4, status: "good" },
  { label: "ESP2", value: 4.0, status: "good" },
  { label: "DE1", value: 4.2, status: "good" },
];

/** Consolidated operational alerts across all sites. */
export const groupAlerts: Alert[] = [
  {
    id: "ga-1",
    title: "Machine à l'arrêt",
    severity: "critique",
    description: "Ligne 3 - Presse hydraulique 250T",
    factory: "Usine Espagne 2",
    date: "09/02/2026 14:23",
    status: "active",
  },
  {
    id: "ga-2",
    title: "Dérive temps de cycle",
    severity: "majeur",
    description: "Ligne 1 - Temps cycle +15% vs nominal",
    factory: "Usine France 2",
    date: "09/02/2026 13:45",
    status: "en_cours",
  },
  {
    id: "ga-3",
    title: "Augmentation taux rebut",
    severity: "majeur",
    description: "Ligne 2 - Taux rebut passé de 2% à 5.2%",
    factory: "Usine Espagne 2",
    date: "09/02/2026 12:10",
    status: "active",
  },
  {
    id: "ga-4",
    title: "Rupture approvisionnement",
    severity: "critique",
    description: "Acier inox 316L - Stock critique",
    factory: "Usine France 2",
    date: "09/02/2026 11:30",
    status: "active",
  },
  {
    id: "ga-5",
    title: "Récurrence incidents",
    severity: "majeur",
    description: "3 arrêts en 2h - Ligne 3",
    factory: "Usine Espagne 2",
    date: "09/02/2026 10:15",
    status: "en_cours",
  },
  {
    id: "ga-6",
    title: "Dérive qualité",
    severity: "mineur",
    description: "Dimension hors tolérance - Lot B2345",
    factory: "Usine France 1",
    date: "09/02/2026 09:00",
    status: "en_cours",
  },
  {
    id: "ga-7",
    title: "Consommation énergétique",
    severity: "mineur",
    description: "Pic de consommation anormal +22%",
    factory: "Usine Allemagne 1",
    date: "09/02/2026 08:30",
    status: "active",
  },
];
