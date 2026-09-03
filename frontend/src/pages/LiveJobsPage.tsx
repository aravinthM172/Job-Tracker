import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CompanyLogo } from "../components/CompanyLogo";
import { useSavedJobs } from "../hooks/useSavedJobs";
import { api, API_BASE } from "../lib/api";
import {
  BriefcaseBusiness,
  Building2,
  Check,
  Clock,
  ExternalLink,
  MapPin,
  Plus,
  Radio,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Sparkles,
  Star,
  X,
} from "lucide-react";

const PAGE_SIZE = 40;

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
  experience_min: number | null;
  experience_max: number | null;
}

interface Summary {
  total: number;
  new: number;
  live: number;
  reposted: number;
  closed: number;
  new_last_hour: number;
}

// stable per-posting key for localStorage save / added tracking
function jobKey(job: LiveJob): string {
  return `${job.company.toLowerCase()}::${job.external_job_id ?? job.title.toLowerCase()}`;
}

const REFRESH_MS = 20000;

type StatusFilter = "ALL" | LiveJob["status"];
type SortKey = "newest" | "oldest" | "company";

// Experience is parsed server-side from the job title + description into
// a [min, max] year range. These buckets let the filter group them; a job
// matches a bucket when its range overlaps the bucket's range.
const EXPERIENCE_BUCKETS = [
  { key: "0-2", label: "0-2 yrs", lo: 0, hi: 2 },
  { key: "3-5", label: "3-5 yrs", lo: 3, hi: 5 },
  { key: "6-9", label: "6-9 yrs", lo: 6, hi: 9 },
  { key: "10+", label: "10+ yrs", lo: 10, hi: 99 },
  { key: "unknown", label: "Not stated", lo: -1, hi: -1 },
] as const;
type ExperienceKey = (typeof EXPERIENCE_BUCKETS)[number]["key"];

function experienceLabel(job: LiveJob): string | null {
  const { experience_min: lo, experience_max: hi } = job;
  if (lo == null && hi == null) return null;
  if (lo != null && hi != null) return lo === hi ? `${lo} yrs` : `${lo}-${hi} yrs`;
  if (lo != null) return `${lo}+ yrs`;
  return `up to ${hi} yrs`;
}

function matchesExperienceBucket(job: LiveJob, key: ExperienceKey): boolean {
  const { experience_min: lo, experience_max: hi } = job;
  if (key === "unknown") return lo == null && hi == null;
  if (lo == null && hi == null) return false;
  const bucket = EXPERIENCE_BUCKETS.find((b) => b.key === key)!;
  const jobLo = lo ?? hi ?? 0;
  const jobHi = hi ?? lo ?? 99;
  return jobLo <= bucket.hi && jobHi >= bucket.lo;
}

// Where each posting was pulled from. Almost every source is the
// employer's own ATS / careers site (first-party); Adzuna is the one
// aggregator back-fill.
const SOURCE_LABELS: Record<string, string> = {
  greenhouse: "Greenhouse",
  lever: "Lever",
  ashby: "Ashby",
  workday: "Workday",
  oracle: "Oracle Recruiting",
  smartrecruiters: "SmartRecruiters",
  successfactors: "SuccessFactors",
  keka: "Keka",
  darwinbox: "Darwinbox",
  radancy: "Careers site",
  sitemap: "Careers site",
  browser: "Careers site",
  bofa: "Careers site",
  swiggy: "Careers site",
  amazon: "Amazon Jobs",
  meta: "Meta Careers",
  google: "Google Careers",
  eightfold: "Careers site",
  phenom: "Careers site",
  avature: "Careers site",
  goldman: "Careers site",
  mynexthire: "Careers site",
  adzuna: "Adzuna (aggregator)",
};

function sourceLabel(source: string): string {
  return SOURCE_LABELS[source] ?? source;
}

// Feeds that publish no post date at all - the backend stamps a
// placeholder so the row stays in-window, so "posted X ago" would be
// fiction. Show the discovery time ("found") for these instead.
const DATELESS_SOURCES = new Set([
  "swiggy",
  "successfactors",
  "meta",
  "google",
  "browser",
]);

function postedText(job: LiveJob, now: number): string | null {
  if (DATELESS_SOURCES.has(job.source)) return null;
  return `posted ${postedDisplay(job.posted_at, now)}`;
}

function normalizeLocation(loc: string | null): string {
  if (!loc || !loc.trim()) return "Not specified";
  const t = loc.toLowerCase();
  if (t.includes("remote")) return "Remote";
  if (t.includes("hybrid")) return "Hybrid";
  if (/(bengaluru|bangalore|\bblr\b)/.test(t)) return "Bengaluru";
  return loc.split(/[,/|]/)[0].trim();
}

