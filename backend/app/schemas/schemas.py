"""API schemas (Pydantic v2)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


# --- auth / users ---------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: str = Field(pattern="^(officer|admin|auditor)$")
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    role: str | None = Field(default=None, pattern="^(officer|admin|auditor)$")
    is_active: bool | None = None


# --- tenders --------------------------------------------------------------
class TenderIn(BaseModel):
    gem_ref: str
    title: str
    buyer_org: str
    eligibility_json: dict[str, Any] = Field(default_factory=dict)
    local_content_class_required: str | None = Field(default=None, pattern="^(I|II|None|none)?$")
    msme_only: bool = False
    min_turnover_crore: float | None = None
    required_docs_json: list[str] = Field(default_factory=list)


class TenderOut(TenderIn):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# --- bidders & submissions ------------------------------------------------
class BidderIn(BaseModel):
    legal_name: str
    entity_type: str
    pan: str | None = None
    gstin: str | None = None
    udyam_no: str | None = None
    cin: str | None = None
    epfo_no: str | None = None
    esic_no: str | None = None
    startup_no: str | None = None
    nsic_no: str | None = None


class BidderOut(BidderIn):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SubmissionCreate(BaseModel):
    tender_id: int
    bidder: BidderIn


class SubmissionOut(BaseModel):
    id: int
    tender_id: int
    bidder_id: int
    status: str
    submitted_at: datetime
    tender: "TenderOut | None" = None
    bidder: "BidderOut | None" = None
    assessment: "AssessmentSummary | None" = None

    model_config = {"from_attributes": True}


class AssessmentSummary(BaseModel):
    id: int
    score: float
    risk_level: str
    recommendation_action: str | None
    recommendation_confidence: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- documents ------------------------------------------------------------
class DocumentOut(BaseModel):
    id: int
    submission_id: int
    doc_type: str
    file_name: str
    extracted_json: dict[str, Any] | None
    ocr_confidence: float | None
    ocr_source: str
    signature_status: str
    signature_detail: dict[str, Any] | None
    tamper_flags_json: dict[str, Any] | None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


# --- checks / assessment ---------------------------------------------------
class CheckOut(BaseModel):
    id: int
    check_type: str
    result: str
    confidence: float
    evidence_json: dict[str, Any] | None
    rule_ref: str | None
    portal_response_json: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AssessmentOut(AssessmentSummary):
    pending_json: list[dict] | None
    recommendation_text: str | None
    model_meta_json: dict[str, Any] | None


class SubmissionDetail(SubmissionOut):
    documents: list[DocumentOut] = []
    checks: list[CheckOut] = []
    assessment: AssessmentOut | None = None
    findings: list[dict] = []
    decisions: list["DecisionOut"] = []


class FindingsOut(BaseModel):
    findings: list[dict]
    model_meta: dict[str, Any]


# --- officer decisions ----------------------------------------------------
class DecisionCreate(BaseModel):
    decision: str = Field(pattern="^(qualify|disqualify|request_docs|escalate)$")
    justification: str = Field(min_length=10, max_length=2000)


class DecisionOut(BaseModel):
    id: int
    submission_id: int
    officer_id: int
    decision: str
    overrides_recommendation: bool
    justification: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- audit -----------------------------------------------------------------
class AuditEntryOut(BaseModel):
    seq: int
    actor: str
    action: str
    entity: str
    payload_hash: str
    prev_hash: str
    this_hash: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditVerifyOut(BaseModel):
    valid: bool
    records: int
    first_broken_seq: int | None
    broken_reason: str | None


# --- rules / admin ---------------------------------------------------------
class RuleSetOut(BaseModel):
    data: dict[str, Any]
    file: str


class MessageOut(BaseModel):
    message: str


class HealthOut(BaseModel):
    status: str
    app: str
    database: str
    adapter: str
    llm_provider: str


SubmissionOut.model_rebuild()
SubmissionDetail.model_rebuild()