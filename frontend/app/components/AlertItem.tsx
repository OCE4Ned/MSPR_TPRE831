import type { Alert } from "~/lib/types";
import {
  severityLabel,
  severityStyle,
  statusBadge,
  statusLabel,
} from "~/lib/format";

function AlertIcon({ severity }: { severity: Alert["severity"] }) {
  const cls = `h-5 w-5 ${severityStyle[severity].icon}`;
  if (severity === "mineur") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="currentColor" aria-hidden>
        <path
          fillRule="evenodd"
          d="M12 2.25A9.75 9.75 0 1 0 21.75 12 9.76 9.76 0 0 0 12 2.25Zm0 4a1.13 1.13 0 1 1 0 2.25 1.13 1.13 0 0 1 0-2.25ZM13.13 17h-2.25v-6h2.25Z"
          clipRule="evenodd"
        />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" className={cls} fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M9.4 3.34a3 3 0 0 1 5.2 0l7.07 12.25A3 3 0 0 1 19.07 20H4.93a3 3 0 0 1-2.6-4.41Zm3.73 5.16a1.13 1.13 0 0 0-2.25 0v4.5a1.13 1.13 0 0 0 2.25 0Zm-1.13 8.25a1.13 1.13 0 1 0 0 2.25 1.13 1.13 0 0 0 0-2.25Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

/** A single operational alert row. */
export function AlertItem({ alert, showFactory = true }: { alert: Alert; showFactory?: boolean }) {
  const style = severityStyle[alert.severity];
  return (
    <div className={`flex gap-3 border-l-4 ${style.accent} rounded-r-lg bg-slate-50/60 p-4`}>
      <div className="mt-0.5 shrink-0">
        <AlertIcon severity={alert.severity} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h4 className="font-semibold text-slate-800">{alert.title}</h4>
          <span
            className={`rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${style.badge}`}
          >
            {severityLabel[alert.severity]}
          </span>
        </div>
        <p className="mt-1 text-sm text-slate-600">{alert.description}</p>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
          {showFactory && <span className="font-medium text-slate-500">{alert.factory}</span>}
          <span>{alert.date}</span>
          <span
            className={`rounded-full px-2 py-0.5 font-medium ring-1 ring-inset ${statusBadge[alert.status]}`}
          >
            {statusLabel[alert.status]}
          </span>
        </div>
      </div>
    </div>
  );
}
