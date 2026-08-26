"""Document routes: upload, list, download, render page image."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.schemas import DocumentOut
from app.services.document_service import process_uploaded_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut)
def upload_document(
    submission_id: int = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(require_roles("officer", "admin")),
    db: Session = Depends(get_db),
):
    content = file.file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    return process_uploaded_document(
        db, submission_id, doc_type, file.filename or "document.pdf", content,
        actor=f"user:{user.id}",
    )


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return doc


@router.get("/{document_id}/file")
def download_document(
    document_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    try:
        content = open(doc.file_path, "rb").read()
    except OSError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File missing on disk")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{doc.file_name}"'},
    )


@router.get("/{document_id}/page/{page_no}.png")
def render_page(
    document_id: int,
    page_no: int,
    scale: float = 2.0,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Render a PDF page to PNG (pypdfium2) for the split-view viewer."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(doc.file_path)
        n = len(pdf)
        if page_no < 1 or page_no > n:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Page {page_no} out of range (1..{n})")
        page = pdf[page_no - 1]
        bitmap = page.render(scale=scale)
        pil = bitmap.to_pil()
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"render failed: {exc}")