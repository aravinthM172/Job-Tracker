import { useOutletContext } from "react-router-dom";
import {
  Award,
  Briefcase,
  ClipboardCheck,
  HelpCircle,
  Inbox,
  Layers,
  Users,
  XCircle,
} from "lucide-react";
import type { TrackerContext } from "../App";
import { StatCard } from "../components/StatCard";
import { PipelineFunnel } from "../components/PipelineFunnel";
import { ApplicationsView } from "../components/ApplicationsView";

export function DashboardPage() {
  const { jobs, dashboard, openJob, runSync } = useOutletContext<TrackerContext>();

  const summary = dashboard ?? {
    total: 0,
    applied: 0,
    application_received: 0,
    assessment: 0,
    interview: 0,
    offer: 0,
    rejected: 0,
    needs_review: 0,
  };

  const cards = [
    { label: "Total Applications", value: summary.total, icon: Layers, accent: "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400" },
    { label: "Applied", value: summary.applied, icon: Briefcase, accent: "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400" },
    { label: "Application Received", value: summary.application_received, icon: Inbox, accent: "bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-300" },
    { label: "Assessments", value: summary.assessment, icon: ClipboardCheck, accent: "bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-300" },
    { label: "Interviews", value: summary.interview, icon: Users, accent: "bg-indigo-50 text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-300" },
    { label: "Offers", value: summary.offer, icon: Award, accent: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-300" },
    { label: "Rejected", value: summary.rejected, icon: XCircle, accent: "bg-rose-50 text-rose-600 dark:bg-rose-950/50 dark:text-rose-300" },
    { label: "Needs Review", value: summary.needs_review, icon: HelpCircle, accent: "bg-orange-50 text-orange-600 dark:bg-orange-950/50 dark:text-orange-300" },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
        {cards.map((card) => (
          <StatCard
            key={card.label}
            label={card.label}
            value={card.value}
            icon={card.icon}
            accentClass={card.accent}
          />
        ))}
      </div>

      <PipelineFunnel summary={summary} />

      <div>
        <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-slate-100">All Applications</h2>
        <ApplicationsView jobs={jobs} onSelectJob={(job) => openJob(job.id)} onSync={runSync} />
      </div>
    </div>
  );
}
