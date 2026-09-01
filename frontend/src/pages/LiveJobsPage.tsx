import { useEffect, useMemo, useState } from "react";
import {
  BriefcaseBusiness,
  ExternalLink,
  RefreshCw,
  Search,
} from "lucide-react";

interface LiveJob {
  id: number;
  company: string;
  external_job_id: string | null;
  title: string;
  location: string | null;
  job_url: string | null;
  source: string;
  posted_at: string | null;
  first_seen_at: string;
  last_seen_at: string;
  updated_at: string;
  is_active: boolean;
  is_reposted: boolean;
  repost_count: number;
  original_first_seen_at: string | null;
  reposted_at: string | null;
  status: "NEW" | "LIVE" | "REPOSTED" | "CLOSED";
}

interface Summary {
  total: number;
  new: number;
  live: number;
  reposted: number;
  closed: number;
}

const API_BASE = "";

function statusClass(status: LiveJob["status"]) {
  switch (status) {
    case "NEW":
      return "bg-blue-50 text-blue-700 border-blue-200";
    case "LIVE":
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    case "REPOSTED":
      return "bg-amber-50 text-amber-700 border-amber-200";
    case "CLOSED":
      return "bg-slate-100 text-slate-600 border-slate-200";
  }
}

function formatPostedAt(value: string | null) {
  if (!value) return "Unknown";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";

  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function LiveJobsPage() {
  const [jobs, setJobs] = useState<LiveJob[]>([]);
  const [summary, setSummary] = useState<Summary>({
    total: 0,
    new: 0,
    live: 0,
    reposted: 0,
    closed: 0,
  });
  const [company, setCompany] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadJobs(showSpinner = false) {
    if (showSpinner) setRefreshing(true);

    try {
      const query = company
        ? `?company=${encodeURIComponent(company)}`
        : "";

      const [jobsResponse, summaryResponse] = await Promise.all([
        fetch(`${API_BASE}/api/live-jobs${query}`),
        fetch(`${API_BASE}/api/live-jobs/summary`),
      ]);

      if (!jobsResponse.ok || !summaryResponse.ok) {
        throw new Error("Could not load Live Jobs");
      }

      const jobsData = await jobsResponse.json();
      const summaryData = await summaryResponse.json();

      setJobs(jobsData);
      setSummary(summaryData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load Live Jobs");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadJobs(true);

    const interval = window.setInterval(() => {
      loadJobs(false);
    }, 15000);

    return () => window.clearInterval(interval);
  }, [company]);

  const companies = useMemo(
    () =>
      Array.from(new Set(jobs.map((job) => job.company))).sort((a, b) =>
        a.localeCompare(b),
      ),
    [jobs],
  );

  const filteredJobs = useMemo(() => {
    const value = search.trim().toLowerCase();

    if (!value) return jobs;

    return jobs.filter(
      (job) =>
        job.company.toLowerCase().includes(value) ||
        job.title.toLowerCase().includes(value) ||
        (job.location ?? "").toLowerCase().includes(value),
    );
  }, [jobs, search]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">Live Jobs</h1>
          <p className="mt-1 text-sm text-slate-500">
            Jobs discovered from tracked companies in the last 48 hours.
          </p>
        </div>

        <button
          onClick={() => loadJobs(true)}
          disabled={refreshing}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {[
          ["Total", summary.total],
          ["New", summary.new],
          ["Live", summary.live],
          ["Reposted", summary.reposted],
          ["Closed", summary.closed],
        ].map(([label, value]) => (
          <div
            key={String(label)}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <p className="text-xs font-medium text-slate-500">{label}</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">
              {value}
            </p>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search company, role or location..."
            className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-sm outline-none focus:border-slate-400"
          />
        </div>

        <select
          value={company}
          onChange={(event) => setCompany(event.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none"
        >
          <option value="">All companies</option>
          {companies.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-400">
          Loading Live Jobs...
        </div>
      ) : filteredJobs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
          <BriefcaseBusiness className="mx-auto h-8 w-8 text-slate-300" />
          <h2 className="mt-3 text-sm font-semibold text-slate-800">
            No Live Jobs found
          </h2>
          <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
            No jobs have been discovered in the current 48-hour window yet.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="divide-y divide-slate-100">
            {filteredJobs.map((job) => (
              <div
                key={job.id}
                className="flex flex-col gap-4 p-5 transition-colors hover:bg-slate-50 lg:flex-row lg:items-center lg:justify-between"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${statusClass(job.status)}`}
                    >
                      {job.status}
                    </span>

                    {job.is_reposted && job.repost_count > 0 && (
                      <span className="text-xs text-slate-400">
                        {job.repost_count} repost
                        {job.repost_count === 1 ? "" : "s"}
                      </span>
                    )}
                  </div>

                  <h3 className="mt-2 truncate text-sm font-semibold text-slate-900">
                    {job.title}
                  </h3>

                  <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
                    <span>{job.company}</span>
                    {job.location && <span>{job.location}</span>}
                    <span>Posted {formatPostedAt(job.posted_at)}</span>
                  </div>
                </div>

                {job.job_url && (
                  <a
                    href={job.job_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-700"
                  >
                    View Job
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
