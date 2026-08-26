import { useEffect, useState } from "react";
import type { AuditEntry } from "../api/client";
import { api } from "../api/client";
import { Spinner, Empty } from "./ui";

export default function AuditTimeline({ submissionId }: { submissionId: number }) {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api
      .audit()
      .then((all) => setEntries(all.filter((e) => e.entity.includes(`submission:${submissionId}`))))
      .catch(setError);
  }, [submissionId]);

  if (error) return <div className="text-xs text-red-600">{String(error)}</div>;
  if (!entries) return <Spinner label="Loading audit trail…" />;
  if (entries.length === 0) return <Empty message="No audit events for this submission." />;

  return (
    <ol className="relative space-y-3 border-l border-slate-200 pl-4">
      {entries.map((e) => (
        <li key={e.seq} className="relative">
          <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-gov-blue ring-4 ring-white" />
          <div className="text-xs font-medium text-gov-navy">{e.action}</div>
          <div className="text-[11px] text-slate-500">
            seq {e.seq} · {e.actor} · {new Date(e.created_at).toLocaleString()}
          </div>
          <div className="mt-0.5 font-mono text-[9px] text-slate-400">hash {e.this_hash.slice(0, 20)}…</div>
        </li>
      ))}
    </ol>
  );
}