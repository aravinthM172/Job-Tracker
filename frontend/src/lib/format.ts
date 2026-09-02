import type { AccountStatus, JobStatus } from "./api";

export const STATUS_LABELS: Record<JobStatus, string> = {
  applied: "Applied",
  application_received: "Application Received",
  assessment: "Assessment",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
  needs_review: "Needs Review",
};

export const STATUS_BADGE_CLASSES: Record<JobStatus, string> = {
  applied:
    "bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700",
  application_received:
    "bg-blue-50 text-blue-700 ring-blue-200 dark:bg-blue-950/50 dark:text-blue-300 dark:ring-blue-900",
  assessment:
    "bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:ring-amber-900",
  interview:
    "bg-indigo-50 text-indigo-700 ring-indigo-200 dark:bg-indigo-950/50 dark:text-indigo-300 dark:ring-indigo-900",
  offer:
    "bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:ring-emerald-900",
  rejected:
    "bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-950/50 dark:text-rose-300 dark:ring-rose-900",
  needs_review:
    "bg-orange-50 text-orange-700 ring-orange-200 dark:bg-orange-950/50 dark:text-orange-300 dark:ring-orange-900",
};

export const STATUS_DOT_CLASSES: Record<JobStatus, string> = {
  applied: "bg-slate-400",
  application_received: "bg-blue-500",
  assessment: "bg-amber-500",
  interview: "bg-indigo-500",
  offer: "bg-emerald-500",
  rejected: "bg-rose-500",
  needs_review: "bg-orange-500",
};

export const ACCOUNT_LABELS: Record<string, string> = {
  gmail_1: "Gmail 1",
  gmail_2: "Gmail 2",
  gmail_3: "Gmail 3",
  gmail_4: "Gmail 4",
  outlook: "Outlook",
  manual: "Manual entry",
};

export function accountLabel(account: string): string {
  return ACCOUNT_LABELS[account] || account;
}

export const ACCOUNT_STATUS_LABELS: Record<AccountStatus, string> = {
  connected: "Connected",
  auth_required: "Authentication Required",
  error: "Error",
};

export const ACCOUNT_STATUS_CLASSES: Record<AccountStatus, string> = {
  connected:
    "bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:ring-emerald-900",
  auth_required:
    "bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:ring-amber-900",
  error:
    "bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-950/50 dark:text-rose-300 dark:ring-rose-900",
};

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";

  const date = new Date(value.endsWith("Z") || value.includes("+") ? value : `${value}Z`);

  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";

  const date = new Date(value.endsWith("Z") || value.includes("+") ? value : `${value}Z`);

  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function relativeTime(value: string | null | undefined): string {
  if (!value) return "—";

  const date = new Date(value.endsWith("Z") || value.includes("+") ? value : `${value}Z`);

  if (Number.isNaN(date.getTime())) return "—";

  const diffMs = date.getTime() - Date.now();
  const diffMinutes = Math.round(diffMs / 60000);

  const divisions: [number, Intl.RelativeTimeFormatUnit][] = [
    [60, "minute"],
    [24, "hour"],
    [30, "day"],
    [12, "month"],
    [Infinity, "year"],
  ];

  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

  let duration = diffMinutes;
  let unit: Intl.RelativeTimeFormatUnit = "minute";

  for (const [amount, nextUnit] of divisions) {
    if (Math.abs(duration) < amount) {
      unit = nextUnit;
      break;
    }
    duration = Math.round(duration / amount);
    unit = nextUnit;
  }

  return rtf.format(duration, unit);
}
