import type { Route } from "./+types/group";
import { PageHeading } from "~/components/PageHeading";
import { KpiCard } from "~/components/KpiCard";
import { Card, SectionTitle } from "~/components/ui/Card";
import { BarChart } from "~/components/charts/BarChart";
import { SitesMap } from "~/components/SitesMap";
import { AlertItem } from "~/components/AlertItem";
import { factories } from "~/data/factories";
import {
  LAST_UPDATE,
  energyBySite,
  groupAlerts,
  groupKpis,
  scrapBySite,
  trsBySite,
} from "~/data/group";

export function meta(_: Route.MetaArgs) {
  return [
    { title: "MECHA – Vue Groupe" },
    {
      name: "description",
      content: "Pilotage industriel consolidé des 5 usines MECHA.",
    },
  ];
}

export default function GroupView() {
  return (
    <div className="space-y-6">
      <PageHeading
        title="Pilotage industriel – Vue Groupe MECHA"
        subtitle="Données consolidées – 5 usines – vision temps réel (PoC)"
        lastUpdate={LAST_UPDATE}
      />

      {/* Consolidated KPIs */}
      <section>
        <SectionTitle className="mb-3">Indicateurs clés de performance</SectionTitle>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {groupKpis.map((kpi) => (
            <KpiCard key={kpi.label} kpi={kpi} />
          ))}
        </div>
      </section>

      {/* Cross-factory comparison + map */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <SectionTitle className="mb-4">Comparaison inter-usines</SectionTitle>
          <p className="mb-1 text-sm font-medium text-slate-600">TRS par site (%)</p>
          <BarChart data={trsBySite} maxValue={100} valueSuffix="%" />
          <p className="mb-1 mt-5 text-sm font-medium text-slate-600">Taux de rebut par site (%)</p>
          <BarChart data={scrapBySite} maxValue={5} valueSuffix="%" />
        </Card>

        <Card className="p-5">
          <SectionTitle className="mb-4">Localisation des sites</SectionTitle>
          <SitesMap factories={factories} />
        </Card>
      </section>

      {/* Energy per site */}
      <Card className="p-5">
        <SectionTitle className="mb-4">Consommation énergétique par site (MWh)</SectionTitle>
        <BarChart data={energyBySite} maxValue={8} />
      </Card>

      {/* Operational alerts */}
      <Card className="p-5">
        <SectionTitle
          className="mb-4"
          icon={
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
          }
        >
          Alertes opérationnelles
        </SectionTitle>
        <div className="space-y-3">
          {groupAlerts.map((alert) => (
            <AlertItem key={alert.id} alert={alert} />
          ))}
        </div>
      </Card>
    </div>
  );
}
