import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Card, Empty, ErrorBox, Spinner } from "./ui";

interface Cluster {
  members: { submission_id: number; bidder_name: string }[];
  links: {
    between: number[];
    attributes: { attribute: string; value: string; match: string; confidence: number }[];
  }[];
}

const ATTR_LABELS: Record<string, string> = {
  pan: "PAN",
  gstin: "GSTIN",
  cin: "CIN",
  bank_account: "Bank account",
  phone: "Phone",
  address: "Address",
  signatory_name: "Authorized signatory",
};

export default function CollusionPanel({ tenderId }: { tenderId: number }) {
  const [clusters, setClusters] = useState<Cluster[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .collusion(tenderId)
      .then((r) => setClusters(r.clusters))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [tenderId]);

  return (
    <Card title="Cross-bidder integrity (collusion / duplicate-bidder scan)">
      <p className="mb-3 text-[11px] text-slate-500">
        Exact-match on PAN/GSTIN/CIN/bank/phone + form-aware fuzzy match on address and authorized
        signatory across all submissions on this tender (rule <code>XVERIFY/collusion</code>).
      </p>
      {error && <ErrorBox error={error} />}
      {!clusters && !error && <Spinner label="Scanning bidders…" />}
      {clusters && clusters.length === 0 && (
        <Empty message="No shared-attribute clusters detected — bidders appear independent." />
      )}
      {clusters?.map((c, i) => (
        <div key={i} className="rounded-md border border-amber-300 bg-amber-50 p-3">
          <div className="text-xs font-bold text-amber-900">
            Cluster {i + 1} — {c.members.length} bidders share identifiers
          </div>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {c.members.map((m) => (
              <Link
                key={m.submission_id}
                to={`/submissions/${m.submission_id}`}
                className="rounded bg-white px-2 py-1 text-[11px] font-medium text-gov-blue shadow-sm hover:bg-gov-blue hover:text-white"
              >
                {m.bidder_name}
              </Link>
            ))}
          </div>
          <div className="mt-2 space-y-1">
            {c.links.map((link, j) =>
              link.attributes.map((a, k) => (
                <div key={`${j}-${k}`} className="rounded bg-white/70 px-2 py-1 text-[11px] text-slate-700">
                  <span className="font-bold">{ATTR_LABELS[a.attribute] || a.attribute}:</span>{" "}
                  <span className="font-mono">{a.value}</span>{" "}
                  <span className="rounded bg-amber-100 px-1 text-[10px] font-semibold text-amber-800">
                    {a.match} · conf {Math.round(a.confidence * 100)}%
                  </span>
                  <span className="text-slate-400"> — submissions {link.between.join(" & ")}</span>
                </div>
              )),
            )}
          </div>
        </div>
      ))}
    </Card>
  );
}