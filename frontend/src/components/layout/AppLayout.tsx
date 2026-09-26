import { Outlet } from "react-router-dom";

export function AppLayout() {
  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-white text-slate-900  p-[15px]">
      <header className="shrink-0 border-b border-slate-200 bg-white">
        <div className="flex h-10 w-full items-center gap-2 px-3">
          <span
            className="flex h-7 w-7 items-center justify-center rounded-md bg-teal-700 text-base font-semibold text-white"
            aria-hidden="true"
          >
            +
          </span>
          <span className="text-sm font-semibold tracking-tight text-slate-900">
            EHR Patient Dashboard
          </span>
        </div>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <Outlet />
      </div>
    </div>
  );
}
