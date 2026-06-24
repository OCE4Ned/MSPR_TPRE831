import type { ReactNode } from "react";

interface PageHeadingProps {
  title: string;
  subtitle: string;
  lastUpdate: string;
  /** Optional control rendered on the right (e.g. the factory selector). */
  action?: ReactNode;
}

/** Title block shown at the top of each dashboard view. */
export function PageHeading({ title, subtitle, lastUpdate, action }: PageHeadingProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
          <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
        </div>
        {action}
      </div>
      <div className="text-left text-xs text-slate-400 sm:text-right">
        <p>
          Dernière mise à jour&nbsp;: <span className="font-medium text-slate-500">{lastUpdate}</span>
        </p>
        <p className="mt-0.5 italic">Maquette statique – Vision cible – PoC MECHA</p>
      </div>
    </div>
  );
}
