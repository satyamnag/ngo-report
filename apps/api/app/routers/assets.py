"""Report asset routes: upload / list placeholder images for a project."""

import io
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Organization, Project, ReportAsset, User, record_audit
from ..schemas import AssetOut
from ..security import get_current_user
from ..storage import get_storage

router = APIRouter(prefix="/api/projects/{project_id}/assets", tags=["assets"])


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


@router.post("", response_model=AssetOut, status_code=201)
async def upload_asset(
    project_id: str,
    name: str = Form(...),
    asset_type: str = Form("image"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload an image to fill a placeholder ([img:NAME]). Name must match the
    marker name in the template. Content type + size are validated; the object
    key is server-generated (never the user filename)."""
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)

    if file.content_type not in settings.allowed_image_types:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported content type {file.content_type}. Allowed: {settings.allowed_image_types}",
        )

    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Image too large")

    storage = get_storage()
    asset_id = str(uuid.uuid4())
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}.get(
        file.content_type, "bin"
    )
    key = f"projects/{project.id}/assets/{asset_id}.{ext}"
    storage.put(key, data, file.content_type)

    # Replace an existing asset with the same placeholder name.
    existing = (
        db.query(ReportAsset)
        .filter_by(project_id=project.id, name=name)
        .first()
    )
    if existing:
        storage.delete(existing.object_key)
        existing.object_key = key
        existing.asset_type = asset_type
        existing.original_name = file.filename
        db.commit()
        db.refresh(existing)
        record_audit(db, f"asset.replace:{name}", user_id=current_user.id, project_id=project.id)
        return existing

    asset = ReportAsset(
        project_id=project.id,
        name=name,
        asset_type=asset_type,
        object_key=key,
        original_name=file.filename,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    record_audit(db, f"asset.upload:{name}", user_id=current_user.id, project_id=project.id)
    return asset


@router.get("", response_model=list[AssetOut])
def list_assets(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = _get_org(db, current_user)
    project = _get_project(db, org, project_id)
    return db.query(ReportAsset).filter_by(project_id=project.id).all()