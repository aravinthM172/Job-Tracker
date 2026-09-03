import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Briefcase,
  Building2,
  ClipboardList,
  LayoutDashboard,
  Radio,
  Search,
  Settings,
  Users,
  XCircle,
} from "lucide-react";
import type { Job } from "../lib/api";

interface Command {
  id: string;
  label: string;
  hint?: string;
  icon: typeof LayoutDashboard;
  run: () => void;
}

interface CommandPaletteProps {
  jobs: Job[];
}

const PAGES: { label: string; to: string; icon: typeof LayoutDashboard }[] = [
  { label: "Dashboard", to: "/", icon: LayoutDashboard },
  { label: "Applications", to: "/applications", icon: Briefcase },
  { label: "Live Jobs", to: "/live-jobs", icon: Radio },
  { label: "Interviews", to: "/interviews", icon: Users },
  { label: "Assessments", to: "/assessments", icon: ClipboardList },
  { label: "Rejected", to: "/rejected", icon: XCircle },
  { label: "Settings", to: "/settings", icon: Settings },
];

export function CommandPalette({ jobs }: CommandPaletteProps) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActive(0);
      // focus after the element mounts
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const companies = useMemo(
    () => Array.from(new Set(jobs.map((j) => j.company))).sort((a, b) => a.localeCompare(b)),
    [jobs],
  );

  const commands = useMemo<Command[]>(() => {
    const go = (to: string) => () => {
      navigate(to);
      setOpen(false);
    };
    const pageCmds: Command[] = PAGES.map((p) => ({
      id: `page:${p.to}`,
      label: p.label,
      hint: "Page",
      icon: p.icon,
      run: go(p.to),
    }));
    const companyCmds: Command[] = companies.map((c) => ({
      id: `company:${c}`,
      label: c,
      hint: "Live Jobs",
      icon: Building2,
      run: go(`/live-jobs?company=${encodeURIComponent(c)}`),
    }));
    return [...pageCmds, ...companyCmds];
  }, [companies, navigate]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands.slice(0, 8);
    return commands
      .filter((c) => c.label.toLowerCase().includes(q))
      .slice(0, 20);
  }, [commands, query]);

  useEffect(() => {
    if (active >= results.length) setActive(0);
  }, [results, active]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/40 p-4 pt-[12vh]"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b border-slate-200 px-3 dark:border-slate-800">
          <Search className="h-4 w-4 text-slate-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActive((i) => Math.min(i + 1, results.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActive((i) => Math.max(i - 1, 0));
              } else if (e.key === "Enter") {
                e.preventDefault();
                results[active]?.run();
              }
            }}
            placeholder="Jump to a page or company…"
            className="flex-1 bg-transparent py-3 text-sm text-slate-800 outline-none placeholder:text-slate-400 dark:text-slate-100"
          />
        </div>

        <ul className="max-h-80 overflow-y-auto py-1">
          {results.length === 0 ? (
            <li className="px-4 py-6 text-center text-sm text-slate-400">
              No matches
            </li>
          ) : (
            results.map((cmd, i) => (
              <li key={cmd.id}>
                <button
                  onMouseEnter={() => setActive(i)}
                  onClick={() => cmd.run()}
                  className={`flex w-full items-center gap-3 px-4 py-2 text-left text-sm ${
                    i === active
                      ? "bg-slate-100 dark:bg-slate-800"
                      : "hover:bg-slate-50 dark:hover:bg-slate-800/60"
                  }`}
                >
                  <cmd.icon className="h-4 w-4 shrink-0 text-slate-400" />
                  <span className="flex-1 truncate text-slate-800 dark:text-slate-100">
                    {cmd.label}
                  </span>
                  {cmd.hint && (
                    <span className="shrink-0 text-xs text-slate-400">
                      {cmd.hint}
                    </span>
                  )}
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
