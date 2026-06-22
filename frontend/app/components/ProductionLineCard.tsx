import type { ProductionLine } from "~/lib/types";
import { statusColor } from "~/lib/format";
import { StatusDot } from "./ui/StatusDot";
import { Card } from "./ui/Card";

/** Performance card for a single production line. */
export function ProductionLineCard({ line }: { line: ProductionLine }) {
  const reach = Math.round((line.production / line.target) * 100);
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-slate-800">{line.name}</h4>
        <StatusDot status={line.status} />
      </div>
      <dl className="mt-4 space-y-2.5 text-sm">
        <div className="flex items-center justify-between">
          <dt className="text-slate-500">TRS</dt>
          <dd className="font-semibold text-slate-800">{line.trs}%</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-slate-500">Production</dt>
          <dd className="font-medium text-slate-700">{line.production.toLocaleString("fr-FR")}</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-slate-500">Objectif</dt>
          <dd className="font-medium text-slate-700">{line.target.toLocaleString("fr-FR")}</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-slate-500">Atteinte</dt>
          <dd className={`font-semibold ${statusColor[line.status].text}`}>{reach}%</dd>
        </div>
      </dl>
      <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className={`h-full rounded-full ${statusColor[line.status].bar}`}
          style={{ width: `${Math.min(100, reach)}%` }}
        />
      </div>
    </Card>
  );
}
