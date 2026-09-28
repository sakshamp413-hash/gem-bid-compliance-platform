/**
 * usePermissions — fetches the RBAC capability map from /users/me/permissions
 * and provides a `can(capability)` helper.
 *
 * Usage:
 *   const { can, caps, loading } = usePermissions();
 *   if (can("procurement_decision")) { ... }
 */
import { useEffect, useState } from "react";
import { api, Capabilities } from "../api/client";

const DEFAULTS: Capabilities = {
  tender_ingestion: false,
  bid_evidence_review: false,
  compliance_score: false,
  risk_fraud_indicators: false,
  rule_visibility: false,
  procurement_decision: false,
  decision_override: false,
  audit_verification: false,
  rule_drafting: false,
  rule_publishing: false,
  user_management: false,
  integration_management: false,
};

export function usePermissions() {
  const [caps, setCaps] = useState<Capabilities>(DEFAULTS);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .myPermissions()
      .then((res) => setCaps(res.capabilities))
      .catch(() => setCaps(DEFAULTS))
      .finally(() => setLoading(false));
  }, []);

  const can = (capability: keyof Capabilities): boolean => caps[capability] ?? false;

  return { can, caps, loading };
}
