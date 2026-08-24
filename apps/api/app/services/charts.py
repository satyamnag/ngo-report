"""Generate real charts from the report's actual data (pattern from
ishaanchowdhury1/LLM-Annual-Report-Generator and bobinsingh/PedroReports).

When a user provides a breakdown like "Grants 30%, Donors 30%, Merch 15%...",
the finance page's placeholder donut is replaced with a real donut chart built
from those numbers. Everything is safe: unparseable/empty input falls back to
the bundled placeholder image.
"""

import io
import re

from PIL import Image, ImageDraw, ImageFont

DONUT_PALETTE = ["2A2A2A", "5B8DEF", "7BA3F5", "9DB8F8", "BDD0FB", "DCE8FD"]


def _font(size):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except Exception:
        return ImageFont.load_default()


def parse_breakdown(text: str) -> list[tuple[str, float]] | None:
    """Parse 'Grants 30%, Donors 30%, Merch 15%' -> [(label, pct), ...].
    Returns None when nothing usable is found."""
    if not text:
        return None
    items = []
    for match in re.finditer(
        r"([A-Za-z][A-Za-z0-9 &.'\-]{0,30}?)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*%?",
        text,
    ):
        label = match.group(1).strip()
        try:
            value = float(match.group(2))
        except ValueError:
            continue
        if label and value > 0:
            items.append((label, value))
    if not items:
        return None
    total = sum(v for _, v in items)
    if total <= 0:
        return None
    # Normalize to 100 so the ring is complete.
    return [(label, round(value * 100 / total, 1)) for label, value in items]


def donut_chart(
    percentages: list[tuple[str, float]],
    title: str,
    width: int = 700,
    height: int = 460,
) -> bytes:
    """Draw a donut chart with a legend. Returns PNG bytes."""
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    cx, cy, r = 220, 230, 170
    start = 0.0
    for index, (_label, pct) in enumerate(percentages):
        color = DONUT_PALETTE[index % len(DONUT_PALETTE)]
        sweep = pct / 100.0 * 360.0
        draw.pieslice(
            [cx - r, cy - r, cx + r, cy + r],
            start,
            start + sweep,
            fill="#" + color,
        )
        start += sweep
    draw.ellipse([cx - 60, cy - 60, cx + 60, cy + 60], fill=(255, 255, 255))
    draw.text((cx, cy), "100%", fill=(30, 30, 30), anchor="mm", font=_font(28))

    y = 60
    for index, (label, pct) in enumerate(percentages[:8]):
        color = DONUT_PALETTE[index % len(DONUT_PALETTE)]
        draw.rectangle([460, y, 500, y + 22], fill="#" + color)
        draw.text(
            (510, y + 11),
            f"{label} {pct:.0f}%",
            fill=(30, 30, 30),
            anchor="lm",
            font=_font(24),
        )
        y += 34
    draw.text((350, 30), title, fill=(30, 30, 30), anchor="mm", font=_font(36))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()