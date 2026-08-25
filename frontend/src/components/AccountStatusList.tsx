import { AlertCircle, CheckCircle2, HelpCircle, Mail } from "lucide-react";
import type { AccountInfo, AccountStatus } from "../lib/api";
import { ACCOUNT_STATUS_CLASSES, ACCOUNT_STATUS_LABELS } from "../lib/format";

const ACCOUNT_ORDER = [
  { key: "gmail_1.json", label: "Gmail 1" },
  { key: "gmail_2.json", label: "Gmail 2" },
  { key: "gmail_3.json", label: "Gmail 3" },
  { key: "gmail_4.json", label: "Gmail 4" },
  { key: "outlook_1.json", label: "Outlook" },
];

function StatusIcon({ status }: { status: AccountStatus }) {
  if (status === "connected") return <CheckCircle2 className="h-4 w-4" />;
  if (status === "error") return <AlertCircle className="h-4 w-4" />;
  return <HelpCircle className="h-4 w-4" />;
}

interface AccountStatusListProps {
  accounts: Record<string, AccountInfo> | null;
}

export function AccountStatusList({ accounts }: AccountStatusListProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="divide-y divide-slate-100">
        {ACCOUNT_ORDER.map(({ key, label }) => {
          const info = accounts?.[key];
          const status: AccountStatus = info?.status ?? "auth_required";

          return (
            <div key={key} className="flex items-center justify-between gap-4 px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
                  <Mail className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-900">{label}</p>
                  {info?.message && (
                    <p className="max-w-sm truncate text-xs text-slate-400" title={info.message}>
                      {info.message}
                    </p>
                  )}
                </div>
              </div>

              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset ${ACCOUNT_STATUS_CLASSES[status]}`}
              >
                <StatusIcon status={status} />
                {ACCOUNT_STATUS_LABELS[status]}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
