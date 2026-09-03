import type { DashboardSummary } from "../lib/api";

// A read of how applications move through the pipeline. Each stage
// counts jobs that reached *at least* that stage, so the bars taper
// as the funnel narrows. "Received" folds in every later stage too
// (a job now in interview was obviously received).

interface PipelineFunnelProps {
  summary: DashboardSummary;
}

export function PipelineFunnel({ summary }: PipelineFunnelProps) {
  const reached = {
    applied: summary.total,
    received:
      summary.application_received +
      summary.assessment +
      summary.interview +
      summary.offer,
    assessment: summary.assessment + summary.interview + summary.offer,
    interview: summary.interview + summary.offer,
    offer: summary.offer,
  };

  const stages = [
    { label: "Applied", value: reached.applied, bar: "bg-slate-400 dark:bg-slate-500" },
    { label: "Application received", value: reached.received, bar: "bg-blue-400 dark:bg-blue-500" },
    { label: "Assessment", value: reached.assessment, bar: "bg-amber-400 dark:bg-amber-500" },
    { label: "Interview", value: reached.interview, bar: "bg-indigo-400 dark:bg-indigo-500" },
    { label: "Offer", value: reached.offer, bar: "bg-emerald-400 dark:bg-emerald-500" },
  ];

  const max = Math.max(1, ...stages.map((s) => s.value));

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          Pipeline
        </h2>
        <span className="text-xs text-slate-400 dark:text-slate-500">
          {summary.rejected} rejected · {summary.needs_review} to review
        </span>
      </div>

      <div className="mt-4 space-y-3">
        {stages.map((stage) => {
          const prev = stages[stages.indexOf(stage) - 1];
          const conv =
            prev && prev.value > 0
              ? Math.round((stage.value / prev.value) * 100)
              : null;
          return (
            <div key={stage.label} className="flex items-center gap-2 text-sm sm:gap-3">
              <span className="w-24 shrink-0 truncate text-slate-500 dark:text-slate-400 sm:w-40">
                {stage.label}
              </span>
              <div className="flex h-6 flex-1 items-center overflow-hidden rounded bg-slate-100 dark:bg-slate-800">
                <div
                  className={`h-full rounded ${stage.bar}`}
                  style={{ width: `${(stage.value / max) * 100}%` }}
                />
              </div>
              <span className="w-8 shrink-0 text-right font-semibold text-slate-900 dark:text-slate-100">
                {stage.value}
              </span>
              <span className="hidden w-12 shrink-0 text-right text-xs text-slate-400 dark:text-slate-500 sm:inline">
                {conv == null ? "" : `${conv}%`}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
