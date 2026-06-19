import type { RiskMachine } from "~/lib/types";
import { riskStatus, statusColor } from "~/lib/format";

/** One row of the "Top machines à risque" list with a colored risk gauge. */
export function RiskMachineItem({ machine }: { machine: RiskMachine }) {
  const status = riskStatus(machine.riskScore);
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-slate-100 bg-slate-50/50 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <h4 className="font-semibold text-slate-800">{machine.name}</h4>
        <p className="mt-1 text-xs text-slate-500">
          Dernière intervention&nbsp;: {machine.lastIntervention}
          <span className="mx-2 text-slate-300">•</span>
          Incidents&nbsp;: {machine.incidents}
        </p>
      </div>
      <div className="w-full sm:w-56">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-[11px] uppercase tracking-wide text-slate-400">Score de risque</span>
          <span className={`text-sm font-semibold ${statusColor[status].text}`}>
            {machine.riskScore}/100
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
          <div
            className={`h-full rounded-full ${statusColor[status].bar}`}
            style={{ width: `${machine.riskScore}%` }}
          />
        </div>
      </div>
    </div>
  );
}
