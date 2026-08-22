"""Programmatic construction of the bundled sample NGO report template.

The resulting .docx contains jinja2 placeholders ({{ var }}) filled by docxtpl
and [img:NAME] markers swapped for images by the generation pipeline. It is
reproducible from code so the scaffold works out-of-the-box without Word.
"""

import io

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

TEAL = RGBColor(0x0B, 0x6E, 0x6B)
DARK = RGBColor(0x22, 0x33, 0x33)
GREY = RGBColor(0x6B, 0x72, 0x80)


def _style_base(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = DARK
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.15


def _heading(doc: Document, text: str, size: int = 16) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(size)
    run.font.color.rgb = TEAL
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(6)
    return p


def _cover(doc: Document) -> None:
    for _ in range(4):
        doc.add_paragraph()

    logo = doc.add_paragraph()
    logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    logo.add_run("[img:logo]")

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("{{ org_name }}")
    run.bold = True
    run.font.size = Pt(30)
    run.font.color.rgb = TEAL

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub.add_run("Annual Report {{ report_year }}")
    run.font.size = Pt(18)
    run.font.color.rgb = GREY

    tag = doc.add_paragraph()
    tag.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = tag.add_run("{{ tagline }}")
    run.italic = True
    run.font.size = Pt(12)

    doc.add_page_break()


def _mission(doc: Document) -> None:
    _heading(doc, "Our Mission")
    doc.add_paragraph("{{ mission.statement }}")


def _impact(doc: Document) -> None:
    _heading(doc, "Impact in Numbers")
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers = table.rows[0].cells
    for index, text in enumerate(("Beneficiaries served", "Communities reached", "Volunteers engaged")):
        cell = headers[index]
        p = cell.paragraphs[0]
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(10)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    row = table.add_row().cells
    values = ("{{ impact.beneficiaries }}", "{{ impact.communities }}", "{{ impact.volunteers }}")
    for index, value in enumerate(values):
        p = row[index].paragraphs[0]
        run = p.add_run(value)
        run.font.size = Pt(14)
        run.font.color.rgb = TEAL
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _financials(doc: Document) -> None:
    _heading(doc, "Financial Highlights")
    chart = doc.add_paragraph()
    chart.alignment = WD_ALIGN_PARAGRAPH.CENTER
    chart.add_run("[img:chart_funding]")
    doc.add_paragraph("Total funding: {{ financial.total }}")


def _donors(doc: Document) -> None:
    _heading(doc, "Donor Acknowledgment")
    doc.add_paragraph("{{ donors.acknowledgment }}")


def _goals(doc: Document) -> None:
    _heading(doc, "Looking Ahead")
    doc.add_paragraph("{{ future_goals }}")


def build_sample_template() -> bytes:
    doc = Document()
    _style_base(doc)
    _cover(doc)
    _mission(doc)
    _impact(doc)
    _financials(doc)
    _donors(doc)
    _goals(doc)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


SAMPLE_SCHEMA = {
    "title": "NGO Annual Report",
    "description": "Standard annual report template with cover, mission, impact, financials, donor acknowledgment and future goals.",
    "sections": [
        {"key": "cover", "label": "Cover", "sort": 0},
        {"key": "mission", "label": "Mission", "sort": 1},
        {"key": "impact", "label": "Impact", "sort": 2},
        {"key": "financials", "label": "Financials", "sort": 3},
        {"key": "donors", "label": "Donor Acknowledgment", "sort": 4},
        {"key": "goals", "label": "Future Goals", "sort": 5},
    ],
    "section_map": {
        "mission": "mission.statement",
        "donors": "donors.acknowledgment",
        "goals": "future_goals",
    },
    "fields": [
        {
            "group": "Cover",
            "fields": [
                {"name": "org_name", "label": "Organization name", "type": "text", "path": "org_name", "required": True},
                {"name": "report_year", "label": "Report year", "type": "text", "path": "report_year", "required": True},
                {"name": "tagline", "label": "Tagline", "type": "textarea", "path": "tagline", "required": False},
                {"name": "logo", "label": "Logo image", "type": "image", "path": "logo", "placeholder": "logo", "required": False},
            ],
        },
        {
            "group": "Mission",
            "fields": [
                {"name": "mission_statement", "label": "Mission statement", "type": "textarea", "path": "mission.statement", "required": True},
            ],
        },
        {
            "group": "Impact",
            "fields": [
                {"name": "impact_beneficiaries", "label": "Beneficiaries served", "type": "number", "path": "impact.beneficiaries", "required": True},
                {"name": "impact_communities", "label": "Communities reached", "type": "number", "path": "impact.communities", "required": True},
                {"name": "impact_volunteers", "label": "Volunteers engaged", "type": "number", "path": "impact.volunteers", "required": True},
            ],
        },
        {
            "group": "Financials",
            "fields": [
                {"name": "financial_total", "label": "Total funding", "type": "number", "path": "financial.total", "required": True},
                {"name": "chart_funding", "label": "Funding chart image", "type": "image", "path": "chart_funding", "placeholder": "chart_funding", "required": False},
            ],
        },
        {
            "group": "Donor Acknowledgment",
            "fields": [
                {"name": "donors_ack", "label": "Donor acknowledgment text", "type": "textarea", "path": "donors.acknowledgment", "required": False},
            ],
        },
        {
            "group": "Future Goals",
            "fields": [
                {"name": "future_goals", "label": "Future goals", "type": "textarea", "path": "future_goals", "required": False},
            ],
        },
    ],
}