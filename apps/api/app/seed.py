"""Startup seeding: create tables, demo user/org, bundled sample template.

Idempotent — safe to run on every startup.
"""

import io
import json
import uuid

from .database import Base, SessionLocal, engine
from .models import Organization, Template, User
from .storage import get_storage
from .template_builder import BUNDLED_TEMPLATES

DEMO_EMAIL = "demo@brightpath.org"
DEMO_PASSWORD = "demo-password-123"
DEMO_ORG = "BrightPath Foundation"

DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _default_images() -> dict[str, tuple[bytes, str]]:
    """Generate bundled placeholder images (logo + funding chart) via Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return {}

    def _font(size: int):
        try:
            return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
        except Exception:
            return ImageFont.load_default()

    images: dict[str, tuple[bytes, str]] = {}

    # Logo placeholder
    logo = Image.new("RGB", (800, 300), (0x0B, 0x6E, 0x6B))
    draw = ImageDraw.Draw(logo)
    draw.rounded_rectangle([40, 40, 760, 260], radius=24, fill=(0x0F, 0x83, 0x80))
    draw.text((400, 150), "BRIGHTPATH", fill=(255, 255, 255), anchor="mm", font=_font(56))
    buf = io.BytesIO()
    logo.save(buf, format="PNG")
    images["logo"] = (buf.getvalue(), "image/png")

    # Funding chart placeholder (simple bar chart)
    chart = Image.new("RGB", (1200, 600), (0xFF, 0xFF, 0xFF))
    draw = ImageDraw.Draw(chart)
    labels = ["2019", "2020", "2021", "2022", "2023"]
    values = [120, 180, 240, 310, 420]
    bar_w = 130
    base_y = 500
    max_v = max(values)
    x = 120
    for label, value in zip(labels, values):
        h = int(value * 420 / max_v)
        draw.rectangle([x, base_y - h, x + bar_w, base_y], fill=(0x0B, 0x6E, 0x6B))
        draw.text((x + bar_w / 2, base_y - h - 24), str(value), fill=(0x22, 0x33, 0x33), anchor="mm", font=_font(24))
        draw.text((x + bar_w / 2, base_y + 24), label, fill=(0x6B, 0x72, 0x80), anchor="mm", font=_font(26))
        x += bar_w + 80
    draw.text((600, 40), "Funding raised (USD 000s)", fill=(0x22, 0x33, 0x33), anchor="mm", font=_font(40))
    buf = io.BytesIO()
    chart.save(buf, format="PNG")
    images["chart_funding"] = (buf.getvalue(), "image/png")

    # Impact chart placeholder (yearly beneficiaries bar chart)
    chart2 = Image.new("RGB", (1200, 600), (0xFF, 0xFF, 0xFF))
    draw = ImageDraw.Draw(chart2)
    labels2 = ["2019", "2020", "2021", "2022", "2023"]
    values2 = [8000, 10500, 12800, 15000, 17800]
    bar_w = 130
    base_y = 500
    max_v = max(values2)
    x = 120
    for label, value in zip(labels2, values2):
        h = int(value * 420 / max_v)
        draw.rectangle([x, base_y - h, x + bar_w, base_y], fill=(0x0F, 0x83, 0x80))
        draw.text((x + bar_w / 2, base_y - h - 24), f"{value // 1000}K", fill=(0x22, 0x33, 0x33), anchor="mm", font=_font(24))
        draw.text((x + bar_w / 2, base_y + 24), label, fill=(0x6B, 0x72, 0x80), anchor="mm", font=_font(26))
        x += bar_w + 80
    draw.text((600, 40), "People served per year", fill=(0x22, 0x33, 0x33), anchor="mm", font=_font(40))
    buf = io.BytesIO()
    chart2.save(buf, format="PNG")
    images["chart_impact"] = (buf.getvalue(), "image/png")

    # Programme photo placeholders (photo-sized cards with a label)
    palette = [
        ("Community", 0x2E, 0x86, 0xAB),
        ("Education", 0xE0, 0x6C, 0x75),
        ("Nutrition", 0x86, 0xAF, 0x49),
        ("Youth", 0xF2, 0xA9, 0x1E),
    ]
    for index, (label, r, g, b) in enumerate(palette, start=1):
        photo = Image.new("RGB", (1400, 800), (r, g, b))
        draw = ImageDraw.Draw(photo)
        draw.rounded_rectangle([60, 60, 1340, 740], radius=28, fill=(r, g, b))
        draw.text((700, 400), f"PROGRAMME {index}\n{label.upper()}", fill=(255, 255, 255), anchor="mm", font=_font(72))
        buf = io.BytesIO()
        photo.save(buf, format="PNG")
        images[f"program_{index}"] = (buf.getvalue(), "image/png")

    return images


def ensure_bundled_templates_for_org(db, org: Organization) -> list[Template]:
    """Idempotently create every bundled template an organization is missing.

    Each org gets all bundled templates (new signups at registration, existing
    orgs backfilled lazily on first template list). Safe to run repeatedly.
    """
    created: list[Template] = []
    storage = get_storage()
    defaults = _default_images()

    for name, schema, builder in BUNDLED_TEMPLATES:
        existing = db.query(Template).filter_by(org_id=org.id, name=name).first()
        if existing is not None:
            continue

        template_id = str(uuid.uuid4())
        docx_bytes = builder()
        docx_key = f"templates/{template_id}/template.docx"
        storage.put(docx_key, docx_bytes, DOCX_MIME)

        manifest: dict[str, str] = {}
        for image_name, (data, content_type) in defaults.items():
            image_key = f"templates/{template_id}/images/{image_name}.png"
            storage.put(image_key, data, content_type)
            manifest[image_name] = image_key
        storage.put(
            f"templates/{template_id}/manifest.json",
            json.dumps(manifest).encode("utf-8"),
            "application/json",
        )

        template = Template(
            id=template_id,
            org_id=org.id,
            name=name,
            description=schema["description"],
            status="active",
            file_key=docx_key,
            schema_json=schema,
            version=1,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        created.append(template)
        print(f"[seed] assigned bundled template {name} ({template_id}) to org {org.name}")

    return created


def seed() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        # --- Demo user + organization ---
        user = db.query(User).filter_by(email=DEMO_EMAIL).first()
        if user is None:
            from .security import hash_password

            user = User(
                email=DEMO_EMAIL,
                org_name=DEMO_ORG,
                password_hash=hash_password(DEMO_PASSWORD),
            )
            db.add(user)
            db.flush()
            db.add(Organization(user_id=user.id, name=DEMO_ORG))
            db.commit()
            print(f"[seed] created demo user {DEMO_EMAIL} / {DEMO_PASSWORD}")

        org = db.query(Organization).filter_by(user_id=user.id).first()

        # --- Bundled templates for the demo organization ---
        ensure_bundled_templates_for_org(db, org)
    finally:
        db.close()