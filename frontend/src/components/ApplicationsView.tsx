import { Inbox, SearchX } from "lucide-react";
import type { Job, JobStatus } from "../lib/api";
import { useJobFilters } from "../hooks/useJobFilters";
import { JobFilters } from "./JobFilters";
import { JobsTable } from "./JobsTable";
import { EmptyState } from "./EmptyState";

interface ApplicationsViewProps {
  jobs: Job[];
  lockedStatus?: JobStatus;
  onSelectJob: (job: Job) => void;
  onSync: () => void;
  emptyTitle?: string;
  emptyDescription?: string;
}

export function ApplicationsView({
  jobs,
  lockedStatus,
  onSelectJob,
  onSync,
  emptyTitle = "No applications yet",
  emptyDescription = "Run a sync to pull application emails from your connected Gmail and Outlook accounts.",
}: ApplicationsViewProps) {
  const { search, setSearch, status, setStatus, source, setSource, sort, setSort, filtered } =
    useJobFilters(jobs, lockedStatus);

  const noDataAtAll = jobs.length === 0;
  const noResultsForFilters = !noDataAtAll && filtered.length === 0;

  return (
    <div className="space-y-4">
      <JobFilters
        search={search}
        onSearchChange={setSearch}
        status={status}
        onStatusChange={setStatus}
        source={source}
        onSourceChange={setSource}
        sort={sort}
        onSortChange={setSort}
        hideStatusFilter={!!lockedStatus}
      />

      {noDataAtAll && (
        <EmptyState
          icon={Inbox}
          title={emptyTitle}
          description={emptyDescription}
          actionLabel="Sync Emails"
          onAction={onSync}
        />
      )}

      {noResultsForFilters && (
        <EmptyState
          icon={SearchX}
          title="No applications match your filters"
          description="Try a different search term or clear the status/source filters."
          actionLabel="Clear search"
          onAction={() => {
            setSearch("");
            setSource("all");
            if (!lockedStatus) setStatus("all");
          }}
        />
      )}

      {filtered.length > 0 && <JobsTable jobs={filtered} onSelect={onSelectJob} />}
    </div>
  );
}
