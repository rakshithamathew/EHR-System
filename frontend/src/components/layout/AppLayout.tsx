import { Outlet } from "react-router-dom";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-white text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center gap-3 px-4 sm:px-6 lg:px-8">
          <span
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-700 text-xl font-semibold text-white"
            aria-hidden="true"
          >
            +
          </span>
          <span className="text-base font-semibold tracking-tight text-slate-900 sm:text-lg">
            EHR Patient Dashboard
          </span>
        </div>
      </header>
      <Outlet />
    </div>
  );
}
