import type { ReactNode } from "react";

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-slate-500">
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-gov-blue border-t-transparent" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function Empty({ message = "Nothing here yet." }: { message?: string }) {
  return <div className="py-10 text-center text-sm text-slate-400">{message}</div>;
}

export function ErrorBox({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
      {msg}
    </div>
  );
}

export function Card({ title, children, actions }: { title?: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <div className="card">
      {(title || actions) && (
        <div className="mb-3 flex items-center justify-between">
          {title && <h3 className="text-sm font-semibold text-gov-navy">{title}</h3>}
          {actions}
        </div>
      )}
      {children}
    </div>
  );
}

export function RiskBadge({ risk }: { risk: string }) {
  const map: Record<string, string> = {
    low: "bg-green-100 text-green-800 border-green-300",
    medium: "bg-amber-100 text-amber-800 border-amber-300",
    high: "bg-red-100 text-red-800 border-red-300",
    unknown: "bg-slate-100 text-slate-600 border-slate-300",
  };
  return (
    <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase ${map[risk] || map.unknown}`}>
      {risk}
    </span>
  );
}

export function ResultChip({ result }: { result: string }) {
  const map: Record<string, string> = {
    pass: "bg-green-100 text-green-800",
    flag: "bg-amber-100 text-amber-800",
    fail: "bg-red-100 text-red-800",
    na: "bg-slate-100 text-slate-500",
  };
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-semibold uppercase ${map[result] || map.na}`}>{result}</span>
  );
}

export function SigBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    valid: { label: "Signature valid", cls: "bg-green-100 text-green-800" },
    invalid: { label: "Signature INVALID", cls: "bg-red-100 text-red-800" },
    untrusted: { label: "Untrusted signer", cls: "bg-amber-100 text-amber-800" },
    not_signed: { label: "Not digitally signed", cls: "bg-slate-100 text-slate-600" },
  };
  const m = map[status] || map.not_signed;
  return <span className={`rounded px-2 py-0.5 text-xs font-semibold ${m.cls}`}>{m.label}</span>;
}

export function TamperBadge({ tampered }: { tampered: boolean | undefined }) {
  if (!tampered) return <span className="rounded bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-800">No tamper flags</span>;
  return <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-800">⚠ Tampered — modified after signing</span>;
}

export function ActionBadge({ action }: { action: string | null }) {
  if (!action) return null;
  const map: Record<string, string> = {
    qualify: "bg-green-100 text-green-800",
    needs_review: "bg-amber-100 text-amber-800",
    disqualify_candidate: "bg-red-100 text-red-800",
  };
  const label =
    action === "qualify" ? "Recommend: Qualify" : action === "needs_review" ? "Recommend: Needs Review" : "Recommend: Disqualify";
  return <span className={`rounded px-2 py-0.5 text-xs font-semibold ${map[action] || ""}`}>{label}</span>;
}