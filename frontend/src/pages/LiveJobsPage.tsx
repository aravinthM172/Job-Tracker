import { useEffect, useMemo, useRef, useState } from "react";
import {
  BriefcaseBusiness,
  Clock,
  ExternalLink,
  MapPin,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Sparkles,
  X,
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
const REFRESH_MS = 20000;

type StatusFilter = "ALL" | LiveJob["status"];
type SortKey = "newest" | "oldest" | "company";

const EXPERIENCE_LEVELS = [
  "Intern",
  "Entry",
  "Mid",
  "Senior",
  "Lead+",
  "Unspecified",
] as const;
type ExperienceLevel = (typeof EXPERIENCE_LEVELS)[number];

function experienceLevel(title: string): ExperienceLevel {
  const t = ` ${title.toLowerCase()} `;
  if (/\b(intern|internship|trainee|apprentice|co-?op)\b/.test(t)) return "Intern";
  if (
    /\b(principal|staff|architect|director|head|vp|distinguished|fellow|lead|manager|mgr)\b/.test(
      t,
    )
  )
    return "Lead+";
  if (/\b(sr\.?|senior|snr|iii|iv)\b/.test(t)) return "Senior";
  if (/\b(jr\.?|junior|entry|graduate|grad|associate|fresher|trainee)\b/.test(t))
    return "Entry";
  if (/\b(ii|mid)\b/.test(t)) return "Mid";
  return "Unspecified";
}

function normalizeLocation(loc: string | null): string {
  if (!loc || !loc.trim()) return "Not specified";
  const t = loc.toLowerCase();
  if (t.includes("remote")) return "Remote";
  if (t.includes("hybrid")) return "Hybrid";
  if (/(bengaluru|bangalore|\bblr\b)/.test(t)) return "Bengaluru";
  return loc.split(/[,/|]/)[0].trim();
}

const AVATAR_COLORS = [
  "bg-blue-100 text-blue-700",
  "bg-emerald-100 text-emerald-700",
  "bg-amber-100 text-amber-700",
  "bg-violet-100 text-violet-700",
  "bg-rose-100 text-rose-700",
  "bg-cyan-100 text-cyan-700",
  "bg-indigo-100 text-indigo-700",
];

function avatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  }
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

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

