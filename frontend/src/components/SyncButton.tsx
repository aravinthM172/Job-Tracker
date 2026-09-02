import { useEffect, useRef, useState } from "react";
import { RefreshCw, CheckCircle2, AlertTriangle, X } from "lucide-react";
import type { SyncPhase } from "../hooks/useTrackerData";
import type { SyncResponse } from "../lib/api";
import { accountLabel } from "../lib/format";

interface SyncButtonProps {
  phase: SyncPhase;
  result: SyncResponse | null;
  errorMessage: string | null;
  onSync: () => void;
  onDismiss: () => void;
}

export function SyncButton({ phase, result, errorMessage, onSync, onDismiss }: SyncButtonProps) {
  const [panelOpen, setPanelOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (phase === "success" || phase === "error") {
      setPanelOpen(true);
    }
  }, [phase]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setPanelOpen(false);
      }
    }
    if (panelOpen) {
      document.addEventListener("mousedown", handleClick);
      return () => document.removeEventListener("mousedown", handleClick);
    }
  }, [panelOpen]);

  const syncing = phase === "syncing";

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => {
          if (!syncing) onSync();
        }}
        disabled={syncing}
        className="flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-70"
      >
        <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
        {syncing ? "Syncing…" : "Sync Emails"}
      </button>

      {panelOpen && (phase === "success" || phase === "error") && (
        <div className="absolute right-0 z-50 mt-2 w-80 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-lg">
          <button
            className="absolute right-3 top-3 text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300"
            onClick={() => {
              setPanelOpen(false);
              onDismiss();
            }}
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>

          {phase === "success" && result && (
            <div>
              <div className="flex items-center gap-2 text-emerald-600">
                <CheckCircle2 className="h-5 w-5" />
                <p className="text-sm font-semibold">Sync completed</p>
              </div>

              <dl className="mt-3 space-y-1.5 text-sm">
                <Row label="Emails scanned" value={result.relevant_emails} />
                <Row label="New applications" value={result.jobs_created} />
                <Row label="Applications updated" value={result.jobs_updated} />
                <Row label="Rejected" value={result.rejected_count} />
                <Row label="Needs review" value={result.needs_review_count} />
              </dl>

              {result.errors.length > 0 && (
                <div className="mt-3 rounded-lg bg-amber-50 p-2.5 dark:bg-amber-950/40">
                  <p className="flex items-center gap-1.5 text-xs font-medium text-amber-700">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    {result.errors.length} account
                    {result.errors.length > 1 ? "s" : ""} need attention
                  </p>
                  <ul className="mt-1.5 space-y-1">
                    {result.errors.map((e) => (
                      <li key={e.account} className="text-xs text-amber-700">
                        <span className="font-medium">{accountLabel(e.account)}:</span>{" "}
                        {e.error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {phase === "error" && (
            <div>
              <div className="flex items-center gap-2 text-rose-600">
                <AlertTriangle className="h-5 w-5" />
                <p className="text-sm font-semibold">Sync failed</p>
              </div>
              <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">{errorMessage}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="font-medium text-slate-900 dark:text-slate-100">{value}</dd>
    </div>
  );
}
