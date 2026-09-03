import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Briefcase,
  XCircle,
  Users,
  ClipboardList,
  Settings,
  Mail,
  Radio,
  X,
} from "lucide-react";
import { API_BASE } from "../lib/api";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/applications", label: "Applications", icon: Briefcase },
  { to: "/live-jobs", label: "Live Jobs", icon: Radio },
  { to: "/interviews", label: "Interviews", icon: Users },
  { to: "/assessments", label: "Assessments", icon: ClipboardList },
  { to: "/rejected", label: "Rejected", icon: XCircle },
  { to: "/settings", label: "Settings", icon: Settings },
];

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

// "N new in the last hour" badge on the Live Jobs nav item, so an
// open tab shows when it's worth looking. Polls the lightweight
// summary endpoint (5 ints) independently of the main data hook.
function useNewLiveJobs() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let alive = true;
    const load = () =>
      fetch(`${API_BASE}/api/live-jobs/summary`)
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => {
          if (alive && d) setCount(d.new_last_hour ?? 0);
        })
        .catch(() => {});
    load();
    const id = setInterval(load, 60_000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return count;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const newLiveJobs = useNewLiveJobs();

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white transition-transform lg:static lg:translate-x-0 dark:border-slate-800 dark:bg-slate-900 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center justify-between px-5">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900">
              <Mail className="h-4 w-4" />
            </div>
            <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Job Tracker
            </span>
          </div>
          <button
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              <span className="flex-1">{item.label}</span>
              {item.to === "/live-jobs" && newLiveJobs > 0 && (
                <span className="rounded-full bg-emerald-500 px-1.5 py-0.5 text-[10px] font-semibold leading-none text-white">
                  {newLiveJobs > 99 ? "99+" : newLiveJobs} new
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-200 p-4 dark:border-slate-800">
          <p className="text-xs text-slate-400 dark:text-slate-500">
            Tracking applications across 4 Gmail accounts and Outlook.
          </p>
        </div>
      </aside>
    </>
  );
}