function statusClass(status: LiveJob["status"]) {
  switch (status) {
    case "NEW":
      return "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/50 dark:text-blue-300 dark:border-blue-900";
    case "LIVE":
      return "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-900";
    case "REPOSTED":
      return "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-900";
    case "CLOSED":
      return "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800";
  }
}

// The API serialises naive-UTC datetimes with no "Z", so a bare
// `new Date(value)` would read them as browser-local time. Normalise.
function parseTs(value: string | null): number {
  if (!value) return NaN;
  const iso = /[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`;
  return new Date(iso).getTime();
}

function timeAgo(value: string | null, now: number): string {
  const then = parseTs(value);
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

// Several feeds (Workday, Oracle, most SmartRecruiters) only publish a
// calendar date - it lands as exactly 00:00:00 UTC. Showing "7h ago" for
// those invents a precision we don't have, so render the date instead.
function postedDisplay(value: string | null, now: number): string {
  const then = parseTs(value);
  if (Number.isNaN(then)) return "date unknown";

  const d = new Date(then);
  const dateOnly =
    d.getUTCHours() === 0 &&
    d.getUTCMinutes() === 0 &&
    d.getUTCSeconds() === 0;

  if (!dateOnly) return timeAgo(value, now);

  const today = new Date(now);
  const dayDiff = Math.round(
    (Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()) -
      Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())) /
      86400000,
  );
  if (dayDiff <= 0) return "today";
  if (dayDiff === 1) return "yesterday";
  if (dayDiff < 7) return `${dayDiff}d ago`;
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
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
    new_last_hour: 0,
  });

  const { isSaved, isAdded, toggleSaved, markAdded, saved, savedCount } =
    useSavedJobs();
  const [addingKey, setAddingKey] = useState<string | null>(null);

  // Filters live in the URL so a search is bookmarkable and survives reload.
  const [params, setParams] = useSearchParams();
  const setParam = (key: string, val: string) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (val) next.set(key, val);
        else next.delete(key);
        return next;
      },
      { replace: true },
    );

  const search = params.get("q") ?? "";
  const company = params.get("company") ?? "";
  const experience = (params.get("exp") ?? "") as ExperienceKey | "";
  const location = params.get("loc") ?? "";
  const sourceFilter = params.get("src") ?? "";
  const statusFilter = (params.get("status") ?? "ALL") as StatusFilter;
  const sort = (params.get("sort") ?? "newest") as SortKey;

  const setSearch = (v: string) => setParam("q", v);
  const setCompany = (v: string) => setParam("company", v);
  const setExperience = (v: ExperienceKey | "") => setParam("exp", v);
  const setLocation = (v: string) => setParam("loc", v);
  const setSourceFilter = (v: string) => setParam("src", v);
  const setStatusFilter = (v: StatusFilter) =>
    setParam("status", v === "ALL" ? "" : v);
  const setSort = (v: SortKey) => setParam("sort", v === "newest" ? "" : v);
  const savedOnly = params.get("saved") === "1";
  const setSavedOnly = (v: boolean) => setParam("saved", v ? "1" : "");

  async function addToApplications(job: LiveJob) {
    const key = jobKey(job);
    setAddingKey(key);
    try {
      await api.createJob({
        company: job.company,
        role: job.title,
        job_id: job.job_url ?? "",
        applied_date: new Date().toISOString(),
      });
      markAdded(key);
    } catch {
      /* surfaced by the disabled->enabled button reverting */
    } finally {
      setAddingKey(null);
    }
  }

  const [visible, setVisible] = useState(PAGE_SIZE);

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

  const sources = useMemo(
    () =>
      Array.from(new Set(jobs.map((job) => job.source))).sort((a, b) =>
        sourceLabel(a).localeCompare(sourceLabel(b)),
      ),
    [jobs],
  );

  const filteredJobs = useMemo(() => {
    const value = search.trim().toLowerCase();

    const rows = jobs.filter((job) => {
      if (savedOnly && !saved.has(jobKey(job))) return false;
      if (statusFilter !== "ALL" && job.status !== statusFilter) return false;
      if (company && job.company !== company) return false;
      if (sourceFilter && job.source !== sourceFilter) return false;
      if (experience && !matchesExperienceBucket(job, experience)) return false;
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
        const at = parseTs(a.posted_at) || 0;
        const bt = parseTs(b.posted_at) || 0;
        return sort === "newest" ? bt - at : at - bt;
      });
    }
    return sorted;
  }, [
    jobs,
    search,
    company,
    sourceFilter,
    experience,
    location,
    statusFilter,
    sort,
    savedOnly,
    saved,
  ]);

  // reset the page window whenever the result set changes
  useEffect(() => {
    setVisible(PAGE_SIZE);
  }, [search, company, sourceFilter, experience, location, statusFilter, sort, savedOnly]);

  const shownJobs = filteredJobs.slice(0, visible);

  // "Freshest" = when discovery most recently *found* a new listing.
  // posted_at is unreliable for a freshness read - many ATS feeds only
  // give a date (shown as midnight), and a couple give no date at all -
  // whereas first_seen_at is stamped by our own 5-minute sync.
  const newestListingAt = useMemo(() => {
    let newest = 0;
    for (const job of jobs) {
      const t = parseTs(job.first_seen_at);
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
  if (sourceFilter)
    activeFilters.push({
      label: `via ${sourceLabel(sourceFilter)}`,
      clear: () => setSourceFilter(""),
    });
  if (experience)
    activeFilters.push({
      label:
        EXPERIENCE_BUCKETS.find((b) => b.key === experience)?.label ?? experience,
      clear: () => setExperience(""),
    });
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
    "rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-700 dark:text-slate-300 outline-none focus:border-slate-400 dark:focus:border-slate-500";

  return (
    <div className="space-y-5">
      {/* Freshness ribbon */}
      <div className="flex flex-col gap-3 rounded-xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-teal-50 p-4 dark:border-emerald-900/60 dark:from-emerald-950/40 dark:to-teal-950/30 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
          </span>
          <div className="text-sm">
            <span className="font-semibold text-slate-900 dark:text-slate-100">
              {summary.total} opening{summary.total === 1 ? "" : "s"} live
            </span>
            <span className="text-slate-500 dark:text-slate-400">
              {" · "}
              {newestListingAt
                ? `newest found ${timeAgo(new Date(newestListingAt).toISOString(), now)}`
                : "no postings yet"}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400">
            <Clock className="h-3.5 w-3.5" />
            {refreshing ? "refreshing…" : `auto-refresh in ${countdown}s`}
          </span>
          <button
            onClick={() => loadJobs(true)}
            disabled={refreshing}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-emerald-300 bg-white dark:bg-slate-800 dark:border-emerald-800 px-3 py-1.5 text-sm font-medium text-emerald-700 dark:text-emerald-300 shadow-sm hover:bg-emerald-50 dark:hover:bg-emerald-950/40 disabled:opacity-60"
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
                  ? "border-slate-900 bg-slate-900 text-white dark:border-slate-100 dark:bg-slate-100 dark:text-slate-900"
                  : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 hover:border-slate-300"
              }`}
            >
              <p
                className={`text-xs font-medium ${active ? "text-slate-300 dark:text-slate-600" : "text-slate-500 dark:text-slate-400"}`}
              >
                {chip.label}
              </p>
              <p className="mt-0.5 text-xl font-semibold">{chip.value}</p>
            </button>
          );
        })}
      </div>

      {/* Filter bar */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
          <SlidersHorizontal className="h-3.5 w-3.5" />
          Filters
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          <div className="relative sm:col-span-2 lg:col-span-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search role, company…"
              className="w-full rounded-lg border border-slate-200 dark:border-slate-800 py-2 pl-9 pr-3 text-sm outline-none focus:border-slate-400 dark:focus:border-slate-500"
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
              setExperience(event.target.value as ExperienceKey | "")
            }
            className={selectClass}
          >
            <option value="">Any experience</option>
            {EXPERIENCE_BUCKETS.map((bucket) => (
              <option key={bucket.key} value={bucket.key}>
                {bucket.label}
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

          <select
            value={sourceFilter}
            onChange={(event) => setSourceFilter(event.target.value)}
            className={selectClass}
          >
            <option value="">All sources</option>
            {sources.map((src) => (
              <option key={src} value={src}>
                {sourceLabel(src)}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {activeFilters.length === 0 ? (
              <span className="text-xs text-slate-400 dark:text-slate-500">No filters applied</span>
            ) : (
              <>
                {activeFilters.map((filter) => (
                  <button
                    key={filter.label}
                    onClick={filter.clear}
                    className="inline-flex items-center gap-1 rounded-full bg-slate-100 dark:bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-200"
                  >
                    {filter.label}
                    <X className="h-3 w-3" />
                  </button>
                ))}
                <button
                  onClick={() => {
                    setSearch("");
                    setCompany("");
                    setSourceFilter("");
                    setExperience("");
                    setLocation("");
                    setStatusFilter("ALL");
                  }}
                  className="text-xs font-medium text-slate-400 dark:text-slate-500 underline-offset-2 hover:text-slate-600 dark:hover:text-slate-300 hover:underline"
                >
                  Clear all
                </button>
              </>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setSavedOnly(!savedOnly)}
              className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-2 text-xs font-medium transition-colors ${
                savedOnly
                  ? "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400 dark:hover:bg-slate-800/60"
              }`}
            >
              <Star
                className={`h-3.5 w-3.5 ${savedOnly ? "fill-amber-400 text-amber-400" : ""}`}
              />
              Saved{savedCount > 0 ? ` (${savedCount})` : ""}
            </button>

            <label className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
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
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300">
          {error}
        </div>
      )}

      <div className="flex items-center justify-between px-1 text-xs text-slate-400 dark:text-slate-500">
        <span>
          {loading
            ? "Loading…"
            : `Showing ${Math.min(visible, filteredJobs.length)} of ${filteredJobs.length}`}
        </span>
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
            >
              <div className="h-10 w-10 shrink-0 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
              <div className="flex-1 space-y-2">
                <div className="h-3.5 w-2/5 animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
                <div className="h-3 w-3/5 animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
              </div>
            </div>
          ))}
        </div>
      ) : filteredJobs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-12 text-center">
          <BriefcaseBusiness className="mx-auto h-8 w-8 text-slate-300" />
          <h2 className="mt-3 text-sm font-semibold text-slate-800 dark:text-slate-200">
            {jobs.length === 0 ? "No Live Jobs yet" : "No jobs match your filters"}
          </h2>
          <p className="mx-auto mt-1 max-w-md text-sm text-slate-500 dark:text-slate-400">
            {jobs.length === 0
              ? "No Bengaluru jobs from tracked companies in the last 48 hours yet."
              : "Try widening the experience, location or company filter."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {shownJobs.map((job) => {
            const expLabel = experienceLabel(job);
            const key = jobKey(job);
            const saved = isSaved(key);
            const added = isAdded(key);
            return (
              <div
                key={job.id}
                className="flex flex-col gap-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm transition-shadow hover:shadow-md lg:flex-row lg:items-center lg:justify-between"
              >
                <div className="flex min-w-0 gap-4">
                  <CompanyLogo company={job.company} url={job.job_url} />

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

                    <h3 className="mt-1.5 truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {job.title}
                    </h3>

                    <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                      <span className="font-medium text-slate-600 dark:text-slate-400">
                        {job.company}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {normalizeLocation(job.location)}
                      </span>
                      {expLabel && (
                        <span className="inline-flex items-center gap-1">
                          <Sparkles className="h-3 w-3" />
                          {expLabel} exp
                        </span>
                      )}
                      <span
                        className="inline-flex items-center gap-1"
                        title={`Pulled from ${sourceLabel(job.source)}`}
                      >
                        <Building2 className="h-3 w-3" />
                        {sourceLabel(job.source)}
                      </span>
                      {postedText(job, now) && (
                        <span
                          className="inline-flex items-center gap-1"
                          title="Post date reported by the source feed"
                        >
                          <Clock className="h-3 w-3" />
                          {postedText(job, now)}
                        </span>
                      )}
                      <span
                        className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400"
                        title="When this sync first picked up the listing"
                      >
                        <Radio className="h-3 w-3" />
                        found {timeAgo(job.first_seen_at, now)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-2 self-start lg:self-auto">
                  <button
                    onClick={() => toggleSaved(key)}
                    title={saved ? "Remove bookmark" : "Save this job"}
                    aria-pressed={saved}
                    className={`inline-flex h-8 w-8 items-center justify-center rounded-lg border transition-colors ${
                      saved
                        ? "border-amber-300 bg-amber-50 text-amber-500 dark:border-amber-800 dark:bg-amber-950/40"
                        : "border-slate-200 text-slate-400 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/60"
                    }`}
                  >
                    <Star className={`h-4 w-4 ${saved ? "fill-amber-400" : ""}`} />
                  </button>

                  <button
                    onClick={() => !added && addToApplications(job)}
                    disabled={added || addingKey === key}
                    title={
                      added
                        ? "Already in your Applications"
                        : "Add to Applications as 'applied'"
                    }
                    className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-2 text-xs font-medium transition-colors ${
                      added
                        ? "border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
                        : "border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-60 dark:border-slate-800 dark:text-slate-400 dark:hover:bg-slate-800/60"
                    }`}
                  >
                    {added ? (
                      <>
                        <Check className="h-3.5 w-3.5" />
                        Added
                      </>
                    ) : (
                      <>
                        <Plus className="h-3.5 w-3.5" />
                        {addingKey === key ? "Adding…" : "Track"}
                      </>
                    )}
                  </button>

                  {job.job_url && (
                    <a
                      href={job.job_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
                    >
                      View Job
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                </div>
              </div>
            );
          })}

          {visible < filteredJobs.length && (
            <button
              onClick={() => setVisible((v) => v + PAGE_SIZE)}
              className="w-full rounded-xl border border-slate-200 bg-white py-3 text-sm font-medium text-slate-600 shadow-sm hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800/60"
            >
              Load {Math.min(PAGE_SIZE, filteredJobs.length - visible)} more
              <span className="text-slate-400 dark:text-slate-500">
                {" "}
                · {filteredJobs.length - visible} left
              </span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
