import type { JobStatus } from "../lib/api";
import { STATUS_BADGE_CLASSES, STATUS_DOT_CLASSES, STATUS_LABELS } from "../lib/format";

export function StatusBadge({ status }: { status: JobStatus }) {
  const badgeClass = STATUS_BADGE_CLASSES[status] ?? STATUS_BADGE_CLASSES.needs_review;
  const dotClass = STATUS_DOT_CLASSES[status] ?? STATUS_DOT_CLASSES.needs_review;
  const label = STATUS_LABELS[status] ?? status;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset whitespace-nowrap ${badgeClass}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dotClass}`} />
      {label}
    </span>
  );
}
