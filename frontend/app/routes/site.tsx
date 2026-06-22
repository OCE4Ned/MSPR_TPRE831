import { useMemo, useState } from "react";
import type { Route } from "./+types/site";
import { PageHeading } from "~/components/PageHeading";
import { KpiCard } from "~/components/KpiCard";
import { Card, SectionTitle } from "~/components/ui/Card";
import { LineChart } from "~/components/charts/LineChart";
import { ProductionLineCard } from "~/components/ProductionLineCard";
import { RiskMachineItem } from "~/components/RiskMachineItem";
import { AlertItem } from "~/components/AlertItem";
import { IaReadyCard } from "~/components/IaReadyCard";
import { FactorySelector } from "~/components/FactorySelector";
import { factories, factoriesById, DEFAULT_FACTORY_ID } from "~/data/factories";
import { getSiteData } from "~/data/site";
import { LAST_UPDATE } from "~/data/group";

export function meta(_: Route.MetaArgs) {
  return [
    { title: "MECHA – Vue Site" },
    {
      name: "description",
      content: "Supervision détaillée d'une usine MECHA en temps réel.",
    },
  ];
}

export default function SiteView() {
  const [factoryId, setFactoryId] = useState(DEFAULT_FACTORY_ID);
  const factory = factoriesById[factoryId];
  const site = useMemo(() => getSiteData(factoryId), [factoryId]);

  return (
    <div className="space-y-6">
      <PageHeading
        title="Pilotage industriel – Vue Site"
        subtitle="Suivi temps réel – 4 lignes de production – 18 machines"
        lastUpdate={LAST_UPDATE}
        action={
          <FactorySelector factories={factories} selected={factory} onSelect={setFactoryId} />
        }
      />

      {/* Site KPIs */}
      <section>
        <SectionTitle className="mb-3">Indicateurs du site</SectionTitle>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {site.kpis.map((kpi) => (
            <KpiCard key={kpi.label} kpi={kpi} />
          ))}
        </div>
      </section>

      {/* Time series */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <SectionTitle
            className="mb-4"
            icon={
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h3l2 6 4-14 2 8h2l2 4h3" />
              </svg>
            }
          >
            Évolution TRS (dernières 14h)
          </SectionTitle>
          <LineChart data={site.trsSeries} color="#2563eb" unit="%" />
        </Card>

        <Card className="p-5">
          <SectionTitle
            className="mb-4"
            icon={
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 2 4 14h7l-1 8 9-12h-7l1-8z" />
              </svg>
            }
          >
            Consommation énergétique (kWh/h)
          </SectionTitle>
          <LineChart data={site.energySeries} color="#f59e0b" unit="kWh/h" />
        </Card>
      </section>

      {/* Production lines */}
      <section>
        <SectionTitle
          className="mb-3"
          icon={
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 17l6-6 4 4 8-8M21 7v6h-6" />
            </svg>
          }
        >
          Performance par ligne de production
        </SectionTitle>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {site.lines.map((line) => (
            <ProductionLineCard key={line.id} line={line} />
          ))}
        </div>
      </section>

      {/* Top machines at risk */}
      <Card className="p-5">
        <SectionTitle
          className="mb-4"
          icon={
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.4 3.34a3 3 0 015.2 0l7.07 12.25A3 3 0 0119.07 20H4.93a3 3 0 01-2.6-4.41zM12 9v4m0 4h.01" />
            </svg>
          }
        >
          Top machines à risque
        </SectionTitle>
        <div className="space-y-3">
          {site.riskMachines.map((machine) => (
            <RiskMachineItem key={machine.id} machine={machine} />
          ))}
        </div>
      </Card>

      {/* Site alerts */}
      <Card className="p-5">
        <SectionTitle className="mb-4">Alertes du site</SectionTitle>
        {site.alerts.length > 0 ? (
          <div className="space-y-3">
            {site.alerts.map((alert) => (
              <AlertItem key={alert.id} alert={alert} showFactory={false} />
            ))}
          </div>
        ) : (
          <div className="flex items-center gap-3 rounded-lg border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
            <span className="h-2.5 w-2.5 rounded-full bg-status-good" />
            Aucune alerte active sur ce site. Tous les indicateurs sont nominaux.
          </div>
        )}
      </Card>

      {/* IA-ready indicators */}
      <Card className="border-brand-100 bg-brand-50/40 p-5">
        <SectionTitle
          subtitle="Préparation à l'intégration de l'intelligence artificielle"
          className="mb-4"
          icon={
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2m0 14v2m9-9h-2M5 12H3m13.66-6.66l-1.42 1.42M7.76 16.24l-1.42 1.42m12.32 0l-1.42-1.42M7.76 7.76L6.34 6.34M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          }
        >
          Indicateurs IA-ready
        </SectionTitle>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {site.iaIndicators.map((indicator) => (
            <IaReadyCard key={indicator.label} indicator={indicator} />
          ))}
        </div>
      </Card>
    </div>
  );
}
