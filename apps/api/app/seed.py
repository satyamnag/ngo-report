"""Startup seeding: create tables, demo user/org, bundled sample template.

Idempotent — safe to run on every startup.
"""

import io
import json
import uuid

from .database import Base, SessionLocal, engine
from .models import Organization, Template, User
from .storage import get_storage
from .template_builder import SAMPLE_SCHEMA, build_sample_template

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
    scale = 1.0
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

    return images


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

        # --- Bundled sample template ---
        existing = db.query(Template).filter_by(org_id=org.id, name="NGO Annual Report").first()
        if existing is not None:
            return

        storage = get_storage()
        template_id = str(uuid.uuid4())
        docx_bytes = build_sample_template()

        docx_key = f"templates/{template_id}/template.docx"
        storage.put(docx_key, docx_bytes, DOCX_MIME)

        manifest: dict[str, str] = {}
        for name, (data, content_type) in _default_images().items():
            image_key = f"templates/{template_id}/images/{name}.png"
            storage.put(image_key, data, content_type)
            manifest[name] = image_key
        storage.put(
            f"templates/{template_id}/manifest.json",
            json.dumps(manifest).encode("utf-8"),
            "application/json",
        )

        template = Template(
            id=template_id,
            org_id=org.id,
            name="NGO Annual Report",
            description=SAMPLE_SCHEMA["description"],
            status="active",
            file_key=docx_key,
            schema_json=SAMPLE_SCHEMA,
            version=1,
        )
        db.add(template)
        db.commit()
        print(f"[seed] created sample template {template.name} ({template.id})")
    finally:
        db.close()