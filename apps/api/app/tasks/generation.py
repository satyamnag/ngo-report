"""Celery background tasks for the report generation pipeline.

Run with: celery -A app.celery_app worker --loglevel=info
"""

import uuid

from ..celery_app import celery_app
from ..database import SessionLocal
from ..models import Generation, Project, ReportAsset, ReportSection, Template, record_audit
from ..services.generation import (
    build_defaulted_context,
    docx_to_html,
    docx_to_pdf,
    html_to_plain_text,
    render_report,
)
from ..storage import get_storage
from ..services.theme import apply_background_to_pdf, apply_theme, background_png_bytes

DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _get_custom_background(db, project_id: str) -> bytes | None:
    asset = (
        db.query(ReportAsset)
        .filter_by(project_id=project_id, name="_background")
        .first()
    )
    if asset is None:
        return None
    try:
        return get_storage().get(asset.object_key).data
    except Exception:
        return None


def _load_template_manifest(storage, template_id: str) -> dict[str, str]:
    """Load templates/<id>/manifest.json -> { image_name: object_key }."""
    try:
        manifest = storage.get(f"templates/{template_id}/manifest.json")
        import json

        return json.loads(manifest.data.decode("utf-8"))
    except Exception:
        return {}


def _build_image_provider(db, project_id: str, template_id: str):
    """Return a callable(name) -> ObjectData | None combining user-uploaded
    project assets with the template's bundled default images."""
    storage = get_storage()

    user_assets: dict[str, object] = {}
    for asset in db.query(ReportAsset).filter_by(project_id=project_id).all():
        try:
            user_assets[asset.name] = storage.get(asset.object_key)
        except Exception:
            continue

    defaults: dict[str, object] = {}
    for name, key in _load_template_manifest(storage, template_id).items():
        try:
            defaults[name] = storage.get(key)
        except Exception:
            continue

    def provider(name: str):
        if name in user_assets:
            return user_assets[name]
        if name in defaults:
            return defaults[name]
        return None

    return provider


def _section_path(schema_json: dict, section_key: str) -> str | None:
    section_map = (schema_json or {}).get("section_map") or {}
    return section_map.get(section_key)


def _set_nested(context: dict, path: str, value):
    keys = path.split(".")
    node = context
    for key in keys[:-1]:
        node = node.setdefault(key, {})
    node[keys[-1]] = value


def _run_generation(
    db, generation: Generation, project: Project, template: Template,
    rich_overrides: list[tuple[str, str]] | None = None,
) -> None:
    storage = get_storage()

    generation.status = "running"
    generation.error = None
    db.commit()

    context = build_defaulted_context(template.schema_json, generation.input_json or {})
    template_bytes = storage.get(template.file_key).data
    provider = _build_image_provider(db, project.id, template.id)
    docx_bytes = render_report(template_bytes, context, provider)

    # Fold Word-like rich section edits into the DOCX (falls back to plain text).
    if rich_overrides:
        from ..services.rich_sections import apply_rich_sections

        docx_bytes = apply_rich_sections(docx_bytes, rich_overrides)

    # Apply the user's theme color + page background.
    theme_input = generation.input_json or {}
    docx_bytes = apply_theme(
        docx_bytes,
        theme_color=theme_input.get("_theme_color"),
        background_id=theme_input.get("_theme_background"),
        custom_background=_get_custom_background(db, project.id),
    )
    docx_key = f"projects/{project.id}/generations/{generation.id}/report.docx"
    storage.put(docx_key, docx_bytes, DOCX_MIME)
    generation.output_docx_key = docx_key
    generation.status = "converting"
    db.commit()

    pdf_bytes = docx_to_pdf(docx_bytes)
    # Guaranteed page background for the PDF (LibreOffice ignores DOCX settings
    # backgrounds, so we overlay it here on every page).
    if theme_input.get("_theme_background") and theme_input.get("_theme_background") != "none":
        bg_image = background_png_bytes(theme_input["_theme_background"], 1240, 1754)
    else:
        bg_image = _get_custom_background(db, project.id)
    if bg_image:
        pdf_bytes = apply_background_to_pdf(pdf_bytes, bg_image)
    pdf_key = f"projects/{project.id}/generations/{generation.id}/report.pdf"
    storage.put(pdf_key, pdf_bytes, "application/pdf")
    generation.output_pdf_key = pdf_key
    generation.status = "completed"
    db.commit()

    project.status = "generated"
    db.commit()
    record_audit(db, "report.generated", project_id=project.id)


@celery_app.task(bind=True, name="generation.generate")
def generate_report_task(self, project_id: str, generation_id: str) -> dict:
    db = SessionLocal()
    try:
        generation = db.get(Generation, generation_id)
        project = db.get(Project, project_id)
        if generation is None or project is None:
            raise ValueError("project or generation not found")
        template = db.get(Template, project.template_id)
        _run_generation(db, generation, project, template)
        return {"generation_id": generation_id, "status": generation.status}
    except Exception as exc:
        db.rollback()
        generation = db.get(Generation, generation_id)
        if generation is not None:
            generation.status = "failed"
            generation.error = str(exc)
            db.commit()
            record_audit(db, f"report.failed: {exc}", project_id=project_id)
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="generation.rebuild")
def rebuild_report_task(self, project_id: str) -> dict:
    """Regenerate the report with TipTap section overrides applied."""
    db = SessionLocal()
    generation: Generation | None = None
    try:
        project = db.get(Project, project_id)
        if project is None:
            raise ValueError("project not found")
        template = db.get(Template, project.template_id)

        context = dict(project.input_json or {})
        sections = (
            db.query(ReportSection)
            .filter_by(project_id=project_id)
            .order_by(ReportSection.sort_order)
            .all()
        )
        rich_overrides: list[tuple[str, str]] = []
        for section in sections:
            path = _section_path(template.schema_json, section.section_key)
            if path and section.content_html:
                plain = html_to_plain_text(section.content_html)
                _set_nested(context, path, plain)
                rich_overrides.append((plain, section.content_html))

        generation = Generation(
            project_id=project.id,
            template_id=template.id,
            input_json=context,
            status="pending",
        )
        db.add(generation)
        db.commit()
        db.refresh(generation)

        _run_generation(db, generation, project, template, rich_overrides=rich_overrides)

        # Persist the merged context (edited sections folded in) so the project
        # record stays the source of truth for previews and later rebuilds.
        project.input_json = generation.input_json
        db.commit()

        return {"generation_id": generation.id, "status": generation.status}
    except Exception as exc:
        db.rollback()
        if generation is not None:
            generation = db.get(Generation, generation.id)
            if generation is not None:
                generation.status = "failed"
                generation.error = str(exc)
                db.commit()
        raise
    finally:
        db.close()


@celery_app.task(name="generation.preview_html")
def preview_html_task(project_id: str) -> str:
    """Convert the latest DOCX to HTML for the browser preview."""
    db = SessionLocal()
    try:
        latest = (
            db.query(Generation)
            .filter_by(project_id=project_id)
            .order_by(Generation.created_at.desc())
            .first()
        )
        if latest is None or not latest.output_docx_key:
            raise ValueError("no generated report available")
        storage = get_storage()
        return docx_to_html(storage.get(latest.output_docx_key).data)
    finally:
        db.close()