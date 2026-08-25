import { useOutletContext } from "react-router-dom";
import type { JobStatus } from "../lib/api";
import type { TrackerContext } from "../App";
import { ApplicationsView } from "../components/ApplicationsView";

interface StatusFilteredPageProps {
  status: JobStatus;
  emptyTitle: string;
  emptyDescription: string;
}

export function StatusFilteredPage({ status, emptyTitle, emptyDescription }: StatusFilteredPageProps) {
  const { jobs, openJob, runSync } = useOutletContext<TrackerContext>();

  return (
    <ApplicationsView
      jobs={jobs}
      lockedStatus={status}
      onSelectJob={(job) => openJob(job.id)}
      onSync={runSync}
      emptyTitle={emptyTitle}
      emptyDescription={emptyDescription}
    />
  );
}
