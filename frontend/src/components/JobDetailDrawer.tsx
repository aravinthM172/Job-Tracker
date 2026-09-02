import { useEffect, useState } from "react";
import { ChevronDown, ExternalLink, Loader2, X } from "lucide-react";
import { api, type Job } from "../lib/api";
import { accountLabel, formatDate, formatDateTime } from "../lib/format";
import { STATUS_LABELS } from "../lib/format";
import { StatusBadge } from "./StatusBadge";

interface JobDetailDrawerProps {
  jobId: number | null;
  onClose: () => void;
}

export function JobDetailDrawer({ jobId, onClose }: JobDetailDrawerProps) {
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedEventId, setExpandedEventId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setExpandedEventId(null);

    if (jobId == null) {
      setJob(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .getJob(jobId)
      .then((res) => {
        if (!cancelled) setJob(res.job);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load job");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [jobId]);

  const open = jobId != null;

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-40 bg-slate-900/40" onClick={onClose} />
      )}

      <aside
        className={`fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xl transition-transform ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Job Details</h2>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {loading && (
            <div className="flex items-center justify-center py-16 text-slate-400 dark:text-slate-500">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          )}

          {error && !loading && (
            <div className="rounded-lg bg-rose-50 p-3 text-sm text-rose-600 dark:bg-rose-950/40 dark:text-rose-300">{error}</div>
          )}

          {job && !loading && (
            <div className="space-y-6">
              <div>
                <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">{job.company}</p>
                <p className="text-sm text-slate-500 dark:text-slate-400">{job.role}</p>
                <div className="mt-3">
                  <StatusBadge status={job.status} />
                </div>
              </div>

              <dl className="grid grid-cols-2 gap-y-3 text-sm">
                <dt className="text-slate-400 dark:text-slate-500">Applied date</dt>
                <dd className="text-right font-medium text-slate-700 dark:text-slate-300">
                  {formatDate(job.applied_date)}
                </dd>

                <dt className="text-slate-400 dark:text-slate-500">Latest activity</dt>
                <dd className="text-right font-medium text-slate-700 dark:text-slate-300">
                  {formatDate(job.last_activity)}
                </dd>

                <dt className="text-slate-400 dark:text-slate-500">Source account</dt>
                <dd className="text-right font-medium text-slate-700 dark:text-slate-300">
                  {accountLabel(job.source_account)}
                </dd>

                <dt className="text-slate-400 dark:text-slate-500">Emails matched</dt>
                <dd className="text-right font-medium text-slate-700 dark:text-slate-300">{job.email_count}</dd>
              </dl>

              <div>
                <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
                  Email Timeline
                </h3>

                {(!job.events || job.events.length === 0) && (
                  <p className="text-sm text-slate-400 dark:text-slate-500">
                    No emails matched to this application yet.
                  </p>
                )}

                <ol className="space-y-4 border-l border-slate-200 dark:border-slate-800 pl-4">
                  {job.events?.map((event) => (
                    <li key={event.id} className="relative">
                      <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full border-2 border-white bg-slate-400 ring-1 ring-slate-300 dark:border-slate-900 dark:bg-slate-500 dark:ring-slate-700" />
                      <div className="flex items-center justify-between gap-2">
                        <StatusBadge status={event.event_type as Job["status"]} />
                        <span className="whitespace-nowrap text-xs text-slate-400 dark:text-slate-500">
                          {formatDateTime(event.received_date)}
                        </span>
                      </div>
                      <p className="mt-1.5 text-sm font-medium text-slate-800 dark:text-slate-200">
                        {event.subject || "(no subject)"}
                      </p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        From {event.sender || "unknown sender"} ·{" "}
                        {accountLabel(event.account)}
                      </p>
                      <p className="text-xs text-slate-400 dark:text-slate-500">
                        {STATUS_LABELS[event.event_type as Job["status"]] ?? event.event_type}
                      </p>

                      <div className="mt-1 flex items-center gap-3">
                        {event.body && (
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedEventId((current) =>
                                current === event.id ? null : event.id,
                              )
                            }
                            className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
                          >
                            {expandedEventId === event.id ? "Hide email" : "Show full email"}
                            <ChevronDown
                              className={`h-3 w-3 transition-transform ${
                                expandedEventId === event.id ? "rotate-180" : ""
                              }`}
                            />
                          </button>
                        )}

                        {event.web_link && (
                          <a
                            href={event.web_link}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
                          >
                            Open email <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>

                      {expandedEventId === event.id && event.body && (
                        <pre className="mt-2 max-h-80 overflow-y-auto whitespace-pre-wrap break-words rounded-lg bg-slate-50 dark:bg-slate-800/50 p-3 font-sans text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                          {event.body}
                        </pre>
                      )}
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
