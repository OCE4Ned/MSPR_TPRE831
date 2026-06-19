import type { IaIndicator } from "~/lib/types";
import { Card } from "./ui/Card";

const toneColor: Record<IaIndicator["tone"], string> = {
  neutral: "text-slate-800",
  good: "text-status-good",
  warn: "text-status-warn",
  crit: "text-status-crit",
  brand: "text-brand-600",
};

/** A single "IA-ready" indicator tile. */
export function IaReadyCard({ indicator }: { indicator: IaIndicator }) {
  return (
    <Card className="p-4">
      <p className="text-[13px] font-medium leading-tight text-slate-500">{indicator.label}</p>
      <p className={`mt-2 text-2xl font-semibold ${toneColor[indicator.tone]}`}>
        {indicator.value}
      </p>
    </Card>
  );
}
