import { useEffect, useState } from "react";
import { api, AuditEntry } from "../api/client";
import { Card, ErrorBox, Spinner } from "../components/ui";

export default function AuditorPage() {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [verify, setVerify] = useState<{ valid: boolean; records: number; first_broken_seq: number | null; broken_reason: string | null } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const load = () => {
    api
      .audit()
      .then(setEntries)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
    api
      .auditVerify()
      .then(setVerify)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  };
  useEffect(load, []);

  const runVerify = async () => {
    setRunning(true);
    try {
      setVerify(await api.auditVerify());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <h1 className="mb-1 text-xl font-bold text-gov-navy">Audit Integrity</h1>
      <p className="mb-4 text-sm text-slate-500">
        Tamper-evident, hash-chained audit log. <code className="rounded bg-slate-100 px-1">/audit/verify</code> recomputes the
        chain and reports the first broken link if any record was modified.
      </p>
      {error && <ErrorBox error={error} />}

      <Card
        title="Chain integrity"
        actions={
          <button className="btn-outline" onClick={runVerify} disabled={running}>
            {running ? "Recomputing…" : "Re-verify chain"}
          </button>
        }
      >
        {!verify && <Spinner />}
        {verify && (
          <div className="flex flex-wrap items-center gap-3">
            <span
              className={`rounded-full px-3 py-1 text-sm font-bold ${
                verify.valid ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
              }`}
            >
              {verify.valid ? "CHAIN INTACT" : "CHAIN BROKEN"}
            </span>
            <span className="text-xs text-slate-600">{verify.records} records chained</span>
            {!verify.valid && verify.first_broken_seq != null && (
              <span className="rounded bg-red-50 px-2 py-1 text-xs text-red-700">
                First broken link: seq {verify.first_broken_seq} — {verify.broken_reason}
              </span>
            )}
          </div>
        )}
      </Card>

      <div className="mt-4">
        <Card title={`Audit records (${entries?.length ?? 0})`}>
          {!entries && <Spinner />}
          {entries && (
            <div className="max-h-[560px] overflow-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-slate-50">
                  <tr className="text-left text-[10px] uppercase text-slate-400">
                    <th className="px-2 py-1.5">Seq</th>
                    <th className="px-2 py-1.5">Time</th>
                    <th className="px-2 py-1.5">Actor</th>
                    <th className="px-2 py-1.5">Action</th>
                    <th className="px-2 py-1.5">Entity</th>
                    <th className="px-2 py-1.5">Hash (prev)</th>
                    <th className="px-2 py-1.5">Hash (this)</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((e) => (
                    <tr key={e.seq} className="border-t border-slate-100 font-mono">
                      <td className="px-2 py-1">{e.seq}</td>
                      <td className="px-2 py-1 text-slate-500">{new Date(e.created_at).toLocaleTimeString()}</td>
                      <td className="px-2 py-1">{e.actor}</td>
                      <td className="px-2 py-1 font-sans">{e.action}</td>
                      <td className="px-2 py-1">{e.entity}</td>
                      <td className="px-2 py-1 text-slate-400">{e.prev_hash.slice(0, 12)}…</td>
                      <td className="px-2 py-1 text-slate-400">{e.this_hash.slice(0, 12)}…</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}