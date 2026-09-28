import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { usePermissions } from "../auth/usePermissions";
import { Card, ErrorBox, Spinner } from "../components/ui";

export default function RulesPage() {
  const { user } = useAuth();
  const { can } = usePermissions();
  const [rules, setRules] = useState<Record<string, unknown> | null>(null);
  const [ruleFile, setRuleFile] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const canDraft = can("rule_drafting");
  const canPublish = can("rule_publishing");

  const load = () => {
    api
      .rules()
      .then((r) => {
        setRules(r.data);
        setRuleFile(r.file);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  };

  useEffect(load, []);

  const saveRules = async () => {
    if (!rules || !canPublish) return;
    setSaving(true);
    setSaved(null);
    setError(null);
    try {
      await api.updateRules(rules);
      setSaved("Rules successfully drafted, saved, and hot-reloaded into the scoring engine.");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gov-navy">Compliance Rules Engine</h1>
          <p className="text-xs text-slate-500">
            Rules are declarative data, not hardcoded logic. Standardized against DPIIT, GFR Rule 173, and GeM procurement manuals.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {canDraft ? (
            <span className="rounded bg-rose-100 px-2 py-1 text-xs font-semibold text-rose-800">
              Admin Authoring Mode (Drafting &amp; Publishing Enabled)
            </span>
          ) : (
            <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
              👁️ Read-Only Rule Visibility ({user?.role?.toUpperCase()})
            </span>
          )}
        </div>
      </div>

      {!canDraft && (
        <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-xs text-blue-800">
          <b>Rule Visibility (Active Policy):</b> As an {user?.role}, you can inspect the evaluation criteria, check weights, and threshold caps. Rule drafting and publishing are restricted to System Administrators.
        </div>
      )}

      {saved && <div className="mb-3 rounded bg-green-50 p-2 text-xs text-green-700">{saved}</div>}
      {error && <ErrorBox error={error} />}
      {!rules && !error && <Spinner label="Loading rules…" />}

      {rules && (
        <Card
          title="Scoring Weights & Threshold Policies"
          actions={
            canPublish && (
              <button className="btn-primary" onClick={saveRules} disabled={saving}>
                {saving ? "Publishing…" : "Save & Publish Rule Set"}
              </button>
            )
          }
        >
          <div className="mb-3 flex items-center justify-between text-[11px] text-slate-500">
            <span>Source: <code className="font-mono">{ruleFile || "rules.yaml"}</code></span>
            <span>Hot-reloads without server restart</span>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <div className="label">Evaluation Weights (JSON / YAML)</div>
              <textarea
                className={`input min-h-80 font-mono text-[11px] ${
                  !canDraft ? "bg-slate-50 text-slate-700 cursor-not-allowed" : ""
                }`}
                value={JSON.stringify(rules.weights, null, 2)}
                readOnly={!canDraft}
                onChange={(e) => {
                  if (!canDraft) return;
                  try {
                    const weights = JSON.parse(e.target.value);
                    setRules({ ...rules, weights });
                  } catch {
                    /* keep parsing safely */
                  }
                }}
              />
              <p className="mt-1 text-[10px] text-slate-400">
                {canDraft
                  ? "Edit weights and click 'Save & Publish Rule Set' to update scoring."
                  : "Read-only view of active compliance check weights."}
              </p>
            </div>

            <div>
              <div className="label">MSME Classification Caps (₹ crore)</div>
              <pre className="min-h-80 overflow-auto rounded bg-slate-900 p-3 text-[11px] text-green-300">
                {JSON.stringify(rules.msme, null, 2)}
              </pre>
              <p className="mt-1 text-[10px] text-slate-400">
                Statutory criteria under MSMED Act (Investment in plant &amp; machinery, annual turnover).
              </p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
