import type { Route } from "./+types/group";
import { PageHeading } from "~/components/PageHeading";
import { KpiCard } from "~/components/KpiCard";
import { Card, SectionTitle } from "~/components/ui/Card";
import { BarChart } from "~/components/charts/BarChart";
import { AlertItem } from "~/components/AlertItem";
import { getGroup } from "~/lib/api";

export function meta(_: Route.MetaArgs) {
  return [
    { title: "MECHA - Vue Groupe" },
    {
      name: "description",
      content: "Pilotage industriel consolidé des usines MECHA.",
    },
  ];
}

/**
 * Charge les données consolidées tous sites depuis le backend (schéma gold).
 * En cas de backend injoignable, `online` passe à false.
 */
export async function loader() {
  try {
    const group = await getGroup();
    return { online: true as const, group };
  } catch {
    return { online: false as const, group: null };
  }
}

const LAST_UPDATE = new Intl.DateTimeFormat("fr-FR", {
  dateStyle: "short",
  timeStyle: "short",
}).format(new Date());

export default function GroupView({ loaderData }: Route.ComponentProps) {
  const { online, group } = loaderData;

  if (!online || !group) {
    return (
      <Card className="border-status-crit/30 bg-status-crit/5 p-6">
        <SectionTitle className="mb-2">Backend indisponible</SectionTitle>
        <p className="text-sm text-slate-600">
          Impossible de joindre l'API de supervision. Vérifiez que le backend
          est lancé (uvicorn, port 8000) et que la base <code>industrial_dw</code>{" "}
          est démarrée.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeading
        title="Pilotage industriel - Vue Groupe MECHA"
        subtitle={`Données consolidées - ${group.siteCount} usines - données réelles`}
        lastUpdate={LAST_UPDATE}
      />

      {/* Consolidated KPIs */}
      <section>
        <SectionTitle className="mb-3">Indicateurs clés de performance</SectionTitle>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {group.kpis.map((kpi) => (
            <KpiCard key={kpi.label} kpi={kpi} />
          ))}
        </div>
      </section>

      {/* Cross-factory comparison */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <SectionTitle className="mb-4">Comparaison inter-usines</SectionTitle>
          <p className="mb-1 text-sm font-medium text-slate-600">TRS par site (%)</p>
          <BarChart data={group.trsBySite} valueSuffix="%" />
          <p className="mb-1 mt-5 text-sm font-medium text-slate-600">Taux de rebut par site (%)</p>
          <BarChart data={group.scrapBySite} valueSuffix="%" />
        </Card>

        <Card className="p-5">
          <SectionTitle
            subtitle="Sites classés par état réel du parc machines (capteurs)"
            className="mb-4"
          >
            Alertes actives par site
          </SectionTitle>
          <BarChart data={group.alertsBySite} />
        </Card>
      </section>

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
        {group.alerts.length > 0 ? (
          <div className="space-y-3">
            {group.alerts.map((alert) => (
              <AlertItem key={alert.id} alert={alert} />
            ))}
          </div>
        ) : (
          <div className="flex items-center gap-3 rounded-lg border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
            <span className="h-2.5 w-2.5 rounded-full bg-status-good" />
            Aucune alerte active sur le périmètre groupe.
          </div>
        )}
      </Card>
    </div>
  );
}
