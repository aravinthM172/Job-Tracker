import { useOutletContext } from "react-router-dom";
import type { TrackerContext } from "../App";
import { AccountStatusList } from "../components/AccountStatusList";
import { ViewersPanel } from "../components/ViewersPanel";

export function SettingsPage() {
  const { syncStatus } = useOutletContext<TrackerContext>();

  return (
    <div className="max-w-2xl space-y-10">
      <div>
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Email Accounts</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Connection status for each mailbox the tracker scans during a sync. Tokens,
          passwords, and client secrets are never shown here.
        </p>
        <div className="mt-4">
          <AccountStatusList accounts={syncStatus} />
        </div>
      </div>

      <ViewersPanel />
    </div>
  );
}
