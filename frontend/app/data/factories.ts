import type { Factory } from "~/lib/types";

/**
 * The five MECHA production sites. Map coordinates are expressed in percent of
 * the map container and roughly follow a western-Europe layout (France /
 * Spain / Germany).
 */
export const factories: Factory[] = [
  {
    id: "fr1",
    code: "FR1",
    name: "Usine France 1",
    country: "France",
    status: "good",
    trs: 87.2,
    map: { x: 44, y: 46 },
  },
  {
    id: "fr2",
    code: "FR2",
    name: "Usine France 2",
    country: "France",
    status: "warn",
    trs: 78.5,
    map: { x: 38, y: 58 },
  },
  {
    id: "esp1",
    code: "ESP1",
    name: "Usine Espagne 1",
    country: "Espagne",
    status: "good",
    trs: 92.1,
    map: { x: 30, y: 72 },
  },
  {
    id: "esp2",
    code: "ESP2",
    name: "Usine Espagne 2",
    country: "Espagne",
    status: "crit",
    trs: 72.3,
    map: { x: 22, y: 78 },
  },
  {
    id: "de1",
    code: "DE1",
    name: "Usine Allemagne 1",
    country: "Allemagne",
    status: "good",
    trs: 85.6,
    map: { x: 58, y: 40 },
  },
];

export const factoriesById = Object.fromEntries(
  factories.map((f) => [f.id, f]),
) as Record<string, Factory>;

export const DEFAULT_FACTORY_ID = factories[0].id;
