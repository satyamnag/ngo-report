"""Backend smoke tests exercising the generation pipeline with the running
stack (Postgres + Redis + Celery). Requires CELERY_TASK_EAGER=true so no
worker is needed.

Run from apps/api:
    CELERY_TASK_EAGER=true ../.venv/bin/python -m pytest tests -q
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("CELERY_TASK_EAGER", "true")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://ngo_app:ngo_app_dev_password@localhost:5432/ngo_report",
)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.models import Generation, Organization, Project, Template, User  # noqa: E402
from app.seed import DEMO_EMAIL, DEMO_PASSWORD  # noqa: E402
from app.services.generation import validate_docx  # noqa: E402

client = TestClient(app)


def _login() -> str:
    resp = client.post(
        "/api/auth/login",
        data={"username": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health():
    assert client.get("/api/health").status_code == 200


def test_register_login_and_templates():
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.org"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "org_name": "Smoke Test Org", "password": "password-1234"},
    )
    assert resp.status_code == 201, resp.text

    # duplicate registration rejected
    dup = client.post(
        "/api/auth/register",
        json={"email": email, "org_name": "Smoke Test Org", "password": "password-1234"},
    )
    assert dup.status_code == 409

    token = _login()
    templates = client.get("/api/templates", headers=_auth(token))
    assert templates.status_code == 200
    assert len(templates.json()) >= 1


def test_full_generation_pipeline():
    token = _login()
    templates = client.get("/api/templates", headers=_auth(token)).json()
    template = templates[0]

    resp = client.post(
        "/api/projects",
        headers=_auth(token),
        json={"template_id": template["id"], "title": "Pipeline Smoke"},
    )
    assert resp.status_code == 201, resp.text
    pid = resp.json()["id"]

    payload = {
        "input_json": {
            "org_name": "Smoke Org",
            "report_year": "2026",
            "tagline": "Testing the pipeline",
            "mission": {"statement": "Every child thrives."},
            "impact": {"beneficiaries": 100, "communities": 5, "volunteers": 20},
            "financial": {"total": "$100K"},
            "donors": {"acknowledgment": "Thanks!"},
            "future_goals": "Keep growing.",
        }
    }
    assert client.put(
        f"/api/projects/{pid}/details", headers=_auth(token), json=payload
    ).status_code == 200

    resp = client.post(f"/api/projects/{pid}/generate", headers=_auth(token), json={})
    assert resp.status_code == 202, resp.text
    gen_id = resp.json()["id"]

    gen = None
    for _ in range(50):
        gen = client.get(
            f"/api/projects/{pid}/generations/latest", headers=_auth(token)
        ).json()
        if gen["status"] in ("completed", "failed"):
            break

    assert gen and gen["status"] == "completed", gen
    assert gen["id"] == gen_id

    docx = client.get(
        f"/api/projects/{pid}/download?format=docx", headers=_auth(token)
    )
    assert docx.status_code == 200
    assert docx.content[:2] == b"PK"
    validate_docx(docx.content)

    pdf = client.get(f"/api/projects/{pid}/download?format=pdf", headers=_auth(token))
    assert pdf.status_code == 200
    assert pdf.content[:5] == b"%PDF-"

    preview = client.get(f"/api/projects/{pid}/report", headers=_auth(token))
    assert preview.status_code == 200
    assert b"Smoke Org" in preview.content

    sections = client.get(f"/api/projects/{pid}/sections", headers=_auth(token))
    assert sections.status_code == 200
    schema = client.get(
        f"/api/templates/{template['id']}/schema", headers=_auth(token)
    ).json()["schema_json"]
    assert len(sections.json()) == len(schema["sections"])
    first_section = sections.json()[0]["section_key"]

    assert client.put(
        f"/api/projects/{pid}/sections/{first_section}",
        headers=_auth(token),
        json={"content_html": "<p>Edited section text.</p>"},
    ).status_code == 200

    resp = client.post(f"/api/projects/{pid}/rebuild", headers=_auth(token), json={})
    assert resp.status_code == 202, resp.text

    for _ in range(50):
        gen = client.get(
            f"/api/projects/{pid}/generations/latest", headers=_auth(token)
        ).json()
        if gen["status"] in ("completed", "failed"):
            break
    assert gen["status"] == "completed", gen


def test_template_upload_validation():
    token = _login()
    # invalid file rejected
    resp = client.post(
        "/api/templates",
        headers=_auth(token),
        data={"name": "Bad", "schema_json": '{"sections": []}'},
        files={"file": ("bad.docx", b"not a zip", "application/octet-stream")},
    )
    assert resp.status_code == 422


def test_asset_upload_rejects_bad_mime():
    token = _login()
    templates = client.get("/api/templates", headers=_auth(token)).json()
    resp = client.post(
        "/api/projects",
        headers=_auth(token),
        json={"template_id": templates[0]["id"], "title": "Asset Smoke"},
    )
    pid = resp.json()["id"]
    resp = client.post(
        f"/api/projects/{pid}/assets",
        headers=_auth(token),
        data={"name": "logo", "asset_type": "image"},
        files={"file": ("x.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 415