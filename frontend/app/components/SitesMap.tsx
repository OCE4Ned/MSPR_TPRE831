import type { Factory } from "~/lib/types";
import { factoryStatusLabel, statusColor, statusHex } from "~/lib/format";

const LEGEND: { status: Factory["status"] }[] = [
  { status: "good" },
  { status: "warn" },
  { status: "crit" },
];

/**
 * Simplified geographic map. An abstract landmass silhouette stands in for
 * western Europe, with one status dot per site positioned by relative
 * coordinates.
 */
export function SitesMap({ factories }: { factories: Factory[] }) {
  return (
    <div>
      <div className="relative aspect-[16/10] w-full overflow-hidden rounded-lg border border-slate-100 bg-slate-50">
        {/* Abstract landmass backdrop */}
        <svg viewBox="0 0 100 62" className="absolute inset-0 h-full w-full" preserveAspectRatio="none">
          <path
            d="M52 8 C60 6 70 10 74 18 C80 20 84 28 80 34 C84 40 78 46 70 46 C66 54 56 56 50 52 C44 58 34 56 30 50 C20 52 14 44 18 36 C12 32 14 22 24 22 C28 14 40 10 52 8 Z"
            fill="#e2e8f0"
            stroke="#cbd5e1"
            strokeWidth={0.4}
          />
        </svg>

        {factories.map((f) => (
          <div
            key={f.id}
            className="group absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${f.map.x}%`, top: `${f.map.y}%` }}
          >
            <span className="relative flex h-3.5 w-3.5">
              <span
                className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-50 ${statusColor[f.status].dot}`}
              />
              <span
                className="relative inline-flex h-3.5 w-3.5 rounded-full ring-2 ring-white"
                style={{ backgroundColor: statusHex[f.status] }}
              />
            </span>
            <div className="pointer-events-none absolute bottom-full left-1/2 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-ink-950 px-2.5 py-1.5 text-xs text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
              <div className="font-semibold">{f.name}</div>
              <div className="text-slate-300">TRS {f.trs}%</div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3 flex items-center gap-5">
        {LEGEND.map(({ status }) => (
          <div key={status} className="flex items-center gap-1.5 text-xs text-slate-500">
            <span className={`h-2.5 w-2.5 rounded-full ${statusColor[status].dot}`} />
            {factoryStatusLabel[status]}
          </div>
        ))}
      </div>
    </div>
  );
}
