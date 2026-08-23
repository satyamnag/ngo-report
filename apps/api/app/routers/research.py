"""Research sources, document uploads, and the agentic report build.

The user grants the agent read access to their public sources (website + social)
and uploads research documents. The OpenAI Agents SDK agent then researches and
builds the content plan, which is merged into the project.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import (
    Organization,
    Project,
    ProjectDocument,
    ProjectSource,
    Template,
    User,
    record_audit,
)
from ..schemas import DocumentOut, SourceOut, SourceUpdate
from ..security import get_current_user
from ..services.extract import extract_text
from ..storage import get_storage

router = APIRouter(prefix="/api/projects", tags=["research"])

PLATFORMS = ["website", "facebook", "instagram", "twitter", "linkedin", "youtube"]

ALLOWED_UPLOADS = {
    "text/plain": "txt",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}


def _get_org(db: Session, user: User) -> Organization:
    org = db.query(Organization).filter_by(user_id=user.id).first()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


def _get_project(db: Session, org: Organization, project_id: str) -> Project:
    project = db.query(Project).filter_by(id=project_id, org_id=org.id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ---------- Sources ----------
@router.put("/{project_id}/sources", response_model=list[SourceOut])
def save_sources(
    project_id: str,
    payload: SourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)

    urls = {
        "website": payload.website,
        "facebook": payload.facebook,
        "instagram": payload.instagram,
        "twitter": payload.twitter,
        "linkedin": payload.linkedin,
        "youtube": payload.youtube,
    }
    for platform in PLATFORMS:
        source = (
            db.query(ProjectSource)
            .filter_by(project_id=project.id, platform=platform)
            .first()
        )
        value = (urls.get(platform) or "").strip() or None
        if source is None:
            source = ProjectSource(project_id=project.id, platform=platform, url=value)
            db.add(source)
        elif value != source.url:
            source.url = value
            source.status = "pending"
            source.fetched_text = None
            source.error = None
            source.fetched_at = None
    db.commit()
    record_audit(db, "sources.saved", user_id=current_user.id, project_id=project.id)
    return _source_rows(db, project.id)


@router.get("/{project_id}/sources", response_model=list[SourceOut])
def list_sources(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)
    return _source_rows(db, project.id)


def _source_rows(db: Session, project_id: str) -> list[SourceOut]:
    rows = (
        db.query(ProjectSource)
        .filter_by(project_id=project_id)
        .order_by(ProjectSource.platform)
        .all()
    )
    out = []
    for row in rows:
        out.append(
            SourceOut(
                platform=row.platform,
                url=row.url,
                status=row.status,
                error=row.error,
                fetched_chars=len(row.fetched_text) if row.fetched_text else None,
            )
        )
    return out


@router.post("/{project_id}/sources/fetch", response_model=list[SourceOut])
def fetch_sources(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch every granted source (read-only, SSRF-guarded) and store its text."""
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)

    from ..services.sources import FetchError, fetch_platform

    sources = (
        db.query(ProjectSource)
        .filter_by(project_id=project.id)
        .order_by(ProjectSource.platform)
        .all()
    )
    for source in sources:
        if not source.url:
            source.status = "skipped"
            source.fetched_text = None
            source.error = None
            continue
        try:
            source.fetched_text = fetch_platform(source.platform, source.url)
            source.status = "ok"
            source.error = None
        except (FetchError, Exception) as exc:  # noqa: BLE001 - status surfaced to user
            source.status = "error"
            source.error = str(exc)[:500]
            source.fetched_text = None
        source.fetched_at = datetime.now(timezone.utc)
    db.commit()
    record_audit(db, "sources.fetched", user_id=current_user.id, project_id=project.id)
    return _source_rows(db, project.id)


# ---------- Documents ----------
@router.post("/{project_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_UPLOADS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. Allowed: txt, pdf, docx, xlsx, pptx, png, jpg, webp, gif.",
        )

    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    storage = get_storage()
    document_id = str(uuid.uuid4())
    ext = ALLOWED_UPLOADS[content_type]
    key = f"projects/{project.id}/documents/{document_id}.{ext}"
    storage.put(key, data, content_type)

    text = extract_text(file.filename or "", data, content_type)

    doc = ProjectDocument(
        project_id=project.id,
        name=(file.filename or f"document.{ext}")[:255],
        object_key=key,
        original_name=file.filename,
        content_type=content_type,
        extracted_text=text,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    record_audit(db, "document.upload", user_id=current_user.id, project_id=project.id)
    return DocumentOut(
        id=doc.id,
        name=doc.name,
        original_name=doc.original_name,
        content_type=doc.content_type,
        has_text=bool(doc.extracted_text),
        created_at=doc.created_at,
    )


@router.get("/{project_id}/documents", response_model=list[DocumentOut])
def list_documents(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)
    docs = (
        db.query(ProjectDocument)
        .filter_by(project_id=project.id)
        .order_by(ProjectDocument.created_at.desc())
        .all()
    )
    return [
        DocumentOut(
            id=d.id,
            name=d.name,
            original_name=d.original_name,
            content_type=d.content_type,
            has_text=bool(d.extracted_text),
            created_at=d.created_at,
        )
        for d in docs
    ]


# ---------- Agentic build ----------
def _build_corpus(db: Session, project: Project) -> str:
    parts: list[str] = []
    sources = (
        db.query(ProjectSource)
        .filter_by(project_id=project.id)
        .order_by(ProjectSource.platform)
        .all()
    )
    for source in sources:
        if source.status == "ok" and source.fetched_text:
            parts.append(
                f"### Source: {source.platform} ({source.url})\n{source.fetched_text}"
            )
        elif source.url:
            parts.append(f"### Source: {source.platform} ({source.url}) — not fetched")

    docs = (
        db.query(ProjectDocument)
        .filter_by(project_id=project.id)
        .order_by(ProjectDocument.created_at.desc())
        .all()
    )
    for doc in docs:
        if doc.extracted_text:
            parts.append(f"### Document: {doc.original_name or doc.name}\n{doc.extracted_text}")
        else:
            parts.append(f"### Document: {doc.original_name or doc.name} (no extractable text)")

    return "\n\n".join(parts)


@router.post("/{project_id}/research-generate")
def research_generate(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run the OpenAI Agents SDK research agent and auto-fill the report."""
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)
    template = db.get(Template, project.template_id)

    from ..services.ai_service import AiKeyMissingError, input_json_to_profile, merge_plan
    from ..services.research_agent import run_research_agent

    profile = input_json_to_profile(project.input_json or {})
    corpus = _build_corpus(db, project)
    user_prompt = (project.input_json or {}).get("_user_prompt")
    try:
        plan = run_research_agent(profile, corpus, template.schema_json, user_prompt=user_prompt)
    except AiKeyMissingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="The AI returned an unreadable response. Please try again.",
        ) from exc

    project.input_json = merge_plan(project.input_json or {}, plan)
    db.commit()
    record_audit(db, "project.research_generate", user_id=current_user.id, project_id=project.id)
    return {"applied": True, "plan": plan}