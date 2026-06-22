import { Outlet } from "react-router";
import { Header } from "~/components/Header";

/** Shared shell wrapping every dashboard view. */
export default function DashboardLayout() {
  return (
    <div className="min-h-screen bg-slate-100">
      <Header />
      <main className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 sm:py-8">
        <Outlet />
      </main>
    </div>
  );
}
