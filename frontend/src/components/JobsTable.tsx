import { Eye, Mail } from "lucide-react";
import type { Job } from "../lib/api";
import { accountLabel, formatDate, relativeTime } from "../lib/format";
import { CompanyLogo } from "./CompanyLogo";
import { StatusBadge } from "./StatusBadge";

interface JobsTableProps {
  jobs: Job[];
  onSelect: (job: Job) => void;
}

export function JobsTable({ jobs, onSelect }: JobsTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
      <table className="w-full min-w-[860px] text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Company</th>
            <th className="px-4 py-3">Job Title</th>
            <th className="px-4 py-3">Applied Date</th>
            <th className="px-4 py-3">Latest Activity</th>
            <th className="px-4 py-3">Source Account</th>
            <th className="px-4 py-3 text-right">Emails</th>
            <th className="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {jobs.map((job) => (
            <tr
              key={job.id}
              onClick={() => onSelect(job)}
              className="cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/60"
            >
              <td className="px-4 py-3">
                <StatusBadge status={job.status} />
              </td>
              <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                <span className="flex items-center gap-2.5">
                  <CompanyLogo
                    company={job.company}
                    url={job.job_id}
                    className="h-7 w-7"
                  />
                  <span className="truncate">{job.company}</span>
                </span>
              </td>
              <td className="max-w-[240px] truncate px-4 py-3 text-slate-600 dark:text-slate-400" title={job.role}>
                {job.role}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-slate-500 dark:text-slate-400">
                {formatDate(job.applied_date)}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-slate-500 dark:text-slate-400">
                {relativeTime(job.last_activity)}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-slate-500 dark:text-slate-400">
                {accountLabel(job.source_account)}
              </td>
              <td className="px-4 py-3 text-right text-slate-500 dark:text-slate-400">
                <span className="inline-flex items-center gap-1">
                  <Mail className="h-3.5 w-3.5" />
                  {job.email_count}
                </span>
              </td>
              <td className="px-4 py-3 text-right">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelect(job);
                  }}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 dark:border-slate-800 px-2.5 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  <Eye className="h-3.5 w-3.5" />
                  View
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
