import { useState } from "react";
import type { Check } from "../api/client";
import { ResultChip } from "./ui";

const LABELS: Record<string, string> = {
  udyam: "Udyam / MSME",
  gst: "GST (incl. return filing)",
  pan: "PAN / Income-Tax",
  mca: "MCA21 (CIN)",
  local_content: "Make-in-India local content",
  epfo: "EPFO",
  esic: "ESIC",
  startup: "Startup India (DPIIT)",
  nsic: "NSIC",
  oem: "OEM authorization",
  digilocker: "DigiLocker / document integrity",
  blacklist: "Blacklisting / debarment",
};

export default function CheckAccordion({ checks }: { checks: Check[] }) {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <div className="space-y-2">
      {checks.map((c) => {
        const isOpen = open === c.id;
        const ev = (c.evidence_json as { evidence?: { field: string; value: string; quote?: string | null; source: string; doc_type?: string | null }[]; summary?: string } | null) || {};
        return (
          <div key={c.id} className="overflow-hidden rounded-md border border-slate-200 bg-white">
            <button
              className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-slate-50"
              onClick={() => setOpen(isOpen ? null : c.id)}
            >
              <ResultChip result={c.result} />
              <span className="flex-1 text-sm font-medium text-gov-navy">
                {LABELS[c.check_type] || c.check_type}
              </span>
              <span className="text-[11px] text-slate-400">conf {Math.round(c.confidence * 100)}%</span>
              <span className="font-mono text-[10px] text-slate-400">{c.rule_ref}</span>
              <span className="text-slate-400">{isOpen ? "▾" : "▸"}</span>
            </button>
            {isOpen && (
              <div className="border-t border-slate-100 bg-slate-50/60 px-3 py-2.5">
                <div className="text-xs text-slate-600">{ev.summary || "No summary."}</div>
                {ev.evidence && ev.evidence.length > 0 && (
                  <table className="mt-2 w-full text-[11px]">
                    <thead>
                      <tr className="text-left text-slate-400">
                        <th className="py-1 pr-2 font-medium">Source</th>
                        <th className="py-1 pr-2 font-medium">Field</th>
                        <th className="py-1 pr-2 font-medium">Value</th>
                        <th className="py-1 font-medium">Quote / note</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ev.evidence.map((e, i) => (
                        <tr key={i} className="border-t border-slate-100 align-top">
                          <td className="py-1 pr-2 text-slate-500">{e.source}</td>
                          <td className="py-1 pr-2 font-medium text-slate-700">{e.field}</td>
                          <td className="py-1 pr-2 text-slate-700">{e.value}</td>
                          <td className="py-1 text-slate-500">{e.quote || e.doc_type || ""}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {c.portal_response_json && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-[11px] text-gov-blue">
                      Portal response ({(c.portal_response_json as { source?: string }).source})
                    </summary>
                    <pre className="mt-1 max-h-40 overflow-auto rounded bg-slate-900 p-2 text-[10px] text-green-300">
                      {JSON.stringify(c.portal_response_json.data, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}