function timeAgo(value: string | null, now: number): string {
  if (!value) return "unknown";
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return "unknown";

  const seconds = Math.max(0, Math.floor((now - then) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
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

  const [search, setSearch] = useState("");
  const [company, setCompany] = useState("");
  const [experience, setExperience] = useState<ExperienceLevel | "">("");
  const [location, setLocation] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [sort, setSort] = useState<SortKey>("newest");

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [now, setNow] = useState(() => Date.now());
  const lastRefreshRef = useRef<number>(Date.now());

  async function loadJobs(showSpinner = false) {
    if (showSpinner) setRefreshing(true);

    try {
      const [jobsResponse, summaryResponse] = await Promise.all([
        fetch(`${API_BASE}/api/live-jobs`),
        fetch(`${API_BASE}/api/live-jobs/summary`),
      ]);

      if (!jobsResponse.ok || !summaryResponse.ok) {
        throw new Error("Could not load Live Jobs");
      }

      setJobs(await jobsResponse.json());
      setSummary(await summaryResponse.json());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load Live Jobs");
    } finally {
      lastRefreshRef.current = Date.now();
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadJobs(true);
    const interval = window.setInterval(() => loadJobs(false), REFRESH_MS);
    return () => window.clearInterval(interval);
  }, []);

  // 1s heartbeat drives the "posted Xm ago" labels and the refresh countdown.
  useEffect(() => {
    const tick = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(tick);
  }, []);

  const companies = useMemo(
    () =>
      Array.from(new Set(jobs.map((job) => job.company))).sort((a, b) =>
        a.localeCompare(b),
      ),
    [jobs],
  );

  const locations = useMemo(
    () =>
      Array.from(new Set(jobs.map((job) => normalizeLocation(job.location)))).sort(
        (a, b) => a.localeCompare(b),
      ),
    [jobs],
  );

  const filteredJobs = useMemo(() => {
    const value = search.trim().toLowerCase();

    const rows = jobs.filter((job) => {
      if (statusFilter !== "ALL" && job.status !== statusFilter) return false;
      if (company && job.company !== company) return false;
      if (experience && experienceLevel(job.title) !== experience) return false;
      if (location && normalizeLocation(job.location) !== location) return false;
      if (value) {
        const haystack =
          `${job.company} ${job.title} ${job.location ?? ""}`.toLowerCase();
        if (!haystack.includes(value)) return false;
      }
      return true;
    });

    const sorted = [...rows];
    if (sort === "company") {
      sorted.sort((a, b) => a.company.localeCompare(b.company));
    } else {
      sorted.sort((a, b) => {
        const at = a.posted_at ? new Date(a.posted_at).getTime() : 0;
        const bt = b.posted_at ? new Date(b.posted_at).getTime() : 0;
        return sort === "newest" ? bt - at : at - bt;
      });
    }
    return sorted;
  }, [jobs, search, company, experience, location, statusFilter, sort]);

  const freshestPostedAt = useMemo(() => {
    let newest = 0;
    for (const job of jobs) {
      if (!job.posted_at) continue;
      const t = new Date(job.posted_at).getTime();
      if (!Number.isNaN(t) && t > newest) newest = t;
    }
    return newest || null;
  }, [jobs]);

  const countdown = Math.max(
    0,
    Math.ceil((lastRefreshRef.current + REFRESH_MS - now) / 1000),
  );

  const activeFilters: { label: string; clear: () => void }[] = [];
  if (statusFilter !== "ALL")
    activeFilters.push({ label: statusFilter, clear: () => setStatusFilter("ALL") });
  if (company) activeFilters.push({ label: company, clear: () => setCompany("") });
  if (experience)
    activeFilters.push({ label: experience, clear: () => setExperience("") });
  if (location) activeFilters.push({ label: location, clear: () => setLocation("") });
  if (search.trim())
    activeFilters.push({ label: `“${search.trim()}”`, clear: () => setSearch("") });

  const statChips: { key: StatusFilter; label: string; value: number }[] = [
    { key: "ALL", label: "All", value: summary.total },
    { key: "NEW", label: "New", value: summary.new },
    { key: "LIVE", label: "Live", value: summary.live },
    { key: "REPOSTED", label: "Reposted", value: summary.reposted },
    { key: "CLOSED", label: "Closed", value: summary.closed },
  ];

  const selectClass =
    "rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-slate-400";

  return (
    <div className="space-y-5">
      {/* Freshness ribbon */}
      <div className="flex flex-col gap-3 rounded-xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-teal-50 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
          </span>
          <div className="text-sm">
            <span className="font-semibold text-slate-900">
              {summary.total} opening{summary.total === 1 ? "" : "s"} live
            </span>
            <span className="text-slate-500">
              {" · "}
              {freshestPostedAt
                ? `freshest ${timeAgo(new Date(freshestPostedAt).toISOString(), now)}`
                : "no postings yet"}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
            <Clock className="h-3.5 w-3.5" />
            {refreshing ? "refreshing…" : `auto-refresh in ${countdown}s`}
          </span>
          <button
            onClick={() => loadJobs(true)}
            disabled={refreshing}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-emerald-200 bg-white px-3 py-1.5 text-sm font-medium text-emerald-700 shadow-sm hover:bg-emerald-50 disabled:opacity-60"
          >
            <RefreshCw
              className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
            />
            Refresh
          </button>
        </div>
      </div>

      {/* Status chips */}
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-5">
        {statChips.map((chip) => {
          const active = statusFilter === chip.key;
          return (
            <button
              key={chip.key}
              onClick={() => setStatusFilter(chip.key)}
              className={`rounded-xl border p-3 text-left transition-colors ${
                active
                  ? "border-slate-900 bg-slate-900 text-white"
                  : "border-slate-200 bg-white text-slate-900 hover:border-slate-300"
              }`}
            >
              <p
                className={`text-xs font-medium ${active ? "text-slate-300" : "text-slate-500"}`}
              >
                {chip.label}
              </p>
              <p className="mt-0.5 text-xl font-semibold">{chip.value}</p>
            </button>
          );
        })}
      </div>

      {/* Filter bar */}
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          <SlidersHorizontal className="h-3.5 w-3.5" />
          Filters
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="relative sm:col-span-2 lg:col-span-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search role, company…"
              className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-sm outline-none focus:border-slate-400"
            />
          </div>

          <select
            value={company}
            onChange={(event) => setCompany(event.target.value)}
            className={selectClass}
          >
            <option value="">All companies</option>
            {companies.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>

          <select
            value={experience}
            onChange={(event) =>
              setExperience(event.target.value as ExperienceLevel | "")
            }
            className={selectClass}
          >
            <option value="">Any experience</option>
            {EXPERIENCE_LEVELS.map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>

          <select
            value={location}
            onChange={(event) => setLocation(event.target.value)}
            className={selectClass}
          >
            <option value="">All locations</option>
            {locations.map((loc) => (
              <option key={loc} value={loc}>
                {loc}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {activeFilters.length === 0 ? (
              <span className="text-xs text-slate-400">No filters applied</span>
            ) : (
              <>
                {activeFilters.map((filter) => (
                  <button
                    key={filter.label}
                    onClick={filter.clear}
                    className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-200"
                  >
                    {filter.label}
                    <X className="h-3 w-3" />
                  </button>
                ))}
                <button
                  onClick={() => {
                    setSearch("");
                    setCompany("");
                    setExperience("");
                    setLocation("");
                    setStatusFilter("ALL");
                  }}
                  className="text-xs font-medium text-slate-400 underline-offset-2 hover:text-slate-600 hover:underline"
                >
                  Clear all
                </button>
              </>
            )}
          </div>

          <label className="flex items-center gap-2 text-xs text-slate-500">
            Sort
            <select
              value={sort}
              onChange={(event) => setSort(event.target.value as SortKey)}
              className={selectClass}
            >
              <option value="newest">Newest posted</option>
              <option value="oldest">Oldest posted</option>
              <option value="company">Company A–Z</option>
            </select>
          </label>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <div className="flex items-center justify-between px-1 text-xs text-slate-400">
        <span>
          {loading
            ? "Loading…"
            : `Showing ${filteredJobs.length} of ${jobs.length}`}
        </span>
      </div>

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-400">
          Loading Live Jobs…
        </div>
      ) : filteredJobs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
          <BriefcaseBusiness className="mx-auto h-8 w-8 text-slate-300" />
          <h2 className="mt-3 text-sm font-semibold text-slate-800">
            {jobs.length === 0 ? "No Live Jobs yet" : "No jobs match your filters"}
          </h2>
          <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
            {jobs.length === 0
              ? "No Bengaluru jobs from tracked companies in the last 48 hours yet."
              : "Try widening the experience, location or company filter."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredJobs.map((job) => {
            const level = experienceLevel(job.title);
            return (
              <div
                key={job.id}
                className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md lg:flex-row lg:items-center lg:justify-between"
              >
                <div className="flex min-w-0 gap-4">
                  <div
                    className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-sm font-semibold ${avatarColor(job.company)}`}
                  >
                    {job.company.slice(0, 2).toUpperCase()}
                  </div>

                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${statusClass(job.status)}`}
                      >
                        {job.status}
                      </span>
                      {job.is_reposted && job.repost_count > 0 && (
                        <span className="text-xs text-amber-600">
                          reposted {job.repost_count}×
                        </span>
                      )}
                    </div>

                    <h3 className="mt-1.5 truncate text-sm font-semibold text-slate-900">
                      {job.title}
                    </h3>

                    <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                      <span className="font-medium text-slate-600">
                        {job.company}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {normalizeLocation(job.location)}
                      </span>
                      {level !== "Unspecified" && (
                        <span className="inline-flex items-center gap-1">
                          <Sparkles className="h-3 w-3" />
                          {level}
                        </span>
                      )}
                      <span className="inline-flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        posted {timeAgo(job.posted_at, now)}
                      </span>
                    </div>
                  </div>
                </div>

                {job.job_url && (
                  <a
                    href={job.job_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex shrink-0 items-center justify-center gap-2 self-start rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-700 lg:self-auto"
                  >
                    View Job
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
