"""Background template catalog + previews for the theme selector."""

import io

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..services.theme import BACKGROUNDS, render_background_image

router = APIRouter(prefix="/api/backgrounds", tags=["backgrounds"])

PREVIEW_W, PREVIEW_H = 240, 340


@router.get("")
def list_backgrounds():
    return [
        {"id": bg_id, "name": meta["name"], "kind": meta["kind"]}
        for bg_id, meta in BACKGROUNDS.items()
    ]


@router.get("/{background_id}/preview")
def background_preview(background_id: str) -> Response:
    meta = BACKGROUNDS.get(background_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Background not found")

    if meta["kind"] == "none":
        from PIL import Image

        img = Image.new("RGB", (PREVIEW_W, PREVIEW_H), (255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")

    if meta["kind"] == "solid":
        from PIL import Image

        img = Image.new("RGB", (PREVIEW_W, PREVIEW_H), tuple(int(meta["color"][i : i + 2], 16) for i in (0, 2, 4)))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")

    data = render_background_image(background_id, PREVIEW_W, PREVIEW_H)
    return Response(content=data, media_type="image/png")