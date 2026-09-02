import { useState } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { AlertTriangle, Loader2 } from "lucide-react";
import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import { JobDetailDrawer } from "./components/JobDetailDrawer";
import { useTrackerData } from "./hooks/useTrackerData";
import type { DashboardSummary, Job, SyncStatusResponse } from "./lib/api";
import { DashboardPage } from "./pages/DashboardPage";
import { ApplicationsPage } from "./pages/ApplicationsPage";
import { StatusFilteredPage } from "./pages/StatusFilteredPage";
import { SettingsPage } from "./pages/SettingsPage";
import { LiveJobsPage } from "./pages/LiveJobsPage";

export interface TrackerContext {
  jobs: Job[];
  dashboard: DashboardSummary | null;
  syncStatus: SyncStatusResponse["accounts"] | null;
  openJob: (id: number) => void;
  runSync: () => void;
}

const PAGE_META: Record<string, { title: string; subtitle: string }> = {
  "/": { title: "Dashboard", subtitle: "Overview of every tracked application" },
  "/applications": { title: "Applications", subtitle: "All applications across every account" },
  "/interviews": { title: "Interviews", subtitle: "Applications currently in the interview stage" },
  "/assessments": { title: "Assessments", subtitle: "Applications with a pending or completed assessment" },
  "/rejected": { title: "Rejected", subtitle: "Applications that did not move forward" },
  "/settings": { title: "Settings", subtitle: "Email account connections" },
  "/live-jobs": { title: "Live Jobs", subtitle: "Fresh Bengaluru openings from tracked companies · last 48 hours" },
};

function Layout() {
  const {
    jobs,
    dashboard,
    syncStatus,
    loading,
    error,
    refresh,
    runSync,
    syncPhase,
    syncResult,
    syncErrorMessage,
    dismissSyncResult,
  } = useTrackerData();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);

  const location = useLocation();
  const meta = PAGE_META[location.pathname] ?? PAGE_META["/"];

  const context: TrackerContext = {
    jobs,
    dashboard,
    syncStatus,
    openJob: setSelectedJobId,
    runSync,
  };

  const initialLoading = loading && jobs.length === 0 && !dashboard && !error;

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          title={meta.title}
          subtitle={meta.subtitle}
          onMenuClick={() => setSidebarOpen(true)}
          syncPhase={syncPhase}
          syncResult={syncResult}
          syncErrorMessage={syncErrorMessage}
          onSync={runSync}
          onDismissSync={dismissSyncResult}
        />

        <main className="flex-1 p-4 sm:p-6">
          {error && (
            <div className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              <span className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                Could not load data from the backend: {error}
              </span>
              <button
                onClick={refresh}
                className="shrink-0 rounded-md border border-rose-300 px-3 py-1 text-xs font-medium hover:bg-rose-100"
              >
                Retry
              </button>
            </div>
          )}

          {initialLoading ? (
            <div className="flex items-center justify-center py-24 text-slate-400">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : (
            <Outlet context={context} />
          )}
        </main>
      </div>

      <JobDetailDrawer jobId={selectedJobId} onClose={() => setSelectedJobId(null)} />
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/applications" element={<ApplicationsPage />} />
        <Route
          path="/interviews"
          element={
            <StatusFilteredPage
              status="interview"
              emptyTitle="No interviews yet"
              emptyDescription="Applications will appear here once an interview-invitation email is detected."
            />
          }
        />
        <Route
          path="/assessments"
          element={
            <StatusFilteredPage
              status="assessment"
              emptyTitle="No assessments yet"
              emptyDescription="Applications will appear here once an assessment-invitation email is detected."
            />
          }
        />
        <Route
          path="/rejected"
          element={
            <StatusFilteredPage
              status="rejected"
              emptyTitle="No rejections"
              emptyDescription="Rejection emails will show up here once detected during a sync."
            />
          }
        />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/live-jobs" element={<LiveJobsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
