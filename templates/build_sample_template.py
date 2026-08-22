"""Regenerate the bundled sample template artifacts (template.docx + schema.json
+ placeholder images).

Run:  ../.venv/bin/python build_sample_template.py
Outputs into templates/ngo_annual_report/.
"""

import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from app.seed import _default_images  # noqa: E402
from app.template_builder import SAMPLE_SCHEMA, build_sample_template  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "ngo_annual_report")


def main() -> None:
    os.makedirs(os.path.join(OUT, "images"), exist_ok=True)
    with open(os.path.join(OUT, "template.docx"), "wb") as fh:
        fh.write(build_sample_template())
    with open(os.path.join(OUT, "schema.json"), "w", encoding="utf-8") as fh:
        json.dump(SAMPLE_SCHEMA, fh, indent=2)
    for name, (data, _content_type) in _default_images().items():
        with open(os.path.join(OUT, "images", f"{name}.png"), "wb") as fh:
            fh.write(data)
    print(f"wrote {OUT}/template.docx, schema.json and images/")


if __name__ == "__main__":
    main()