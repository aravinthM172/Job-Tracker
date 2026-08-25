import { Menu } from "lucide-react";
import type { SyncPhase } from "../hooks/useTrackerData";
import type { SyncResponse } from "../lib/api";
import { SyncButton } from "./SyncButton";

interface TopbarProps {
  title: string;
  subtitle?: string;
  onMenuClick: () => void;
  syncPhase: SyncPhase;
  syncResult: SyncResponse | null;
  syncErrorMessage: string | null;
  onSync: () => void;
  onDismissSync: () => void;
}

export function Topbar({
  title,
  subtitle,
  onMenuClick,
  syncPhase,
  syncResult,
  syncErrorMessage,
  onSync,
  onDismissSync,
}: TopbarProps) {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden"
          onClick={onMenuClick}
          aria-label="Open sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold text-slate-900">{title}</h1>
          {subtitle && <p className="truncate text-xs text-slate-500">{subtitle}</p>}
        </div>
      </div>

      <SyncButton
        phase={syncPhase}
        result={syncResult}
        errorMessage={syncErrorMessage}
        onSync={onSync}
        onDismiss={onDismissSync}
      />
    </header>
  );
}
