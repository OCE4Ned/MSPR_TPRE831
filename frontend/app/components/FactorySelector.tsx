import { useEffect, useRef, useState } from "react";
import type { Factory } from "~/lib/types";
import { statusColor } from "~/lib/format";

interface FactorySelectorProps {
  factories: Factory[];
  selected: Factory;
  onSelect: (id: string) => void;
}

/** Dropdown used in the site view to switch the active factory. */
export function FactorySelector({ factories, selected, onSelect }: FactorySelectorProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        {selected.name}
        <svg
          viewBox="0 0 24 24"
          className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {open && (
        <ul
          role="listbox"
          className="absolute right-0 z-20 mt-2 w-72 overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-xl"
        >
          {factories.map((f) => {
            const active = f.id === selected.id;
            return (
              <li key={f.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={active}
                  onClick={() => {
                    onSelect(f.id);
                    setOpen(false);
                  }}
                  className={`flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left transition hover:bg-slate-50 ${
                    active ? "bg-brand-50" : ""
                  }`}
                >
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-slate-800">{f.name}</span>
                    <span className="block text-xs text-slate-400">{f.country}</span>
                  </span>
                  <span className="flex items-center gap-2 whitespace-nowrap">
                    <span className={`h-2.5 w-2.5 rounded-full ${statusColor[f.status].dot}`} />
                    <span className="text-xs font-medium text-slate-500">TRS {f.trs}%</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
