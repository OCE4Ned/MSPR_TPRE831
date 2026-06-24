import type { StatusLevel } from "~/lib/types";
import { statusColor } from "~/lib/format";

interface StatusDotProps {
  status: StatusLevel;
  pulse?: boolean;
  className?: string;
}

/** Small colored indicator used for factory / line health. */
export function StatusDot({ status, pulse = false, className = "" }: StatusDotProps) {
  return (
    <span className={`relative inline-flex h-2.5 w-2.5 ${className}`}>
      {pulse && (
        <span
          className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${statusColor[status].dot}`}
        />
      )}
      <span
        className={`relative inline-flex h-2.5 w-2.5 rounded-full ${statusColor[status].dot}`}
      />
    </span>
  );
}
