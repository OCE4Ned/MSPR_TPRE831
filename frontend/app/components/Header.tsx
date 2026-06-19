import { NavLink } from "react-router";

const navItems = [
  { to: "/", label: "Vue Groupe", end: true },
  { to: "/site", label: "Vue Site", end: false },
];

function GroupIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 21V8l6-3v4l6-3v4l6-3v14M3 21h18M8 21v-4m8 4v-4" />
    </svg>
  );
}

function SiteIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 21V5a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v16M12 21V11h7a1 1 0 0 1 1 1v9M4 21h17M7 8h2M7 12h2M7 16h2M15 15h2M15 18h2" />
    </svg>
  );
}

/** Top application bar with brand identity and the group / site navigation. */
export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-800 bg-ink-950">
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600 text-lg font-bold text-white shadow-md">
            M
          </div>
          <div>
            <p className="text-base font-bold leading-tight tracking-tight text-white">MECHA</p>
            <p className="text-xs text-slate-400">Système de pilotage industriel</p>
          </div>
        </div>

        <nav className="flex items-center gap-1.5">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition ${
                  isActive
                    ? "bg-brand-600 text-white shadow-sm"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`
              }
            >
              {item.to === "/" ? <GroupIcon /> : <SiteIcon />}
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
