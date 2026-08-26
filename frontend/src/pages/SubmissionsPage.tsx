import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Submission, Tender } from "../api/client";
import { Card, Empty, ErrorBox, RiskBadge, Spinner, ActionBadge } from "../components/ui";
import CollusionPanel from "../components/CollusionPanel";

export default function SubmissionsPage() {
  const { tenderId } = useParams();
  const [tender, setTender] = useState<Tender | null>(null);
  const [subs, setSubs] = useState<Submission[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    if (tenderId) {
      api.tenders().then((ts) => setTender(ts.find((t) => t.id === Number(tenderId)) || null));
    }
    api
      .submissions(tenderId ? Number(tenderId) : undefined)
      .then(setSubs)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [tenderId]);

  const filtered = useMemo(() => {
    if (!subs) return null;
    if (filter === "all") return subs;
    if (filter === "assessed") return subs.filter((s) => s.assessment);
    return subs.filter((s) => s.assessment?.risk_level === filter);
  }, [subs, filter]);

  const scoreColor = (score: number) =>
    score >= 80 ? "text-green-700" : score >= 50 ? "text-amber-700" : "text-red-700";

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gov-navy">
            {tender ? tender.title : "Bid Submissions"}
          </h1>
          {tender && <p className="text-xs text-slate-500">{tender.buyer_org} · {tender.gem_ref}</p>}
        </div>
        <select className="input w-auto" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="all">All</option>
          <option value="assessed">Assessed</option>
          <option value="low">Risk: Low</option>
          <option value="medium">Risk: Medium</option>
          <option value="high">Risk: High</option>
        </select>
      </div>
      {error && <ErrorBox error={error} />}
      {!filtered && !error && <Spinner />}
      {filtered && filtered.length === 0 && <Empty message="No submissions match." />}
      {tenderId && (
        <div className="mb-4">
          <CollusionPanel tenderId={Number(tenderId)} />
        </div>
      )}
      <div className="card overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
              <th className="px-4 py-2.5">Bidder</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5">Score</th>
              <th className="px-4 py-2.5">Risk</th>
              <th className="px-4 py-2.5">Recommendation</th>
              <th className="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {filtered?.map((s) => (
              <tr key={s.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-4 py-2.5 font-medium text-gov-navy">{s.bidder?.legal_name}</td>
                <td className="px-4 py-2.5 text-xs capitalize text-slate-500">{s.status}</td>
                <td className="px-4 py-2.5">
                  {s.assessment ? (
                    <span className={`text-base font-bold ${scoreColor(s.assessment.score)}`}>
                      {s.assessment.score.toFixed(1)}
                    </span>
                  ) : (
                    <span className="text-xs text-slate-400">—</span>
                  )}
                </td>
                <td className="px-4 py-2.5">
                  {s.assessment && <RiskBadge risk={s.assessment.risk_level} />}
                </td>
                <td className="px-4 py-2.5">
                  {s.assessment && <ActionBadge action={s.assessment.recommendation_action} />}
                </td>
                <td className="px-4 py-2.5 text-right">
                  <Link
                    to={`/submissions/${s.id}`}
                    className="rounded bg-gov-blue px-3 py-1 text-xs font-medium text-white hover:bg-gov-navy"
                  >
                    Open
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}