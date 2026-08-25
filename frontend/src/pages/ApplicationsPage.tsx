import { useOutletContext } from "react-router-dom";
import type { TrackerContext } from "../App";
import { ApplicationsView } from "../components/ApplicationsView";

export function ApplicationsPage() {
  const { jobs, openJob, runSync } = useOutletContext<TrackerContext>();

  return <ApplicationsView jobs={jobs} onSelectJob={(job) => openJob(job.id)} onSync={runSync} />;
}
