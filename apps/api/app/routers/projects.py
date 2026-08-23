"""Project routes: create, details, generate, download, preview, sections."""

import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import (
    Generation,
    Organization,
    Project,
    ReportSection,
    Template,
    User,
    record_audit,
)
from ..schemas import (
    AuditOut,
    GenerationOut,
    ProjectCreate,
    ProjectDetails,
    ProjectOut,
    SectionOut,
    SectionUpdate,
)
from ..security import get_current_user
from ..services.generation import docx_to_html
from ..storage import get_storage
from ..tasks.generation import generate_report_task, preview_html_task, rebuild_report_task

router = APIRouter(prefix="/api/projects", tags=["projects"])

DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


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


def _seed_sections(db: Session, project: Project, template: Template) -> None:
    """Create default report_sections from the template schema (idempotent)."""
    if project.sections:
        return
    for index, section in enumerate(template.schema_json.get("sections", [])):
        db.add(
            ReportSection(
                project_id=project.id,
                section_key=section.get("key", f"section_{index}"),
                sort_order=section.get("sort", index),
            )
        )
    db.commit()


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    template = db.query(Template).filter_by(id=payload.template_id, org_id=org.id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    project = Project(
        org_id=org.id,
        template_id=template.id,
        title=payload.title,
        status="draft",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    _seed_sections(db, project, template)
    record_audit(db, "project.create", user_id=current_user.id, project_id=project.id)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    return (
        db.query(Project)
        .filter_by(org_id=org.id)
        .order_by(Project.updated_at.desc())
        .all()
    )


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    return _get_project(db, org, project_id)


@router.put("/{project_id}/details", response_model=ProjectOut)
def save_details(
    project_id: str,
    payload: ProjectDetails,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)
    if payload.title is not None:
        project.title = payload.title
    if payload.input_json:
        project.input_json = payload.input_json
    if payload.theme_color is not None:
        project.input_json["_theme_color"] = payload.theme_color
    if payload.theme_background is not None:
        project.input_json["_theme_background"] = payload.theme_background
    db.commit()
    db.refresh(project)
    record_audit(db, "project.details_saved", user_id=current_user.id, project_id=project.id)
    return project


@router.post("/{project_id}/generate", response_model=GenerationOut, status_code=202)
def generate(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)

    generation = Generation(
        project_id=project.id,
        template_id=project.template_id,
        input_json=project.input_json or {},
        status="pending",
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)

    if settings.celery_task_eager:
        generate_report_task.apply(args=[project.id, generation.id])
    else:
        generate_report_task.delay(project.id, generation.id)

    record_audit(db, "project.generate", user_id=current_user.id, project_id=project.id)
    db.refresh(generation)
    return generation


@router.post("/{project_id}/rebuild", response_model=GenerationOut, status_code=202)
def rebuild(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerate with TipTap section edits folded into the template context."""
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)

    if settings.celery_task_eager:
        result = rebuild_report_task.apply(args=[project.id])
        generation_id = result.result.get("generation_id")
    else:
        result = rebuild_report_task.delay(project.id)
        generation_id = result.id

    generation = (
        db.query(Generation)
        .filter_by(project_id=project.id)
        .order_by(Generation.created_at.desc())
        .first()
    )
    record_audit(db, "project.rebuild", user_id=current_user.id, project_id=project.id)
    return generation


@router.get("/{project_id}/generations/latest", response_model=GenerationOut)
def latest_generation(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)
    generation = (
        db.query(Generation)
        .filter_by(project_id=project.id)
        .order_by(Generation.created_at.desc())
        .first()
    )
    if generation is None:
        raise HTTPException(status_code=404, detail="No generation yet")
    return generation


def _latest_generation(db: Session, project_id: str) -> Generation:
    generation = (
        db.query(Generation)
        .filter_by(project_id=project_id)
        .order_by(Generation.created_at.desc())
        .first()
    )
    if generation is None or not generation.output_docx_key:
        raise HTTPException(status_code=404, detail="No generated report yet")
    return generation


@router.get("/{project_id}/download")
def download(
    project_id: str,
    format: str = Query("docx", pattern="^(docx|pdf)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)
    generation = _latest_generation(db, project.id)

    key = generation.output_pdf_key if format == "pdf" else generation.output_docx_key
    if not key:
        raise HTTPException(status_code=404, detail="File not available yet")

    storage = get_storage()
    obj = storage.get(key)

    media_type = "application/pdf" if format == "pdf" else DOCX_MIME
    filename = f"{project.title or 'report'}.{format}"
    return StreamingResponse(
        io.BytesIO(obj.data),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{project_id}/report", response_class=HTMLResponse)
def report_preview(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """HTML preview of the latest generated DOCX (for the editor phase)."""
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)
    generation = _latest_generation(db, project.id)

    storage = get_storage()
    html = docx_to_html(storage.get(generation.output_docx_key).data)
    return HTMLResponse(content=html)


@router.get("/{project_id}/sections", response_model=list[SectionOut])
def list_sections(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)
    return (
        db.query(ReportSection)
        .filter_by(project_id=project.id)
        .order_by(ReportSection.sort_order)
        .all()
    )


@router.put("/{project_id}/sections/{section_key}", response_model=SectionOut)
def update_section(
    project_id: str,
    section_key: str,
    payload: SectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)
    section = (
        db.query(ReportSection)
        .filter_by(project_id=project.id, section_key=section_key)
        .first()
    )
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    if payload.content_html is not None:
        section.content_html = payload.content_html
    if payload.image_url is not None:
        section.image_url = payload.image_url
    db.commit()
    db.refresh(section)
    record_audit(db, f"section.update:{section_key}", user_id=current_user.id, project_id=project.id)
    return section


@router.post("/{project_id}/ai-generate", status_code=200)
def ai_generate(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a content plan with OpenAI using the bundled agent prompt, then
    auto-fill the project's details. Factual fields are never overwritten."""
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)
    template = db.get(Template, project.template_id)

    from ..services.ai_service import (
        AiKeyMissingError,
        generate_content_plan,
        input_json_to_profile,
        merge_plan,
    )

    profile = input_json_to_profile(project.input_json or {})
    try:
        plan = generate_content_plan(profile, template.schema_json)
    except AiKeyMissingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="The AI returned an unreadable response. Please try again.",
        ) from exc

    merged = merge_plan(project.input_json or {}, plan)
    project.input_json = merged
    db.commit()
    record_audit(db, "project.ai_generate", user_id=current_user.id, project_id=project.id)
    return {"applied": True, "plan": plan}


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)

    # Best-effort removal of stored artifacts (never fails the delete).
    storage = get_storage()
    keys: list[str] = []
    for generation in project.generations:
        if generation.output_docx_key:
            keys.append(generation.output_docx_key)
        if generation.output_pdf_key:
            keys.append(generation.output_pdf_key)
    keys.extend(asset.object_key for asset in project.assets)
    keys.extend(doc.object_key for doc in project.documents)
    for key in keys:
        try:
            storage.delete(key)
        except Exception:
            continue

    record_audit(db, "project.delete", user_id=current_user.id, project_id=project.id)
    # audit_logs reference projects without cascade; remove them explicitly.
    from ..models import AuditLog

    db.query(AuditLog).filter(AuditLog.project_id == project.id).delete(
        synchronize_session=False
    )
    db.delete(project)
    db.commit()


@router.get("/{project_id}/audit", response_model=list[AuditOut])
def audit_trail(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)
    from ..models import AuditLog

    logs = (
        db.query(AuditLog)
        .filter_by(project_id=project.id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
        .all()
    )
    return logs