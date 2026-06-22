import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
}

/** Base surface used for every panel and KPI tile across the dashboard. */
export function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}
    >
      {children}
    </div>
  );
}

interface SectionTitleProps {
  children: ReactNode;
  icon?: ReactNode;
  subtitle?: string;
  className?: string;
}

/** Consistent heading used above each dashboard section. */
export function SectionTitle({ children, icon, subtitle, className = "" }: SectionTitleProps) {
  return (
    <div className={className}>
      <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-800">
        {icon && <span className="text-brand-600">{icon}</span>}
        {children}
      </h2>
      {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
    </div>
  );
}
