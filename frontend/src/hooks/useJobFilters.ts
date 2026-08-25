import { useMemo, useState } from "react";
import type { Job, JobStatus } from "../lib/api";
import type { SortOption } from "../components/JobFilters";
import { STATUS_LABELS } from "../lib/format";

function toTime(value: string | null | undefined): number {
  if (!value) return 0;
  const t = new Date(value.endsWith("Z") || value.includes("+") ? value : `${value}Z`).getTime();
  return Number.isNaN(t) ? 0 : t;
}

export function useJobFilters(jobs: Job[], lockedStatus?: JobStatus) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<JobStatus | "all">(lockedStatus ?? "all");
  const [source, setSource] = useState("all");
  const [sort, setSort] = useState<SortOption>("latest_activity");

  const filtered = useMemo(() => {
    const effectiveStatus = lockedStatus ?? status;
    const query = search.trim().toLowerCase();

    let result = jobs.filter((job) => {
      if (effectiveStatus !== "all" && job.status !== effectiveStatus) return false;
      if (source !== "all" && job.source_account !== source) return false;

      if (query) {
        const haystack = [
          job.company,
          job.role,
          job.latest_event?.subject ?? "",
          job.latest_event?.sender ?? "",
        ]
          .join(" ")
          .toLowerCase();

        if (!haystack.includes(query)) return false;
      }

      return true;
    });

    result = [...result].sort((a, b) => {
      switch (sort) {
        case "newest_applied":
          return toTime(b.applied_date) - toTime(a.applied_date);
        case "oldest_applied":
          return toTime(a.applied_date) - toTime(b.applied_date);
        case "latest_activity":
          return toTime(b.last_activity) - toTime(a.last_activity);
        case "company":
          return a.company.localeCompare(b.company);
        case "status":
          return STATUS_LABELS[a.status].localeCompare(STATUS_LABELS[b.status]);
        default:
          return 0;
      }
    });

    return result;
  }, [jobs, search, status, source, sort, lockedStatus]);

  return {
    search,
    setSearch,
    status,
    setStatus,
    source,
    setSource,
    sort,
    setSort,
    filtered,
  };
}
