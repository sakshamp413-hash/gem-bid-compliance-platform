import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Tender } from "../api/client";
import { Card, Empty, ErrorBox, Spinner } from "../components/ui";

export default function TendersPage() {
  const [tenders, setTenders] = useState<Tender[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .tenders()
      .then(setTenders)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  return (
    <div>
      <h1 className="mb-1 text-xl font-bold text-gov-navy">Tenders</h1>
      <p className="mb-4 text-sm text-slate-500">
        Browse GeM tenders and open their bid submissions for compliance verification.
      </p>
      {error && <ErrorBox error={error} />}
      {!tenders && !error && <Spinner />}
      {tenders && tenders.length === 0 && <Empty message="No tenders yet." />}
      <div className="grid gap-4 md:grid-cols-2">
        {tenders?.map((t) => (
          <Link key={t.id} to={`/tenders/${t.id}`} className="card block transition-shadow hover:shadow-md">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-gov-blue">{t.title}</div>
                <div className="mt-0.5 text-xs text-slate-500">{t.buyer_org}</div>
              </div>
              <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[11px] text-slate-600">
                {t.gem_ref}
              </span>
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
              {t.local_content_class_required && (
                <span className="rounded bg-green-100 px-2 py-0.5 font-medium text-green-800">
                  Local content Class {t.local_content_class_required}
                </span>
              )}
              {t.msme_only && (
                <span className="rounded bg-blue-100 px-2 py-0.5 font-medium text-blue-800">MSME-only</span>
              )}
              {t.min_turnover_crore != null && (
                <span className="rounded bg-slate-100 px-2 py-0.5 text-slate-600">
                  Min turnover ₹{t.min_turnover_crore} Cr
                </span>
              )}
              <span className="rounded bg-slate-100 px-2 py-0.5 text-slate-600">
                Docs: {t.required_docs_json.join(", ")}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}