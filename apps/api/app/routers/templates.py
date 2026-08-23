"""Template routes: list, schema, upload (with validation)."""

import io
import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
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

# Demo content so the preview shows the design (preview only, never a real report).
_PREVIEW_CONTEXT = {
    "report_year": "2029",
    "tagline": "Because together we are stronger",
    "cover_authors": "KALAN ABHEEDI, ROYCE CHALMER\nAMANDA SULLY, JANN VAN HUYSEN\nJEANNETTE MOSS, ELENA SONG",
    "intro_title": "The Road We Walked Together",
    "intro_text": "Our journey would not have been possible without our valued volunteers, dedicated donors, and the many professionals who helped our cause.",
    "strategy_funds_2029": "$14,500,200",
    "strategy_funds_2028": "$13,400,700",
    "strategy_people_2029": "15,200",
    "strategy_people_2028": "13,700",
    "outreach_emails": "23,000",
    "outreach_conversations": "12,000",
    "outreach_speeches": "23",
    "volunteer_growth": "13%",
    "volunteer_hours": "460k",
    "volunteer_party": "1",
    "finance_events": "• Planning fundraiser events\n• Community gatherings\n• Sporting events",
    "finance_conferences": "Attending conferences as guest or speaker to raise awareness.",
    "finance_digital": "We create a digital roadmap to building our online following.",
    "projects_fundraiser": "The annual fundraiser is the most significant event of the year in terms of donor impact.",
    "projects_campaign": "Inspired by our digital marketing team, this campaign was digital and on-the-ground.",
    "projects_handwash_title": "If you're happy and you know it, wash your hands",
    "projects_handwash_text": "Like many other illnesses, meningitis can be transmitted through the sharing of germs.",
    "projects_checklist": "✓ Awareness posters in urban areas.\n✓ Promotional video with 20,000 shares.\n✓ Public washing stations throughout the city.",
}


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

    # Idempotently assign any bundled templates the org is missing (safe to run
    # on every list; new signups get them at registration).
    from ..seed import ensure_bundled_templates_for_org

    ensure_bundled_templates_for_org(db, org)

    return (
        db.query(Template)
        .filter(Template.org_id == org.id, Template.status == "active")
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


@router.get("/{template_id}/preview")
def template_preview(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Render the template's first page as a PNG for the preview (cached)."""
    org = _get_org(db, current_user)
    template = db.query(Template).filter_by(id=template_id, org_id=org.id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    storage = get_storage()
    cache_key = f"templates/{template.id}/preview.png"
    if storage.exists(cache_key):
        return Response(content=storage.get(cache_key).data, media_type="image/png")

    from ..services.generation import build_defaulted_context, docx_to_pdf, render_report

    docx_bytes = storage.get(template.file_key).data
    context = build_defaulted_context(template.schema_json, _PREVIEW_CONTEXT)

    from ..seed import _default_images

    _defaults = {name: __import__("app.storage", fromlist=["ObjectData"]).ObjectData(data=data, content_type=ct) for name, (data, ct) in _default_images().items()}

    rendered = render_report(docx_bytes, context, lambda name: _defaults.get(name))
    pdf = docx_to_pdf(rendered)

    import fitz
    from PIL import Image

    pdf_doc = fitz.open(stream=pdf, filetype="pdf")
    page_images = [page.get_pixmap(dpi=100) for page in pdf_doc]
    if not page_images:
        raise HTTPException(status_code=500, detail="Could not render template preview")
    width = page_images[0].width
    height = sum(p.height for p in page_images)
    combined = Image.new("RGB", (width, height), (255, 255, 255))
    y = 0
    for p in page_images:
        combined.paste(Image.open(io.BytesIO(p.tobytes("png"))), (0, y))
        y += p.height
    png_buf = io.BytesIO()
    combined.save(png_buf, format="PNG")
    png = png_buf.getvalue()
    pdf_doc.close()

    storage.put(cache_key, png, "image/png")
    return Response(content=png, media_type="image/png")


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