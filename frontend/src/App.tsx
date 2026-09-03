import { useState } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { AlertTriangle, Loader2 } from "lucide-react";
import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import { JobDetailDrawer } from "./components/JobDetailDrawer";
import { CommandPalette } from "./components/CommandPalette";
import { useTrackerData } from "./hooks/useTrackerData";
import { useTheme } from "./hooks/useTheme";
import { useAuth } from "./hooks/useAuth";
import type { DashboardSummary, Job, SyncStatusResponse } from "./lib/api";
import { DashboardPage } from "./pages/DashboardPage";
import { ApplicationsPage } from "./pages/ApplicationsPage";
import { StatusFilteredPage } from "./pages/StatusFilteredPage";
import { SettingsPage } from "./pages/SettingsPage";
import { LiveJobsPage } from "./pages/LiveJobsPage";
import { LoginPage } from "./pages/LoginPage";

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
  "/settings": { title: "Settings", subtitle: "Accounts and access" },
  "/live-jobs": { title: "Live Jobs", subtitle: "Fresh Bengaluru openings from tracked companies · last 48 hours" },
};

function OwnerLayout() {
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
  const { user, logout } = useAuth();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const { theme, toggle: toggleTheme } = useTheme();

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
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        role="owner"
        username={user?.username ?? null}
        onLogout={logout}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          title={meta.title}
          subtitle={meta.subtitle}
          onMenuClick={() => setSidebarOpen(true)}
          theme={theme}
          onToggleTheme={toggleTheme}
          syncPhase={syncPhase}
          syncResult={syncResult}
          syncErrorMessage={syncErrorMessage}
          onSync={runSync}
          onDismissSync={dismissSyncResult}
        />

        <main className="flex-1 p-4 sm:p-6">
          {error && (
            <div className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300">
              <span className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                Could not load data from the backend: {error}
              </span>
              <button
                onClick={refresh}
                className="shrink-0 rounded-md border border-rose-300 px-3 py-1 text-xs font-medium hover:bg-rose-100 dark:border-rose-800 dark:hover:bg-rose-950"
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
      <CommandPalette jobs={jobs} />
    </div>
  );
}

function ViewerLayout() {
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { theme, toggle: toggleTheme } = useTheme();

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        role="viewer"
        username={user?.username ?? null}
        onLogout={logout}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          title="Live Jobs"
          subtitle={PAGE_META["/live-jobs"].subtitle}
          onMenuClick={() => setSidebarOpen(true)}
          theme={theme}
          onToggleTheme={toggleTheme}
        />
        <main className="flex-1 p-4 sm:p-6">
          <LiveJobsPage />
        </main>
      </div>
    </div>
  );
}

function OwnerApp() {
  return (
    <Routes>
      <Route element={<OwnerLayout />}>
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

function ViewerApp() {
  return (
    <Routes>
      <Route path="/live-jobs" element={<ViewerLayout />} />
      <Route path="*" element={<Navigate to="/live-jobs" replace />} />
    </Routes>
  );
}

export default function App() {
  const { status, user } = useAuth();

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-400 dark:bg-slate-950">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  if (status === "anon" || !user) {
    return <LoginPage />;
  }

  return user.role === "viewer" ? <ViewerApp /> : <OwnerApp />;
}
