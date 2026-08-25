import { Search } from "lucide-react";
import type { JobStatus } from "../lib/api";
import { STATUS_LABELS } from "../lib/format";

export type SortOption =
  | "newest_applied"
  | "oldest_applied"
  | "latest_activity"
  | "company"
  | "status";

export const SORT_LABELS: Record<SortOption, string> = {
  newest_applied: "Newest application",
  oldest_applied: "Oldest application",
  latest_activity: "Latest activity",
  company: "Company",
  status: "Status",
};

export const SOURCE_OPTIONS = [
  { value: "all", label: "All" },
  { value: "gmail_1", label: "Gmail 1" },
  { value: "gmail_2", label: "Gmail 2" },
  { value: "gmail_3", label: "Gmail 3" },
  { value: "gmail_4", label: "Gmail 4" },
  { value: "outlook", label: "Outlook" },
];

export const STATUS_FILTER_OPTIONS: Array<{ value: JobStatus | "all"; label: string }> = [
  { value: "all", label: "All" },
  { value: "applied", label: STATUS_LABELS.applied },
  { value: "application_received", label: STATUS_LABELS.application_received },
  { value: "assessment", label: STATUS_LABELS.assessment },
  { value: "interview", label: STATUS_LABELS.interview },
  { value: "offer", label: STATUS_LABELS.offer },
  { value: "rejected", label: STATUS_LABELS.rejected },
  { value: "needs_review", label: STATUS_LABELS.needs_review },
];

interface JobFiltersProps {
  search: string;
  onSearchChange: (value: string) => void;
  status: JobStatus | "all";
  onStatusChange: (value: JobStatus | "all") => void;
  source: string;
  onSourceChange: (value: string) => void;
  sort: SortOption;
  onSortChange: (value: SortOption) => void;
  hideStatusFilter?: boolean;
}

export function JobFilters({
  search,
  onSearchChange,
  status,
  onStatusChange,
  source,
  onSourceChange,
  sort,
  onSortChange,
  hideStatusFilter,
}: JobFiltersProps) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3 sm:flex-row sm:items-center">
      <div className="relative flex-1">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search company, job title, sender, or subject…"
          className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-sm outline-none placeholder:text-slate-400 focus:border-slate-400 focus:bg-white"
        />
      </div>

      <div className="flex flex-wrap gap-2">
        {!hideStatusFilter && (
          <select
            value={status}
            onChange={(e) => onStatusChange(e.target.value as JobStatus | "all")}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-slate-400"
          >
            {STATUS_FILTER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                Status: {opt.label}
              </option>
            ))}
          </select>
        )}

        <select
          value={source}
          onChange={(e) => onSourceChange(e.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-slate-400"
        >
          {SOURCE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              Source: {opt.label}
            </option>
          ))}
        </select>

        <select
          value={sort}
          onChange={(e) => onSortChange(e.target.value as SortOption)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-slate-400"
        >
          {Object.entries(SORT_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              Sort: {label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
