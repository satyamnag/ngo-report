"""Template routes: list, schema, upload (with validation)."""

import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Organization, Template, User, record_audit
from ..schemas import TemplateOut, TemplateSchemaOut
from ..security import get_current_user
from ..services.generation import TemplateValidationError, validate_docx
from ..storage import get_storage

router = APIRouter(prefix="/api/templates", tags=["templates"])

DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _get_org(db: Session, user: User) -> Organization:
    org = db.query(Organization).filter_by(user_id=user.id).first()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get("", response_model=list[TemplateOut])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    return (
        db.query(Template)
        .filter(Template.org_id == org.id)
        .order_by(Template.created_at.desc())
        .all()
    )


@router.get("/{template_id}/schema", response_model=TemplateSchemaOut)
def get_schema(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    template = db.query(Template).filter_by(id=template_id, org_id=org.id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateSchemaOut(
        id=template.id, name=template.name, schema_json=template.schema_json
    )


@router.post("", response_model=TemplateOut, status_code=201)
async def upload_template(
    name: str = Form(...),
    description: str | None = Form(default=None),
    schema_json: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a new .docx template with its form schema (JSON string)."""
    org = _get_org(db, current_user)

    try:
        schema = json.loads(schema_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="schema_json must be valid JSON") from exc
    if not isinstance(schema, dict) or "sections" not in schema:
        raise HTTPException(
            status_code=422, detail="schema_json must contain a 'sections' list"
        )

    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Template file too large")
    try:
        validate_docx(data)
    except TemplateValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    storage = get_storage()
    template_id = str(uuid.uuid4())
    key = f"templates/{template_id}/template.docx"
    storage.put(key, data, DOCX_MIME)

    template = Template(
        id=template_id,
        org_id=org.id,
        name=name,
        description=description,
        status="active",
        file_key=key,
        schema_json=schema,
        version=1,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    record_audit(db, "template.upload", user_id=current_user.id)
    return template