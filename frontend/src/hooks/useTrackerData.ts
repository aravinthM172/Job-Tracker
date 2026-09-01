import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  type DashboardResponse,
  type Job,
  type SyncResponse,
  type SyncStatusResponse,
} from "../lib/api";

export type SyncPhase = "idle" | "syncing" | "success" | "error";

// Matches the backend's auto-sync interval (see AUTO_SYNC_INTERVAL_SECONDS
// in backend/main.py) so an open tab picks up new data soon after each
// background sync completes.
const AUTO_REFRESH_INTERVAL_MS = 5 * 60 * 1000;

interface TrackerState {
  jobs: Job[];
  dashboard: DashboardResponse["summary"] | null;
  syncStatus: SyncStatusResponse["accounts"] | null;
  loading: boolean;
  error: string | null;
}

export function useTrackerData() {
  const [state, setState] = useState<TrackerState>({
    jobs: [],
    dashboard: null,
    syncStatus: null,
    loading: true,
    error: null,
  });

  const [syncPhase, setSyncPhase] = useState<SyncPhase>("idle");
  const [syncResult, setSyncResult] = useState<SyncResponse | null>(null);
  const [syncErrorMessage, setSyncErrorMessage] = useState<string | null>(null);

  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const refresh = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const [jobsRes, dashboardRes, syncStatusRes] = await Promise.all([
        api.getJobs(),
        api.getDashboard(),
        api.getSyncStatus(),
      ]);

      if (!mounted.current) return;

      setState({
        jobs: jobsRes.jobs,
        dashboard: dashboardRes.summary,
        syncStatus: syncStatusRes.accounts,
        loading: false,
        error: null,
      });
    } catch (err) {
      if (!mounted.current) return;

      setState((prev) => ({
        ...prev,
        loading: false,
        error:
          err instanceof Error
            ? err.message
            : "Could not reach the backend API.",
      }));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // The backend auto-syncs in the background every few minutes, but
  // that doesn't push anything to the browser - without this, a tab
  // left open would keep showing whatever was loaded at mount time.
  useEffect(() => {
    const id = setInterval(refresh, AUTO_REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  // Does NOT block the UI: the button drives a small async state
  // machine, everything else stays interactive while it runs.
  const runSync = useCallback(async () => {
    setSyncPhase("syncing");
    setSyncErrorMessage(null);

    try {
      const result = await api.sync();

      if (!mounted.current) return;

      setSyncResult(result);
      setSyncPhase("success");

      // Auto-refresh dashboard data after a successful sync.
      await refresh();
    } catch (err) {
      if (!mounted.current) return;

      setSyncErrorMessage(
        err instanceof Error ? err.message : "Sync failed unexpectedly."
      );
      setSyncPhase("error");
    }
  }, [refresh]);

  const dismissSyncResult = useCallback(() => {
    setSyncPhase("idle");
    setSyncResult(null);
    setSyncErrorMessage(null);
  }, []);

  return {
    ...state,
    refresh,
    runSync,
    syncPhase,
    syncResult,
    syncErrorMessage,
    dismissSyncResult,
  };
}
