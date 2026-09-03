import { Menu, Moon, Sun } from "lucide-react";
import type { SyncPhase } from "../hooks/useTrackerData";
import type { Theme } from "../hooks/useTheme";
import type { SyncResponse } from "../lib/api";
import { SyncButton } from "./SyncButton";

interface TopbarProps {
  title: string;
  subtitle?: string;
  onMenuClick: () => void;
  theme: Theme;
  onToggleTheme: () => void;
  syncPhase?: SyncPhase;
  syncResult?: SyncResponse | null;
  syncErrorMessage?: string | null;
  onSync?: () => void;
  onDismissSync?: () => void;
}

export function Topbar({
  title,
  subtitle,
  onMenuClick,
  theme,
  onToggleTheme,
  syncPhase,
  syncResult,
  syncErrorMessage,
  onSync,
  onDismissSync,
}: TopbarProps) {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6 dark:border-slate-800 dark:bg-slate-900/90">
      <div className="flex min-w-0 items-center gap-3">
        <button
          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden dark:text-slate-400 dark:hover:bg-slate-800"
          onClick={onMenuClick}
          aria-label="Open sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold text-slate-900 dark:text-slate-100">
            {title}
          </h1>
          {subtitle && (
            <p className="truncate text-xs text-slate-500 dark:text-slate-400">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onToggleTheme}
          className="rounded-lg border border-slate-200 bg-white p-2 text-slate-500 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          title={theme === "dark" ? "Light mode" : "Dark mode"}
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </button>

        {onSync && (
          <SyncButton
            phase={syncPhase ?? "idle"}
            result={syncResult ?? null}
            errorMessage={syncErrorMessage ?? null}
            onSync={onSync}
            onDismiss={onDismissSync ?? (() => {})}
          />
        )}
      </div>
    </header>
  );
}
