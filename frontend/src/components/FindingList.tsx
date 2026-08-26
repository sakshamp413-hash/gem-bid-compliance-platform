import type { Finding } from "../api/client";

const SEV_CLS: Record<string, string> = {
  critical: "bg-red-100 text-red-800 border-red-300",
  high: "bg-orange-100 text-orange-800 border-orange-300",
  medium: "bg-amber-100 text-amber-800 border-amber-300",
  low: "bg-yellow-100 text-yellow-800 border-yellow-300",
  info: "bg-blue-100 text-blue-800 border-blue-300",
};

export default function FindingList({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) return <div className="text-xs text-slate-400">No cross-verification findings.</div>;
  return (
    <ul className="space-y-2">
      {findings.map((f, i) => (
        <li key={i} className="rounded-md border border-slate-200 bg-white p-3">
          <div className="flex items-start gap-2">
            <span className={`rounded border px-1.5 py-0.5 text-[10px] font-bold uppercase ${SEV_CLS[f.severity] || SEV_CLS.info}`}>
              {f.severity}
            </span>
            <div className="flex-1">
              <p className="text-xs font-medium text-slate-800">{f.message}</p>
              <div className="mt-1 flex flex-wrap gap-1 text-[10px] text-slate-400">
                <span className="font-mono">{f.rule_ref}</span>
                <span>·</span>
                <span>conf {Math.round(f.confidence * 100)}%</span>
                <span>·</span>
                <span>{f.evidence.length} evidence item(s)</span>
              </div>
              {f.evidence.length > 0 && (
                <ul className="mt-1.5 space-y-0.5 border-t border-slate-100 pt-1.5">
                  {f.evidence.slice(0, 3).map((e, j) => (
                    <li key={j} className="text-[10px] text-slate-500">
                      <span className="font-medium text-slate-600">{e.source}</span> · {e.field} ={" "}
                      <span className="font-medium">{e.value}</span>
                      {e.quote && <span className="italic"> — {e.quote}</span>}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}