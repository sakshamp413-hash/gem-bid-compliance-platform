const API = "";

export interface User {
  id: number;
  name: string;
  email: string;
  role: "officer" | "admin" | "auditor";
}

export interface Capabilities {
  tender_ingestion: boolean;
  bid_evidence_review: boolean;
  compliance_score: boolean;
  risk_fraud_indicators: boolean;
  rule_visibility: boolean;
  procurement_decision: boolean;
  decision_override: boolean;
  audit_verification: boolean;
  rule_drafting: boolean;
  rule_publishing: boolean;
  user_management: boolean;
  integration_management: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Tender {
  id: number;
  gem_ref: string;
  title: string;
  buyer_org: string;
  eligibility_json: Record<string, unknown>;
  local_content_class_required: string | null;
  msme_only: boolean;
  min_turnover_crore: number | null;
  required_docs_json: string[];
  created_at: string;
}

export interface Bidder {
  id: number;
  legal_name: string;
  entity_type: string;
  pan?: string | null;
  gstin?: string | null;
  udyam_no?: string | null;
  cin?: string | null;
  is_reseller?: boolean;
}

export interface Assessment {
  id: number;
  score: number;
  risk_level: string;
  recommendation_action: string | null;
  recommendation_confidence: number | null;
  recommendation_text?: string | null;
  pending_json?: { check_type: string; result: string; requirement: string; rule_ref: string }[];
  model_meta_json?: Record<string, unknown> | null;
  created_at: string;
}

export interface Submission {
  id: number;
  tender_id: number;
  bidder_id: number;
  status: string;
  submitted_at: string;
  tender?: Tender | null;
  bidder?: Bidder | null;
  assessment?: Assessment | null;
}

export interface Document {
  id: number;
  submission_id: number;
  doc_type: string;
  file_name: string;
  extracted_json: Record<string, unknown> | null;
  ocr_confidence: number | null;
  ocr_source: string;
  signature_status: string;
  signature_detail: Record<string, unknown> | null;
  tamper_flags_json: Record<string, unknown> | null;
  uploaded_at: string;
}

export interface Check {
  id: number;
  check_type: string;
  result: string;
  confidence: number;
  evidence_json: { evidence?: unknown[]; summary?: string } | null;
  rule_ref: string | null;
  portal_response_json: Record<string, unknown> | null;
  created_at: string;
}

export interface Finding {
  severity: string;
  message: string;
  evidence: { doc_id: number | null; field: string; value: string; quote: string | null; source: string }[];
  rule_ref: string;
  confidence: number;
}

export interface SubmissionDetail extends Submission {
  documents: Document[];
  checks: Check[];
  assessment: Assessment | null;
  findings: Finding[];
  decisions: { id: number; decision: string; overrides_recommendation: boolean; justification: string; created_at: string }[];
}

export interface AuditEntry {
  seq: number;
  actor: string;
  action: string;
  entity: string;
  payload_hash: string;
  prev_hash: string;
  this_hash: string;
  created_at: string;
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let accessToken: string | null = localStorage.getItem("gem_access");
let refreshToken: string | null = localStorage.getItem("gem_refresh");
let currentUser: User | null = JSON.parse(localStorage.getItem("gem_user") || "null");

export function getToken() {
  return accessToken;
}
export function getUser() {
  return currentUser;
}

export function setTokens(t: TokenResponse) {
  accessToken = t.access_token;
  refreshToken = t.refresh_token;
  currentUser = t.user;
  localStorage.setItem("gem_access", t.access_token);
  localStorage.setItem("gem_refresh", t.refresh_token);
  localStorage.setItem("gem_user", JSON.stringify(t.user));
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  currentUser = null;
  localStorage.removeItem("gem_access");
  localStorage.removeItem("gem_refresh");
  localStorage.removeItem("gem_user");
}

async function request<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (res.status === 401 && retry && refreshToken) {
    const ok = await tryRefresh();
    if (ok) return request<T>(path, options, false);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, String(detail));
  }
  return res.json() as Promise<T>;
}

async function tryRefresh(): Promise<boolean> {
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${API}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      clearTokens();
      return false;
    }
    setTokens(await res.json());
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

export const api = {
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request<User>("/auth/me"),
  tenders: () => request<Tender[]>("/tenders"),
  submissions: (tenderId?: number) =>
    request<Submission[]>(`/submissions${tenderId ? `?tender_id=${tenderId}` : ""}`),
  submission: (id: number) => request<SubmissionDetail>(`/submissions/${id}`),
  findings: (id: number) => request<{ findings: Finding[] }>(`/submissions/${id}/findings`),
  assess: (id: number) => request<SubmissionDetail>(`/submissions/${id}/assess`, { method: "POST" }),
  decision: (id: number, decision: string, justification: string) =>
    request(`/submissions/${id}/decisions`, {
      method: "POST",
      body: JSON.stringify({ decision, justification }),
    }),
  audit: () => request<AuditEntry[]>("/audit"),
  auditVerify: () => request<{ valid: boolean; records: number; first_broken_seq: number | null; broken_reason: string | null }>("/audit/verify"),
  collusion: (tenderId: number) =>
    request<{
      clusters: {
        members: { submission_id: number; bidder_name: string }[];
        links: {
          between: number[];
          attributes: { attribute: string; value: string; match: string; confidence: number }[];
        }[];
      }[];
      notes: string[];
    }>(`/tenders/${tenderId}/collusion`),
  downloadReport: async (submissionId: number) => {
    const headers: Record<string, string> = {};
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    const res = await fetch(`${API}/submissions/${submissionId}/report.pdf`, { headers });
    if (!res.ok) throw new Error(`report download failed (${res.status})`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `compliance_report_submission_${submissionId}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
  stats: () => request<Record<string, unknown>>("/admin/stats"),
  rules: () => request<{ data: Record<string, unknown>; file: string }>("/admin/rules"),
  updateRules: (data: Record<string, unknown>) =>
    request<{ data: Record<string, unknown> }>("/admin/rules", { method: "PUT", body: JSON.stringify(data) }),
  users: () => request<User[]>("/users"),
  createUser: (body: { name: string; email: string; role: string; password: string }) =>
    request<User>("/users", { method: "POST", body: JSON.stringify(body) }),
  uploadDocument: (submissionId: number, docType: string, file: File) => {
    const form = new FormData();
    form.append("submission_id", String(submissionId));
    form.append("doc_type", docType);
    form.append("file", file);
    const headers: Record<string, string> = {};
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    return fetch(`${API}/documents`, { method: "POST", body: form, headers });
  },
  createTender: (body: {
    gem_ref: string;
    title: string;
    buyer_org: string;
    eligibility_json?: Record<string, unknown>;
    local_content_class_required?: string | null;
    msme_only?: boolean;
    min_turnover_crore?: number | null;
    required_docs_json?: string[];
  }) => request<Tender>("/tenders", { method: "POST", body: JSON.stringify(body) }),
  integrations: () =>
    request<{
      active_adapter: string;
      adapter_class: string;
      status: string;
      integrations: {
        id: string;
        name: string;
        authority: string;
        status: string;
        endpoint_type: string;
        avg_latency_ms: number;
        cached_records: number;
      }[];
    }>("/admin/integrations"),
  testIntegrations: () =>
    request<{
      status: string;
      timestamp: string;
      tests_passed: number;
      tests_failed: number;
      average_ping_ms: number;
    }>("/admin/integrations/test", { method: "POST" }),
  myPermissions: () =>
    request<{ role: string; capabilities: Capabilities }>("/users/me/permissions"),
};