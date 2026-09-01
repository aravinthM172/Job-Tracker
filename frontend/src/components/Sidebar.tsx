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

export function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white transition-transform lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center justify-between px-5">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-white">
              <Mail className="h-4 w-4" />
            </div>
            <span className="text-sm font-semibold text-slate-900">
              Job Tracker
            </span>
          </div>
          <button
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 lg:hidden"
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
                    ? "bg-slate-900 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-200 p-4">
          <p className="text-xs text-slate-400">
            Tracking applications across 4 Gmail accounts and Outlook.
          </p>
        </div>
      </aside>
    </>
  );
}
