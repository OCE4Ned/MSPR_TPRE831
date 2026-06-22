import type { BarDatum } from "~/lib/types";
import { statusHex } from "~/lib/format";

interface BarChartProps {
  data: BarDatum[];
  /** Force the top of the y-axis (e.g. 100 for a percentage chart). */
  maxValue?: number;
  ticks?: number;
  /** Suffix appended to value labels above the bars (e.g. "%"). */
  valueSuffix?: string;
}

const W = 760;
const H = 260;
const PAD = { top: 24, right: 16, bottom: 28, left: 40 };

/** Categorical SVG bar chart with status-driven colors. */
export function BarChart({ data, maxValue, ticks = 4, valueSuffix = "" }: BarChartProps) {
  if (data.length === 0) return null;

  const max = maxValue ?? Math.ceil(Math.max(...data.map((d) => d.value)) * 1.2);
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const slot = plotW / data.length;
  const barW = Math.min(slot * 0.5, 70);

  const y = (v: number) => PAD.top + plotH - (v / max) * plotH;
  const tickValues = Array.from({ length: ticks + 1 }, (_, i) => (max / ticks) * i);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img">
      {tickValues.map((tv, i) => {
        const yy = y(tv);
        return (
          <g key={i}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={yy}
              y2={yy}
              stroke="#e2e8f0"
              strokeWidth={1}
              strokeDasharray={i === 0 ? "0" : "4 4"}
            />
            <text x={PAD.left - 8} y={yy + 4} textAnchor="end" className="fill-slate-400 text-[11px]">
              {Math.round(tv)}
            </text>
          </g>
        );
      })}

      {data.map((d, i) => {
        const cx = PAD.left + slot * i + slot / 2;
        const barH = (d.value / max) * plotH;
        const yy = PAD.top + plotH - barH;
        return (
          <g key={d.label}>
            <rect
              x={cx - barW / 2}
              y={yy}
              width={barW}
              height={barH}
              rx={4}
              fill={statusHex[d.status]}
            />
            <text x={cx} y={yy - 8} textAnchor="middle" className="fill-slate-600 text-[11px] font-semibold">
              {d.value}
              {valueSuffix}
            </text>
            <text x={cx} y={H - 8} textAnchor="middle" className="fill-slate-500 text-[11px]">
              {d.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
