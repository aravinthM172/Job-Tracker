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
    { label: "Total Applications", value: summary.total, icon: Layers, accent: "bg-slate-100 text-slate-600" },
    { label: "Applied", value: summary.applied, icon: Briefcase, accent: "bg-slate-100 text-slate-600" },
    { label: "Application Received", value: summary.application_received, icon: Inbox, accent: "bg-blue-50 text-blue-600" },
    { label: "Assessments", value: summary.assessment, icon: ClipboardCheck, accent: "bg-amber-50 text-amber-600" },
    { label: "Interviews", value: summary.interview, icon: Users, accent: "bg-indigo-50 text-indigo-600" },
    { label: "Offers", value: summary.offer, icon: Award, accent: "bg-emerald-50 text-emerald-600" },
    { label: "Rejected", value: summary.rejected, icon: XCircle, accent: "bg-rose-50 text-rose-600" },
    { label: "Needs Review", value: summary.needs_review, icon: HelpCircle, accent: "bg-orange-50 text-orange-600" },
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

      <div>
        <h2 className="mb-3 text-sm font-semibold text-slate-900">All Applications</h2>
        <ApplicationsView jobs={jobs} onSelectJob={(job) => openJob(job.id)} onSync={runSync} />
      </div>
    </div>
  );
}
