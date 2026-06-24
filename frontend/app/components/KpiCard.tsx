import type { Kpi } from "~/lib/types";
import { Card } from "./ui/Card";

function TrendArrow({ kpi }: { kpi: Kpi }) {
  if (!kpi.trend) return null;
  if (kpi.trend === "flat") {
    return <span className="text-slate-300" aria-label="stable">—</span>;
  }
  const good = kpi.trendIsGood;
  const color = good === undefined ? "text-slate-400" : good ? "text-status-good" : "text-status-crit";
  const up = kpi.trend === "up";
  return (
    <svg
      viewBox="0 0 24 24"
      className={`h-5 w-5 ${color}`}
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      aria-label={up ? "en hausse" : "en baisse"}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d={up ? "M5 15l7-7 7 7" : "M19 9l-7 7-7-7"}
      />
    </svg>
  );
}

/** KPI tile used in both the group and site views. */
export function KpiCard({ kpi }: { kpi: Kpi }) {
  const accent = kpi.accent;
  return (
    <Card
      className={
        accent
          ? "border-brand-600 bg-brand-600 p-4 text-white shadow-md"
          : "p-4"
      }
    >
      <div className="flex items-start justify-between gap-2">
        <p
          className={`text-[13px] font-medium leading-tight ${
            accent ? "text-brand-100" : "text-slate-500"
          }`}
        >
          {kpi.label}
        </p>
        {!accent && <TrendArrow kpi={kpi} />}
      </div>
      <div className="mt-3 flex items-baseline gap-1">
        <span
          className={`text-3xl font-semibold tracking-tight ${
            accent ? "text-white" : "text-slate-900"
          }`}
        >
          {kpi.value}
        </span>
        {kpi.unit && (
          <span
            className={`text-sm font-medium ${
              accent ? "text-brand-100" : "text-slate-400"
            }`}
          >
            {kpi.unit}
          </span>
        )}
      </div>
    </Card>
  );
}
