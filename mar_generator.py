"""
MAR Chart Generator - PDF and Word document output
Generates Medication Administration Record charts.
"""
from __future__ import annotations

import calendar
import io
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

ROUNDS = ["Morning", "Noon", "Evening", "Bedtime"]
ROUND_SHORT = {"Morning": "Morn", "Noon": "Noon", "Evening": "Eve", "Bedtime": "Bed"}


@dataclass
class Medication:
    name: str
    dose: str
    route: str
    start_date: str
    end_date: str = ""
    rounds: List[str] = field(default_factory=list)
    instructions: str = ""


@dataclass
class MARData:
    patient_name: str
    patient_dob: str
    patient_id: str
    allergies: str
    org_name: str
    org_address: str
    prescriber_name: str
    chart_month: int
    chart_year: int
    medications: List[Medication] = field(default_factory=list)


# ---------------------------------------------------------------------------
# PDF generation (reportlab)
# ---------------------------------------------------------------------------

def generate_pdf(data: MARData) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    )

    buf = io.BytesIO()
    page_w, page_h = landscape(A4)

    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = ParagraphStyle("small", parent=normal, fontSize=7, leading=9)
    small_bold = ParagraphStyle("small_bold", parent=normal, fontSize=7, leading=9, fontName="Helvetica-Bold")
    medium = ParagraphStyle("medium", parent=normal, fontSize=9, leading=11)
    medium_bold = ParagraphStyle("medium_bold", parent=normal, fontSize=9, leading=11, fontName="Helvetica-Bold")
    title_style = ParagraphStyle("title", parent=normal, fontSize=12, leading=14, fontName="Helvetica-Bold", alignment=1)

    month_name = calendar.month_name[data.chart_month]
    days_in_month = calendar.monthrange(data.chart_year, data.chart_month)[1]
    day_labels = [str(d) for d in range(1, days_in_month + 1)]

    def build_page(meds_slice: List[Medication], page_label: str) -> list:
        story = []

        # ---- Title ----
        story.append(Paragraph(
            f"MEDICATION ADMINISTRATION RECORD (MAR) — {month_name} {data.chart_year}  |  {page_label}",
            title_style,
        ))
        story.append(Spacer(1, 4 * mm))

        # ---- Patient / Organisation info ----
        info_data = [
            [
                Paragraph("<b>Patient Name:</b>", small_bold),
                Paragraph(data.patient_name, small),
                Paragraph("<b>Date of Birth:</b>", small_bold),
                Paragraph(data.patient_dob, small),
                Paragraph("<b>Patient ID / NHS No:</b>", small_bold),
                Paragraph(data.patient_id, small),
            ],
            [
                Paragraph("<b>Allergies / ADRs:</b>", small_bold),
                Paragraph(data.allergies or "None known", small),
                Paragraph("<b>Prescribing Organisation:</b>", small_bold),
                Paragraph(data.org_name, small),
                Paragraph("<b>Prescriber:</b>", small_bold),
                Paragraph(data.prescriber_name, small),
            ],
            [
                Paragraph("", small),
                Paragraph("", small),
                Paragraph("<b>Address:</b>", small_bold),
                Paragraph(data.org_address, small),
                Paragraph("", small),
                Paragraph("", small),
            ],
        ]
        info_col_widths = [30 * mm, 50 * mm, 35 * mm, 55 * mm, 30 * mm, 50 * mm]
        info_table = Table(info_data, colWidths=info_col_widths)
        info_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f4fa")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 4 * mm))

        # ---- Medication grid ----
        header_col_widths = _build_med_grid(
            story, meds_slice, day_labels, days_in_month, small, small_bold, medium_bold, page_w
        )

        # ---- Signature key ----
        story.append(Spacer(1, 4 * mm))
        key_data = [[
            Paragraph("<b>KEY:</b>", small_bold),
            Paragraph("✓ = Administered", small),
            Paragraph("X = Not given (see notes)", small),
            Paragraph("R = Refused", small),
            Paragraph("H = Hospital / Away", small),
            Paragraph("S = Self-administered", small),
        ]]
        key_table = Table(key_data, colWidths=[15 * mm, 40 * mm, 50 * mm, 30 * mm, 40 * mm, 40 * mm])
        key_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbe6")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(key_table)
        return story

    def _build_med_grid(story, meds, day_labels, days_in_month, small, small_bold, medium_bold, page_w):
        # Fixed left columns: Med name, Dose, Route, Start, End, Round
        left_col_widths = [38 * mm, 18 * mm, 16 * mm, 16 * mm, 16 * mm, 14 * mm]
        left_total = sum(left_col_widths)
        available = page_w - 20 * mm - left_total  # margins
        day_col_w = max(available / days_in_month, 5 * mm)
        day_col_widths = [day_col_w] * days_in_month

        all_col_widths = left_col_widths + day_col_widths

        # Header row
        header_row = [
            Paragraph("<b>Medication / Instructions</b>", small_bold),
            Paragraph("<b>Dose</b>", small_bold),
            Paragraph("<b>Route</b>", small_bold),
            Paragraph("<b>Start</b>", small_bold),
            Paragraph("<b>End</b>", small_bold),
            Paragraph("<b>Round</b>", small_bold),
        ] + [Paragraph(f"<b>{d}</b>", small_bold) for d in day_labels]

        table_data = [header_row]
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5f8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]

        row_idx = 1
        for med_i, med in enumerate(meds):
            rounds_to_show = med.rounds if med.rounds else ["—"]
            alt_bg = colors.HexColor("#eaf3fb") if med_i % 2 == 0 else colors.HexColor("#f8f8ff")

            for r_idx, rnd in enumerate(rounds_to_show):
                is_first = r_idx == 0
                med_cell = Paragraph(
                    f"<b>{med.name}</b><br/><font size='6'>{med.instructions}</font>" if is_first and med.instructions else (f"<b>{med.name}</b>" if is_first else ""),
                    small,
                )
                dose_cell = Paragraph(med.dose if is_first else "", small)
                route_cell = Paragraph(med.route if is_first else "", small)
                start_cell = Paragraph(med.start_date if is_first else "", small)
                end_cell = Paragraph(med.end_date if is_first else "", small)
                round_cell = Paragraph(ROUND_SHORT.get(rnd, rnd), small)
                day_cells = [""] * days_in_month

                data_row = [med_cell, dose_cell, route_cell, start_cell, end_cell, round_cell] + day_cells
                table_data.append(data_row)

                style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), alt_bg))
                row_idx += 1

            # Divider line after each medication
            if med_i < len(meds) - 1:
                style_cmds.append(("LINEBELOW", (0, row_idx - 1), (-1, row_idx - 1), 1, colors.HexColor("#2c5f8a")))

        # Add empty rows for blank medications if fewer than 3
        empty_count = len(meds)
        while empty_count < 3:
            for rnd in ROUNDS:
                empty_row = ["", "", "", "", "", ROUND_SHORT[rnd]] + [""] * days_in_month
                table_data.append(empty_row)
                style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#f8f8ff")))
                row_idx += 1
            # blank divider
            style_cmds.append(("LINEBELOW", (0, row_idx - 1), (-1, row_idx - 1), 0.5, colors.grey))
            empty_count += 1

        grid_table = Table(table_data, colWidths=all_col_widths, repeatRows=1)
        grid_table.setStyle(TableStyle(style_cmds))
        story.append(grid_table)

    # --- Build front (meds 0-2) and back (meds 3-5) pages ---
    all_meds = data.medications
    front_meds = all_meds[:3]
    back_meds = all_meds[3:6]

    story_all = build_page(list(front_meds), "Page 1 of 2 — Front")

    if back_meds:
        from reportlab.platypus import PageBreak
        story_all.append(PageBreak())
        story_all.extend(build_page(list(back_meds), "Page 2 of 2 — Back"))

    doc.build(story_all)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Word document generation (python-docx)
