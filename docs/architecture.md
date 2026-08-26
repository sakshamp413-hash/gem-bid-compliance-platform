# Architecture

See the README for the full Mermaid diagram. This file documents module responsibilities.

## Backend (`backend/app`)

```
core/         config (pydantic-settings), JWT+bcrypt security, Fernet field crypto,
              PII-redacting logging, rate limiter, Indian ID validators
db/           engine/session, encrypted-string column type, hash-chained audit
models/       SQLAlchemy 2 models: users, tenders, bidders, bid_submissions,
              documents, verification_checks, compliance_assessments,
              officer_decisions, audit_log
schemas/      Pydantic v2 API schemas
api/          deps (auth/RBAC/rate-limit) + route modules (auth, users, tenders,
              submissions, documents, decisions, audit, findings, admin)
services/
  checks/     12 compliance check modules (udyam, gst, pan, mca, local_content,
              epfo, esic, startup, nsic, oem, digilocker, blacklist)
  pipeline.py orchestration: checklist → checks → AI cross-verify → score → recommendation
  document_service.py  upload → extract → signature verify → tamper detect
ai/           LLMClient (OpenAI-compat/Ollama/offline), OCR, extraction (per-doc
              schema + bbox), cross-verification, recommendation
security/     PKI signature verification (pyHanko), PDF tamper detection, demo CA
rules/        rule engine (rules are data: rules.yaml), weighted scoring + risk
integration/  GovPortalAdapter seam + MockGovPortal + APISetu/GSP/DigiLocker stubs
seed.py       demo users/tender/5 bidders + full pipeline run
```

## Pipeline (single assessment)

```
documents (extracted + signed/tamper analyzed)
  → applicable checklist from (tender, bidder) + rule set
  → per-check: format/validity → mock-portal cross-check → cross-document
    consistency → evidence-linked CheckOutput
  → AI cross-verification (deterministic rules + optional LLM pass)
  → weighted score (pass=1, flag=0.5, fail=0 × weight × confidence)
  → risk: high if hard-fail/forgery/debarment; medium if flags/score<80
  → pending requirements + plain-language recommendation (Qualify /
    Needs-Review / Disqualify-candidate)
  → persist + hash-chained audit entries
```

## Frontend (`frontend/src`)

```
api/client.ts      typed fetch wrapper, token refresh, RBAC-aware
auth/              AuthContext (role-aware routing)
components/        Layout, ScoreGauge, CheckAccordion, DocViewer (split view with
                   field bbox highlights), FindingList, AuditTimeline, badges
pages/             Login, Tenders, Submissions, BidderDetail (hero), Admin, Auditor
```

## Data generation (`data/generate.py`)

Renders government-style PDFs with reportlab → signs them with pyHanko against the demo CA →
forges FraudFillers' GST certificate (incremental metadata update + full re-save) → writes the
seeded registry (`data/mock_portal.json`). Deterministic and re-runnable.