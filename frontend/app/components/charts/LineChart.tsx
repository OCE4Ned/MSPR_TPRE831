import { useId } from "react";
import type { SeriesPoint } from "~/lib/types";

interface LineChartProps {
  data: SeriesPoint[];
  color?: string;
  /** Number of horizontal grid lines / y-axis ticks. */
  ticks?: number;
  unit?: string;
}

const W = 760;
const H = 260;
const PAD = { top: 16, right: 16, bottom: 28, left: 40 };

/** Lightweight SVG line chart with grid, gradient area and data points. */
export function LineChart({ data, color = "#2563eb", ticks = 4, unit }: LineChartProps) {
  const gradientId = useId();
  if (data.length === 0) return null;

  const values = data.map((d) => d.value);
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const span = rawMax - rawMin || 1;
  // Pad the domain so the curve never touches the chart edges.
  const min = Math.floor(rawMin - span * 0.25);
  const max = Math.ceil(rawMax + span * 0.25);

  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const x = (i: number) => PAD.left + (i / (data.length - 1)) * plotW;
  const y = (v: number) => PAD.top + plotH - ((v - min) / (max - min)) * plotH;

  const linePath = data.map((d, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(d.value)}`).join(" ");
  const areaPath = `${linePath} L ${x(data.length - 1)} ${PAD.top + plotH} L ${x(0)} ${
    PAD.top + plotH
  } Z`;

  const tickValues = Array.from({ length: ticks + 1 }, (_, i) => min + ((max - min) / ticks) * i);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.22} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>

      {/* Horizontal grid + y-axis labels */}
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

      <path d={areaPath} fill={`url(#${gradientId})`} />
      <path d={linePath} fill="none" stroke={color} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />

      {data.map((d, i) => (
        <g key={i}>
          <circle cx={x(i)} cy={y(d.value)} r={4} fill="#fff" stroke={color} strokeWidth={2.5} />
          <text
            x={x(i)}
            y={H - 8}
            textAnchor="middle"
            className="fill-slate-400 text-[11px]"
          >
            {d.label}
          </text>
        </g>
      ))}

      {unit && (
        <text x={PAD.left} y={12} className="fill-slate-400 text-[10px]">
          {unit}
        </text>
      )}
    </svg>
  );
}
