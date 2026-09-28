import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api, SubmissionDetail, Document, Finding } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { usePermissions } from "../auth/usePermissions";
import {
  ActionBadge, Card, ErrorBox, ResultChip, RiskBadge, Spinner,
} from "../components/ui";
import ScoreGauge from "../components/ScoreGauge";
import CheckAccordion from "../components/CheckAccordion";
import DocViewer from "../components/DocViewer";
import FindingList from "../components/FindingList";
import AuditTimeline from "../components/AuditTimeline";

const DOC_LABELS: Record<string, string> = {
  udyam: "Udyam certificate",
  gst_cert: "GST registration certificate",
  pan_card: "PAN card",
  cin: "Certificate of Incorporation (CIN)",
  oem_auth: "OEM authorization letter",
  local_content: "Local-content self-certification",
  epfo: "EPFO registration",
  esic: "ESIC registration",
  startup: "Startup recognition",
  nsic: "NSIC registration",
};

function DecisionModal({
  onClose,
  onConfirm,
  recommendedAction,
  userRole,
}: {
  onClose: () => void;
  onConfirm: (decision: string, justification: string) => Promise<void>;
  recommendedAction: string | null;
  userRole: string;
}) {
  const [decision, setDecision] = useState(
    recommendedAction === "qualify" ? "qualify" : recommendedAction === "disqualify_candidate" ? "disqualify" : "escalate",
  );
  const [justification, setJustification] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isOverride =
    (recommendedAction === "qualify" && decision !== "qualify") ||
    (recommendedAction === "disqualify_candidate" && decision !== "disqualify");

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await onConfirm(decision, justification);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to record decision");
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-lg bg-white p-5 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold text-gov-navy">
            {userRole === "admin" ? "⚠️ Administrative Decision (Override Workflow)" : "Procurement Decision (Human-in-the-Loop)"}
          </h3>
        </div>
        <p className="mt-1 text-[11px] text-slate-500">
          The AI recommends — you decide. Every decision is written to the hash-chained audit log.
        </p>

        {userRole === "admin" && (
          <div className="mt-3 rounded border border-amber-300 bg-amber-50 p-2.5 text-xs text-amber-800">
            <b>⚠️ Administrative Action Warning:</b> You are recording a procurement decision as an <b>Administrator</b>. This bypasses the standard evaluation officer workflow and will be permanently logged under <code className="rounded bg-amber-200/60 px-1 font-mono text-[10px]">admin_decision_override</code> in the tamper-evident audit log.
          </div>
        )}

        {userRole === "officer" && isOverride && (
          <div className="mt-3 rounded border border-purple-200 bg-purple-50 p-2 text-xs text-purple-800">
            <b>* Recommendation Override Notice:</b> Your selected decision deviates from the AI compliance recommendation. Detailed factual justification citing verified evidence is mandatory under GFR Rule 173.
          </div>
        )}

        <div className="mt-4 space-y-3">
          <div>
            <label className="label">Decision</label>
            <select className="input" value={decision} onChange={(e) => setDecision(e.target.value)}>
              <option value="qualify">Qualify</option>
              <option value="disqualify">Disqualify</option>
              <option value="request_docs">Request document from bidder</option>
              <option value="escalate">Escalate for senior review</option>
            </select>
          </div>
          <div>
            <label className="label">
              Justification {isOverride || userRole === "admin" ? "(Mandatory — min 10 chars)" : "(required — min 10 chars)"}
            </label>
            <textarea
              className="input min-h-24"
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              placeholder="State the basis of your decision, referencing the evidence and statutory rules…"
            />
          </div>
          {error && <div className="rounded bg-red-50 p-2 text-xs text-red-700">{error}</div>}
          <div className="flex justify-end gap-2">
            <button className="btn-outline" onClick={onClose}>Cancel</button>
            <button
              className={userRole === "admin" ? "btn-primary bg-amber-700 hover:bg-amber-800" : "btn-primary"}
              disabled={busy || justification.trim().length < 10}
              onClick={submit}
            >
              {busy ? "Recording…" : userRole === "admin" ? "Record Administrative Decision ⚠️" : "Record Decision"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function BidderDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { can } = usePermissions();
  const [detail, setDetail] = useState<SubmissionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeDoc, setActiveDoc] = useState<Document | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [reassessing, setReassessing] = useState(false);
  const [findings, setFindings] = useState<Finding[]>([]);

  const canDecide = can("procurement_decision");
  const isAuditor = user?.role === "auditor";
  const isAdmin = user?.role === "admin";

  const load = () => {
    api
      .submission(Number(id))
      .then((d) => {
        setDetail(d);
        setActiveDoc((cur) => cur || d.documents[0] || null);
      })
      .catch(setError);
  };

  useEffect(load, [id]);

  useEffect(() => {
    api
      .findings(Number(id))
      .then((f) => setFindings(f.findings))
      .catch(() => setFindings([]));
  }, [id]);

  const flaggedDocs = useMemo(
    () =>
      (detail?.documents || []).filter(
        (d) => d.signature_status === "invalid" || d.signature_status === "untrusted" || d.tamper_flags_json?.tampered,
      ),
    [detail],
  );

  if (error) return <ErrorBox error={error} />;
  if (!detail) return <Spinner label="Loading submission…" />;

  const a = detail.assessment;

  return (
    <div className="space-y-4">
      {isAuditor && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-800">
          <b>👁️ Auditor Evidence Review Mode:</b> Segregation of duties active. You have read-only access to bid documents, verification checks, and tamper indicators. Procurement decisions and assessment triggers are restricted to authorized Officers under CVC Guidelines.
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gov-navy">{detail.bidder?.legal_name}</h1>
          <p className="text-xs text-slate-500">
            {detail.tender?.title} · {detail.tender?.buyer_org} · entity: {detail.bidder?.entity_type}
            {detail.bidder?.is_reseller ? " · reseller" : " · manufacturer"}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className="btn-outline"
            onClick={() =>
              api.downloadReport(Number(id)).catch((e) => setError(e instanceof Error ? e.message : String(e)))
            }
          >
            ⬇ Download report (PDF)
          </button>
          {!isAuditor && (
            <button
              className="btn-outline"
              disabled={reassessing}
              onClick={async () => {
                setReassessing(true);
                try {
                  await api.assess(Number(id));
                  load();
                } finally {
                  setReassessing(false);
                }
              }}
            >
              {reassessing ? "Re-assessing…" : "Re-run assessment"}
            </button>
          )}
          {canDecide && (
            <button
              className={isAdmin ? "btn-primary bg-amber-700 hover:bg-amber-800" : "btn-primary"}
              onClick={() => setModalOpen(true)}
            >
              {isAdmin ? "Record Administrative Decision ⚠️" : "Record decision"}
            </button>
          )}
        </div>
      </div>

      {flaggedDocs.length > 0 && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-xs text-red-800">
          <b>{flaggedDocs.length} document(s) failed integrity checks:</b>{" "}
          {flaggedDocs.map((d) => d.file_name).join(", ")} — signature invalid / tampered / untrusted signer.
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        {/* left column: score + recommendation */}
        <div className="space-y-4">
          <Card title="Compliance score">
            <div className="flex items-center justify-center">
              <ScoreGauge score={a?.score ?? 0} />
            </div>
            <div className="mt-2 flex items-center justify-center gap-2">
              <RiskBadge risk={a?.risk_level ?? "unknown"} />
              <ActionBadge action={a?.recommendation_action ?? null} />
            </div>
            {a?.recommendation_confidence != null && (
              <div className="mt-2 text-center text-[11px] text-slate-500">
                recommendation confidence {Math.round(a.recommendation_confidence * 100)}%
              </div>
            )}
          </Card>

          <Card title="AI recommendation">
            {a?.recommendation_text ? (
              <p className="text-xs leading-relaxed text-slate-700">{a.recommendation_text}</p>
            ) : (
              <p className="text-xs text-slate-400">No recommendation yet — run the assessment.</p>
            )}
            {a?.pending_json && a.pending_json.length > 0 && (
              <div className="mt-3 border-t border-slate-100 pt-2">
                <div className="label">Pending requirements</div>
                <ul className="space-y-1">
                  {a.pending_json.map((p, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-[11px] text-slate-600">
                      <ResultChip result={p.result} />
                      <span>{p.requirement}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {a?.model_meta_json && (
              <div className="mt-3 border-t border-slate-100 pt-2 font-mono text-[9px] text-slate-400">
                model_meta: {JSON.stringify((a.model_meta_json as { llm?: { provider?: string; model?: string } }).llm)}
              </div>
            )}
          </Card>

          <Card title="Cross-verification findings (AI)">
            <FindingList findings={findings} />
          </Card>

          <Card title="Officer decisions">
            {detail.decisions.length === 0 && <div className="text-xs text-slate-400">No officer decision recorded yet.</div>}
            <ul className="space-y-2">
              {detail.decisions.map((d) => (
                <li key={d.id} className="rounded border border-slate-200 bg-slate-50 p-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-gov-navy uppercase">{d.decision}</span>
                    {d.overrides_recommendation && (
                      <span className="rounded bg-purple-100 px-1.5 py-0.5 text-[10px] font-semibold text-purple-700">
                        overrides AI recommendation
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-slate-600">{d.justification}</p>
                  <div className="mt-0.5 text-[10px] text-slate-400">{new Date(d.created_at).toLocaleString()}</div>
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Audit trail">
            <AuditTimeline submissionId={Number(id)} />
          </Card>
        </div>

        {/* right column: checks + documents */}
        <div className="space-y-4 lg:col-span-2">
          <Card title={`Compliance checks (${detail.checks.length})`}>
            <CheckAccordion checks={detail.checks} />
          </Card>

          <Card title="Bidder documents">
            {detail.documents.length === 0 && <div className="text-xs text-slate-400">No documents uploaded.</div>}
            <div className="mb-3 flex flex-wrap gap-1.5">
              {detail.documents.map((d) => (
                <button
                  key={d.id}
                  onClick={() => setActiveDoc(d)}
                  className={`rounded border px-2 py-1 text-[11px] font-medium transition-colors ${
                    activeDoc?.id === d.id
                      ? "border-gov-blue bg-gov-blue text-white"
                      : d.signature_status === "invalid" || d.tamper_flags_json?.tampered
                        ? "border-red-300 bg-red-50 text-red-700"
                        : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {DOC_LABELS[d.doc_type] || d.doc_type}
                </button>
              ))}
            </div>
            {activeDoc ? (
              <DocViewer doc={activeDoc} />
            ) : (
              <div className="text-xs text-slate-400">Select a document to inspect.</div>
            )}
          </Card>
        </div>
      </div>

      {modalOpen && (
        <DecisionModal
          onClose={() => setModalOpen(false)}
          recommendedAction={a?.recommendation_action ?? null}
          userRole={user?.role || "officer"}
          onConfirm={async (decision, justification) => {
            await api.decision(Number(id), decision, justification);
            load();
          }}
        />
      )}
    </div>
  );
}