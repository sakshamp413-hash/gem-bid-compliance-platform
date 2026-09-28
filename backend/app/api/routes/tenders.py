"""Tender management (admin create; all roles read) + F01/F02/F05 endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.audit import append_audit
from app.db.session import get_db
from app.models.tender import Tender
from app.models.user import User
from app.schemas.schemas import TenderIn, TenderOut

router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.get("", response_model=list[TenderOut])
def list_tenders(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Tender).order_by(Tender.id).all()


@router.get("/{tender_id}", response_model=TenderOut)
def get_tender(
    tender_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tender = db.get(Tender, tender_id)
    if tender is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tender not found")
    return tender


@router.post("", response_model=TenderOut)
def create_tender(
    body: TenderIn,
    actor: User = Depends(require_roles("officer", "admin")),
    db: Session = Depends(get_db),
):
    """Tender ingestion — officer and admin can ingest/create tenders."""
    if db.query(Tender).filter(Tender.gem_ref == body.gem_ref).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "gem_ref already exists")
    tender = Tender(**body.model_dump())
    db.add(tender)
    db.commit()
    db.refresh(tender)
    append_audit(db, actor=f"user:{actor.id}", action="create_tender",
                 entity=f"tender:{tender.id}",
                 payload={"gem_ref": tender.gem_ref, "ingested_by_role": actor.role})
    return tender


@router.get("/{tender_id}/collusion")
def tender_collusion(
    tender_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cross-bidder integrity: collusion / duplicate-bidder clusters on a tender."""
    from app.services.collusion import detect_collusion

    return detect_collusion(db, tender_id)


# ── F05: Procurement Integrity Graph Visualizer ──────────────────────────────

@router.get("/{tender_id}/collusion/graph")
def tender_collusion_graph(
    tender_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    D3.js-compatible node-link graph for the Procurement Integrity Graph Visualizer.
    Returns {nodes, links, clusters, metadata} ready for force-directed rendering.
    """
    if db.get(Tender, tender_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tender not found")
    from app.services.collusion import build_collusion_graph
    return build_collusion_graph(db, tender_id)


# ── F01: Tender Requirement Compiler ─────────────────────────────────────────

@router.post("/compile")
def compile_tender_requirements(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    """
    Upload a tender/ATC PDF and receive structured JSON requirement objects.
    Uses deterministic regex+pdfplumber extraction (no LLM).
    Returns list of CompiledRequirement sorted by severity.
    """
    import io

    try:
        import pdfplumber

        pdf_bytes = file.file.read()
        text_parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        text = "\n".join(text_parts)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"PDF extraction failed: {exc}",
        )

    from app.ai.tender_compiler import compile_tender_requirements as _compile

    requirements = _compile(text)
    return {
        "source": file.filename,
        "total_requirements": len(requirements),
        "requirements": [r.to_dict() for r in requirements],
        "source_badge": "● DETERMINISTIC (regex/pdfplumber — no LLM)",
    }


# ── F02: Corrigendum Impact Analyzer ─────────────────────────────────────────

@router.post("/{tender_id}/corrigenda")
def upload_corrigendum(
    tender_id: int,
    corrigendum_number: int = Form(1),
    title: str = Form("Corrigendum"),
    file: UploadFile = File(None),
    text_content: str = Form(None),
    officer: User = Depends(require_roles("officer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Upload a corrigendum PDF or paste raw text. Diffs against original tender
    requirements, identifies affected bidders, persists TenderCorrigendum record.
    Returns {diff, affected_bidder_ids, total_changes, critical_changes}.
    """
    import hashlib
    import io

    if db.get(Tender, tender_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tender not found")

    corrigendum_text = ""
    pdf_hash = None

    if file is not None:
        try:
            import pdfplumber

            pdf_bytes = file.file.read()
            pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
            text_parts = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text_parts.append(t)
            corrigendum_text = "\n".join(text_parts)
        except Exception as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"PDF extraction failed: {exc}",
            )
    elif text_content:
        corrigendum_text = text_content
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Provide either a PDF file or text_content",
        )

    from app.services.corrigendum import analyze_corrigendum

    try:
        result = analyze_corrigendum(
            db=db,
            tender_id=tender_id,
            corrigendum_text=corrigendum_text,
            corrigendum_number=corrigendum_number,
            title=title,
            pdf_hash=pdf_hash,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))

    append_audit(
        db,
        actor=f"user:{officer.id}",
        action="upload_corrigendum",
        entity=f"tender:{tender_id}",
        payload={
            "corrigendum_number": corrigendum_number,
            "total_changes": result["total_changes"],
            "critical_changes": result["critical_changes"],
        },
    )
    return result


@router.get("/{tender_id}/corrigenda")
def list_corrigenda(
    tender_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all corrigenda for a tender (newest first)."""
    if db.get(Tender, tender_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tender not found")
    from app.services.corrigendum import get_corrigenda_for_tender
    return get_corrigenda_for_tender(db, tender_id)