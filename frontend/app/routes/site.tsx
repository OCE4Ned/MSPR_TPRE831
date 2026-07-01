import { useNavigate } from "react-router";
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
import { statusColor } from "~/lib/format";
import { getSites, getSiteAnalytics } from "~/lib/api";

export function meta(_: Route.MetaArgs) {
  return [
    { title: "MECHA - Vue Site" },
    {
      name: "description",
      content: "Supervision détaillée d'une usine MECHA en temps réel.",
    },
  ];
}

/**
 * Charge les donnees du site depuis le backend (schema gold).
 * Le site affiche est choisi par le parametre d'URL `?site=`, sinon le
 * premier site disponible. En cas de backend injoignable, `online` passe a
 * false et la page affiche un bandeau d'avertissement.
 */
export async function loader({ request }: Route.LoaderArgs) {
  const requested = new URL(request.url).searchParams.get("site");
  try {
    const sites = await getSites();
    if (sites.length === 0) {
      return { online: true as const, sites, site: null };
    }
    const selectedId =
      requested && sites.some((s) => s.id === requested) ? requested : sites[0].id;
    const site = await getSiteAnalytics(selectedId);
    return { online: true as const, sites, site };
  } catch {
    return { online: false as const, sites: [], site: null };
  }
}

const LAST_UPDATE = new Intl.DateTimeFormat("fr-FR", {
  dateStyle: "short",
  timeStyle: "short",
}).format(new Date());

export default function SiteView({ loaderData }: Route.ComponentProps) {
  const { online, sites, site } = loaderData;
  const navigate = useNavigate();

  if (!online || !site) {
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

  const factory = site.factory;

  return (
    <div className="space-y-6">
      <PageHeading
        title="Pilotage industriel - Vue Site"
        subtitle={`${factory.name} - ${site.lines.length} lignes - ${site.riskMachines.length} machines suivies`}
        lastUpdate={LAST_UPDATE}
        action={
          <FactorySelector
            factories={sites}
            selected={factory}
            onSelect={(id) => navigate(`?site=${encodeURIComponent(id)}`)}
          />
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

      {/* Predictive maintenance plan */}
      {site.maintenancePlan.length > 0 && (
        <Card className="p-5">
          <SectionTitle
            subtitle="Machines classées par durée de vie restante estimée (modèle RUL)"
            className="mb-4"
            icon={
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3M4 11h16M5 5h14a1 1 0 011 1v13a1 1 0 01-1 1H5a1 1 0 01-1-1V6a1 1 0 011-1z" />
              </svg>
            }
          >
            Maintenance prévisionnelle
          </SectionTitle>
          <div className="space-y-2">
            {site.maintenancePlan.map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between gap-3 rounded-lg border border-slate-100 bg-slate-50/50 px-4 py-3"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${statusColor[m.status].dot}`} />
                  <span className="font-medium text-slate-800">{m.machine}</span>
                  {m.state === "at_risk" && (
                    <span className="rounded-full bg-status-crit/10 px-2 py-0.5 text-[11px] font-medium text-status-crit ring-1 ring-inset ring-status-crit/30">
                      À risque
                    </span>
                  )}
                </div>
                <div className="text-right">
                  <div className={`text-sm font-semibold ${statusColor[m.status].text}`}>
                    {m.rulDays} j restants
                  </div>
                  <div className="text-xs text-slate-400">Échéance estimée&nbsp;: {m.dueDate}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

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
