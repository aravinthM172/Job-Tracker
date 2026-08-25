// Thin client around the FastAPI backend. Types here mirror the real
// response shapes returned by backend/main.py + backend/db.py exactly -
// nothing here is invented; every field is one the backend actually sends.

// Defaults to whatever host the page itself was loaded from (with the
// backend's port) instead of a hardcoded 127.0.0.1 - that way the same
// build works both from localhost and from a phone hitting the PC's
// Tailscale IP/hostname, with no per-device config.
export const API_BASE =
  (import.meta.env.VITE_API_URL as string | undefined) ||
  `http://${window.location.hostname}:8000`;

export type JobStatus =
  | "applied"
  | "application_received"
  | "assessment"
  | "interview"
  | "offer"
  | "rejected"
  | "needs_review";

export const ALL_STATUSES: JobStatus[] = [
  "applied",
  "application_received",
  "assessment",
  "interview",
  "offer",
  "rejected",
  "needs_review",
];

export interface JobEvent {
  id: number;
  event_type: string;
  subject: string;
  sender: string;
  account: string;
  email_id: string | null;
  web_link: string;
  received_date: string | null;
  // Only present on the /jobs/{id} detail response (job.events), not
  // on the job list/dashboard's latest_event - full email text would
  // bloat every list response.
  body?: string;
}

export interface Job {
  id: number;
  company: string;
  role: string;
  job_id: string;
  status: JobStatus;
  source_account: string;
  applied_date: string | null;
  last_activity: string | null;
  email_count: number;
  created_at: string;
  updated_at: string;
  latest_event: JobEvent | null;
  events?: JobEvent[];
}

export interface JobsResponse {
  success: boolean;
  total: number;
  jobs: Job[];
}

export interface JobDetailResponse {
  success: boolean;
  job: Job;
}

export interface DashboardSummary {
  total: number;
  applied: number;
  application_received: number;
  assessment: number;
  interview: number;
  offer: number;
  rejected: number;
  needs_review: number;
}

export interface DashboardResponse {
  success: boolean;
  summary: DashboardSummary;
  jobs: Job[];
}

export type AccountStatus = "connected" | "auth_required" | "error";

export interface AccountInfo {
  exists: boolean;
  size: number;
  token_available: boolean;
  status: AccountStatus;
  message: string | null;
}

export interface SyncStatusResponse {
  success: boolean;
  token_directory: string;
  accounts: Record<string, AccountInfo>;
}

export interface SyncError {
  account: string;
  error: string;
}

export interface SyncResponse {
  success: boolean;
  message: string;
  accounts: { gmail: number; outlook: number; total: number };
  relevant_emails: number;
  source_counts: Record<string, number>;
  total_jobs: number;
  jobs_created: number;
  jobs_updated: number;
  matched: number;
  new_events: number;
  rejected_count: number;
  needs_review_count: number;
  errors: SyncError[];
}

export interface CreateJobPayload {
  company: string;
  role: string;
  job_id?: string;
  applied_date: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!res.ok) {
    let detail = res.statusText;

    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      // ignore, keep statusText
    }

    throw new Error(`${res.status} ${detail}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  getJobs: () => request<JobsResponse>("/jobs"),

  getJob: (id: number) => request<JobDetailResponse>(`/jobs/${id}`),

  createJob: (payload: CreateJobPayload) =>
    request<{ success: boolean; job: Job }>("/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getDashboard: () => request<DashboardResponse>("/dashboard"),

  getSyncStatus: () => request<SyncStatusResponse>("/sync/status"),

  sync: () => request<SyncResponse>("/sync", { method: "POST" }),
};
