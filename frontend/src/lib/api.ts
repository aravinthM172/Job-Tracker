// Thin client around the FastAPI backend. Types here mirror the real
// response shapes returned by backend/main.py + backend/db.py exactly -
// nothing here is invented; every field is one the backend actually sends.

// In dev (Vite dev server on :5173), the backend is a separate
// process on :8000 - default to whatever host the page loaded from
// so this also works from a phone hitting the PC's Tailscale IP. In
// a production build, main.py serves the built frontend itself, so
// the API is same-origin - "" makes fetch() resolve relative to the
// page's own URL instead of assuming a :8000 backend exists.
export const API_BASE =
  (import.meta.env.VITE_API_URL as string | undefined) ??
  (import.meta.env.DEV ? `http://${window.location.hostname}:8000` : "");

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

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    // the session cookie is httpOnly; in dev the frontend and API are
    // different origins, so it only rides along with credentials set.
    credentials: "include",
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

    // a 401 on anything other than the login call itself means the
    // session lapsed - let the app fall back to the login screen
    if (res.status === 401 && !path.startsWith("/api/auth/login")) {
      window.dispatchEvent(new Event("auth-expired"));
    }

    throw new ApiError(res.status, `${res.status} ${detail}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type Role = "owner" | "viewer";

export interface AuthUser {
  username: string;
  role: Role;
}

export interface ManagedUser {
  id: number;
  username: string;
  role: Role;
  is_disabled: boolean;
  is_demo: boolean;
  created_at: string;
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

  auth: {
    me: () => request<AuthUser>("/api/auth/me"),

    login: (username: string, password: string) =>
      request<AuthUser>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      }),

    logout: () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),

    listUsers: () => request<ManagedUser[]>("/api/auth/users"),

    createUser: (username: string, password: string) =>
      request<ManagedUser>("/api/auth/users", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      }),

    deleteUser: (id: number) =>
      request<void>(`/api/auth/users/${id}`, { method: "DELETE" }),
  },
};
