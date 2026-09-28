import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Tender } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { usePermissions } from "../auth/usePermissions";
import { Card, Empty, ErrorBox, Spinner } from "../components/ui";

function IngestTenderModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (t: Tender) => void;
}) {
  const [gemRef, setGemRef] = useState(`GEM/${new Date().getFullYear()}/B/${Math.floor(1000000 + Math.random() * 9000000)}`);
  const [title, setTitle] = useState("");
  const [buyerOrg, setBuyerOrg] = useState("");
  const [msmeOnly, setMsmeOnly] = useState(false);
  const [localContent, setLocalContent] = useState<string>("1");
  const [minTurnover, setMinTurnover] = useState<string>("2.0");
  const [requiredDocs, setRequiredDocs] = useState("udyam, gst_cert, pan_card, local_content");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const docs = requiredDocs.split(",").map((s) => s.trim()).filter(Boolean);
      const created = await api.createTender({
        gem_ref: gemRef,
        title,
        buyer_org: buyerOrg,
        msme_only: msmeOnly,
        local_content_class_required: localContent || null,
        min_turnover_crore: minTurnover ? parseFloat(minTurnover) : null,
        required_docs_json: docs,
      });
      onCreated(created);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to ingest tender");
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-lg rounded-lg bg-white p-5 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-sm font-bold text-gov-navy">Tender Ingestion (GeM / Buyer Portal)</h3>
        <p className="mt-1 text-[11px] text-slate-500">
          Create/ingest a tender specification into the compliance verification pipeline.
        </p>

        {error && <div className="mt-2 rounded bg-red-50 p-2 text-xs text-red-700">{error}</div>}

        <div className="mt-3 space-y-3">
          <div>
            <label className="label">GeM Reference Number</label>
            <input className="input font-mono" value={gemRef} onChange={(e) => setGemRef(e.target.value)} />
          </div>
          <div>
            <label className="label">Tender Title / Scope of Work</label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Supply of Submersible Pumps" />
          </div>
          <div>
            <label className="label">Procuring Entity / Buyer Organization</label>
            <input className="input" value={buyerOrg} onChange={(e) => setBuyerOrg(e.target.value)} placeholder="e.g. Indian Oil Corporation Limited" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Local Content Class Required</label>
              <select className="input" value={localContent} onChange={(e) => setLocalContent(e.target.value)}>
                <option value="1">Class 1 (&gt;= 50%)</option>
                <option value="2">Class 2 (&gt;= 20%)</option>
                <option value="non_local">Non-Local</option>
              </select>
            </div>
            <div>
              <label className="label">Min Turnover (₹ Crore)</label>
              <input className="input" type="number" step="0.5" value={minTurnover} onChange={(e) => setMinTurnover(e.target.value)} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input id="msme-check" type="checkbox" checked={msmeOnly} onChange={(e) => setMsmeOnly(e.target.checked)} />
            <label htmlFor="msme-check" className="text-xs font-medium text-slate-700">MSME Purchase Preference / Reserved</label>
          </div>
          <div>
            <label className="label">Required Statutory Documents (comma-separated)</label>
            <input className="input text-xs" value={requiredDocs} onChange={(e) => setRequiredDocs(e.target.value)} />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button className="btn-outline" onClick={onClose}>Cancel</button>
            <button
              className="btn-primary"
              disabled={busy || !title || !buyerOrg || !gemRef}
              onClick={submit}
            >
              {busy ? "Ingesting…" : "Ingest Tender"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function TendersPage() {
  const { user } = useAuth();
  const { can } = usePermissions();
  const [tenders, setTenders] = useState<Tender[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ingestModalOpen, setIngestModalOpen] = useState(false);

  const canIngest = can("tender_ingestion");

  const load = () => {
    api
      .tenders()
      .then(setTenders)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  };

  useEffect(load, []);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gov-navy">Tenders</h1>
          <p className="text-sm text-slate-500">
            Browse GeM tenders and open their bid submissions for compliance verification.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {canIngest ? (
            <button className="btn-primary" onClick={() => setIngestModalOpen(true)}>
              + Ingest New Tender
            </button>
          ) : (
            <span className="rounded bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
              👁️ View-Only Mode ({user?.role?.toUpperCase()})
            </span>
          )}
        </div>
      </div>

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

      {ingestModalOpen && (
        <IngestTenderModal
          onClose={() => setIngestModalOpen(false)}
          onCreated={(newTender) => {
            setTenders((prev) => (prev ? [newTender, ...prev] : [newTender]));
          }}
        />
      )}
    </div>
  );
}