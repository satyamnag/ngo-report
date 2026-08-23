"""Pydantic request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    org_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: str
    email: EmailStr
    org_name: str
    role: str

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ---------- Templates ----------
class TemplateOut(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    version: int
    schema_json: dict

    model_config = {"from_attributes": True}


class TemplateSchemaOut(BaseModel):
    id: str
    name: str
    schema_json: dict


# ---------- Projects ----------
class ProjectCreate(BaseModel):
    template_id: str
    title: str = Field(min_length=1, max_length=255)


class ProjectDetails(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    input_json: dict = Field(default_factory=dict)
    theme_color: str | None = Field(default=None, max_length=16)
    theme_background: str | None = Field(default=None, max_length=64)


class SectionUpdate(BaseModel):
    content_html: str | None = None
    image_url: str | None = None


class ProjectOut(BaseModel):
    id: str
    title: str
    status: str
    template_id: str
    input_json: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GenerationOut(BaseModel):
    id: str
    project_id: str
    status: str
    error: str | None
    output_docx_key: str | None
    output_pdf_key: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SectionOut(BaseModel):
    id: str
    section_key: str
    content_html: str | None
    image_url: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class AssetOut(BaseModel):
    id: str
    name: str
    asset_type: str
    original_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditOut(BaseModel):
    id: str
    action: str
    created_at: datetime

    model_config = {"from_attributes": True}