# ---------------------------------------------------------------------------

def generate_word(data: MARData) -> bytes:
    from docx import Document
    from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor, Cm

    def set_cell_bg(cell, hex_color: str):
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color)
        tcPr.append(shd)

    def set_cell_borders(cell, **kwargs):
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcBorders = OxmlElement("w:tcBorders")
        for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
            border_el = OxmlElement(f"w:{side}")
            border_el.set(qn("w:val"), kwargs.get(side, "single"))
            border_el.set(qn("w:sz"), str(kwargs.get("sz", 4)))
            border_el.set(qn("w:space"), "0")
            border_el.set(qn("w:color"), kwargs.get("color", "000000"))
            tcBorders.append(border_el)
        tcPr.append(tcBorders)

    def cell_para(cell, text: str, bold=False, size=7, color=None, align=WD_ALIGN_PARAGRAPH.LEFT):
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = align
        run = p.add_run(text)
        run.bold = bold
        run.font.size = Pt(size)
        if color:
            run.font.color.rgb = RGBColor(*color)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        return run

    month_name = calendar.month_name[data.chart_month]
    days_in_month = calendar.monthrange(data.chart_year, data.chart_month)[1]

    def build_doc_page(doc: Document, meds_slice: list, page_label: str, add_break: bool = False):
        if add_break:
            doc.add_page_break()

        # Title
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_para.add_run(
            f"MEDICATION ADMINISTRATION RECORD (MAR) — {month_name} {data.chart_year}  |  {page_label}"
        )
        run.bold = True
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(44, 95, 138)

        # Info table: 3 rows × 6 cols
        info_tbl = doc.add_table(rows=3, cols=6)
        info_tbl.style = "Table Grid"
        info_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        labels = [
            ("Patient Name:", data.patient_name, "Date of Birth:", data.patient_dob, "Patient ID / NHS No:", data.patient_id),
            ("Allergies / ADRs:", data.allergies or "None known", "Prescribing Organisation:", data.org_name, "Prescriber:", data.prescriber_name),
            ("", "", "Address:", data.org_address, "", ""),
        ]
        for r_i, row_vals in enumerate(labels):
            row = info_tbl.rows[r_i]
            for c_i, val in enumerate(row_vals):
                cell = row.cells[c_i]
                is_label = c_i % 2 == 0
                cell_para(cell, val, bold=is_label, size=7)
                set_cell_bg(cell, "F0F4FA" if is_label else "FFFFFF")

        doc.add_paragraph()

        # Medication grid
        # Columns: Medication | Dose | Route | Start | End | Round | day1..dayN
        n_cols = 6 + days_in_month
        med_tbl = doc.add_table(rows=1, cols=n_cols)
        med_tbl.style = "Table Grid"

        # Set narrow column widths
        col_widths_cm = [4.5, 2.0, 1.8, 1.8, 1.8, 1.5]
        avail_cm = 25.0 - sum(col_widths_cm)
        day_w = max(avail_cm / days_in_month, 0.5)

        for i, col in enumerate(med_tbl.columns):
            width = col_widths_cm[i] if i < 6 else day_w
            for cell in col.cells:
                cell.width = Cm(width)

        # Header
        header_cells = med_tbl.rows[0].cells
        headers = ["Medication / Instructions", "Dose", "Route", "Start", "End", "Round"] + [str(d) for d in range(1, days_in_month + 1)]
        for c_i, h in enumerate(headers):
            cell = header_cells[c_i]
            cell_para(cell, h, bold=True, size=7, color=(255, 255, 255), align=WD_ALIGN_PARAGRAPH.CENTER)
            set_cell_bg(cell, "2C5F8A")

        # Rows
        for med_i, med in enumerate(meds_slice):
            if med is None:
                rounds_to_show = ROUNDS
                med_name = ""
                dose = ""
                route = ""
                start = ""
                end = ""
                instructions = ""
            else:
                rounds_to_show = med.rounds if med.rounds else ["—"]
                med_name = med.name
                dose = med.dose
                route = med.route
                start = med.start_date
                end = med.end_date
                instructions = med.instructions
            alt_bg = "EAF3FB" if med_i % 2 == 0 else "F8F8FF"

            for r_idx, rnd in enumerate(rounds_to_show):
                is_first = r_idx == 0
                row = med_tbl.add_row()
                cells = row.cells
                cell_para(cells[0], (med_name + (f"\n{instructions}" if instructions else "")) if is_first else "", bold=is_first, size=7)
                cell_para(cells[1], dose if is_first else "", size=7, align=WD_ALIGN_PARAGRAPH.CENTER)
                cell_para(cells[2], route if is_first else "", size=7, align=WD_ALIGN_PARAGRAPH.CENTER)
                cell_para(cells[3], start if is_first else "", size=7, align=WD_ALIGN_PARAGRAPH.CENTER)
                cell_para(cells[4], end if is_first else "", size=7, align=WD_ALIGN_PARAGRAPH.CENTER)
                cell_para(cells[5], ROUND_SHORT.get(rnd, rnd), size=7, align=WD_ALIGN_PARAGRAPH.CENTER)
                for d in range(days_in_month):
                    cell_para(cells[6 + d], "", size=6, align=WD_ALIGN_PARAGRAPH.CENTER)
                for c_i in range(n_cols):
                    set_cell_bg(cells[c_i], alt_bg)

        # Key
        doc.add_paragraph()
        key_para = doc.add_paragraph()
        key_para.add_run("KEY:  ").bold = True
        key_para.add_run("✓ = Administered   X = Not given (see notes)   R = Refused   H = Hospital/Away   S = Self-administered")
        key_para.runs[-1].font.size = Pt(7)

    doc = Document()
    # Set landscape A4
    from docx.oxml.ns import qn as ns_qn
    section = doc.sections[0]
    section.page_width = Inches(11.69)
    section.page_height = Inches(8.27)
    section.left_margin = Cm(1)
    section.right_margin = Cm(1)
    section.top_margin = Cm(1)
    section.bottom_margin = Cm(1)

    all_meds = data.medications
    front_meds = list(all_meds[:3])
    back_meds = list(all_meds[3:6])

    # Pad front_meds to 3 with None
    while len(front_meds) < 3:
        front_meds.append(None)

    build_doc_page(doc, front_meds, "Page 1 of 2 — Front", add_break=False)

    if any(m is not None for m in back_meds):
        back_meds_padded = list(back_meds)
        while len(back_meds_padded) < 3:
            back_meds_padded.append(None)
        build_doc_page(doc, back_meds_padded, "Page 2 of 2 — Back", add_break=True)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
