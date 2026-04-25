"""
MAR Chart Generator – AYP Healthcare format

Front page : Medication Administration Record Sheet
             Weekly grid (4 weeks × 7 days), EARLY/MORNI/LUNCH/TEA/NIGHT rounds,
             up to 3 medications per page.
Back page  : Carers Medication Notes table
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROUNDS = ["EARLY", "MORNI", "LUNCH", "TEA", "NIGHT"]
DAY_ABBRS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

# All body zones that can be highlighted on the body map
BODY_ZONES = [
    "Head", "Neck",
    "Left Shoulder", "Right Shoulder",
    "Chest", "Abdomen", "Back",
    "Left Arm", "Right Arm",
    "Left Hand", "Right Hand",
    "Left Hip", "Right Hip",
    "Left Thigh", "Right Thigh",
    "Left Lower Leg", "Right Lower Leg",
    "Left Foot", "Right Foot",
]


@dataclass
class Medication:
    name: str
    dose: str
    route: str
    end_date: str = ""
    rounds: List[str] = field(default_factory=lambda: list(ROUNDS))
    instructions: str = ""
    container: str = ""              # e.g. "Separate container"
    application_sites: List[str] = field(default_factory=list)  # body-map zones


@dataclass
class MARData:
    patient_name: str         # e.g. "wilson, sherry (Mrs)"
    patient_dob: str          # e.g. "19/11/2000"
    nhs_number: str           # e.g. "4247393842"
    allergies: str            # e.g. "Adverse reaction to insulin"
    gender: str               # e.g. "Female"
    patient_address: str      # full address string
    doctor: str               # e.g. "Billy Barber"
    start_date: str           # "DD/MM/YYYY" – first date of the chart period
    patient_id: str           # e.g. "53486"
    room: str                 # e.g. "35"
    org_name: str             # shown at top centre, e.g. "AYP Healthcare"
    org_address: str          # newline-separated address lines
    prescribing_org: str      # e.g. "Enathu medical practice"
    document_no: str          # e.g. "MAR-001"
    pharmacy_no: str          # e.g. "FKD50"
    phone: str                # e.g. "0208 344 0500"
    medications: List[Medication] = field(default_factory=list)



# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _parse_start_date(date_str: str) -> date:
    """Parse DD/MM/YYYY; fall back to today on error."""
    parts = date_str.strip().split("/")
    if len(parts) == 3:
        try:
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
        except (ValueError, IndexError):
            pass
    return date.today()


def _get_four_weeks(start_date_str: str) -> List[List[date]]:
    """Return 4 weeks (28 days) starting from the selected start date."""
    start = _parse_start_date(start_date_str)
    return [
        [start + timedelta(weeks=w, days=d) for d in range(7)]
        for w in range(4)
    ]


def _format_start_date(date_str: str) -> str:
    """Return 'Friday 27 December 2025' from a DD/MM/YYYY string."""
    d = _parse_start_date(date_str)
    return f"{d.strftime('%A')} {d.day} {d.strftime('%B %Y')}"


def _format_period(start_date_str: str) -> str:
    """Return date span for the 4-week grid from the selected start date."""
    weeks = _get_four_weeks(start_date_str)
    s, e = weeks[0][0], weeks[3][6]
    return f"{s.day} {s.strftime('%b %Y')} \u2013 {e.day} {e.strftime('%b %Y')}"


# ---------------------------------------------------------------------------
# PDF generation (reportlab)
# ---------------------------------------------------------------------------

def generate_pdf(data: MARData) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    buf = io.BytesIO()
    pw, _ph = landscape(A4)   # 841.89 × 595.27 pt
    marg = 10 * mm
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=marg, rightMargin=marg,
        topMargin=marg, bottomMargin=marg,
    )
    usable_w = pw - 2 * marg   # ~821 pt

    # ---- Style factory (unique names avoid reportlab cache warnings) ----
    _sty_cache: dict = {}

    def sty(name: str, size: float = 7, bold: bool = False, align: int = 0) -> ParagraphStyle:
        key = (name, size, bold, align)
        if key not in _sty_cache:
            fn = "Helvetica-Bold" if bold else "Helvetica"
            _sty_cache[key] = ParagraphStyle(
                name, fontName=fn, fontSize=size,
                leading=size * 1.3, alignment=align,
            )
        return _sty_cache[key]

    def p(text: str, style: ParagraphStyle = None) -> Paragraph:
        return Paragraph(str(text), style or sty("t7"))

    # Pre-build commonly used styles
    t5bc = sty("t5bc", 6, bold=True, align=1)
    t6   = sty("t6",   6.2, bold=True)
    t6b  = sty("t6b",  6,  bold=True)
    t6bc = sty("t6bc", 6,  bold=True, align=1)
    t7   = sty("t7",   7,  bold=True)
    t7b  = sty("t7b",  7,  bold=True)
    t7bc = sty("t7bc", 7,  bold=True, align=1)
    t9b  = sty("t9b",  9,  bold=True)
    t14b = sty("t14b", 14, bold=True, align=1)

    # ---- Week dates ----
    weeks = _get_four_weeks(data.start_date)
    all_dates = [d for week in weeks for d in week]   # 28 dates

    # ---- Column widths for the 31-column medication grid ----
    # col 0 = medication description, col 1 = round label,
    # col 2 = dose, cols 3-30 = 28 day cells
    med_w  = 60 * mm
    rnd_w  = 10.5 * mm
    dose_w = 13 * mm
    day_w  = max((usable_w - med_w - rnd_w - dose_w) / 28, 5.5 * mm)
    grid_col_w = [med_w, rnd_w, dose_w] + [day_w] * 28
    total_grid_w = sum(grid_col_w)

    # ================================================================
    # Received / Returned / Destroyed nested table
    # ================================================================
    def _make_received_row() -> Table:
        props = [0.09, 0.065, 0.04, 0.04,
                 0.10,  0.07,  0.06, 0.18,
                 0.10,  0.065, 0.07, 0.065, 0.065]
        s = sum(props)
        cws = [total_grid_w * c / s for c in props]
        row = [[
            p("Received:", t6b), p("Qty:", t6b), p(""), p(""),
            p("Returned:", t6b), p("Qty:", t6b), p("By:", t6b), p(""),
            p("Destroyed:", t6b), p("Qty:", t6b), p(""), p("By:", t6b), p(""),
        ]]
        tbl = Table(row, colWidths=cws)
        tbl.setStyle(TableStyle([
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, colors.black),
            ("BOX",           (0, 0), (-1, -1), 0.5, colors.black),
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING",   (0, 0), (-1, -1), 2),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 2),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return tbl

    # ================================================================
    # Medication administration grid  (always 3 slots)
    # ================================================================
    def _build_med_grid(meds: list) -> Table:
        slots = (list(meds[:3]) + [None, None, None])[:3]
        N_HDR = 3
        slot_rows = len(ROUNDS) + 2
        N_ROWS = N_HDR + 3 * slot_rows
        NCOLS  = 31

        dg = [[""] * NCOLS for _ in range(N_ROWS)]
        sc = []    # style commands

        # Default styles
        sc += [
            ("BOX",           (0, 0), (-1, -1), 0.75, colors.black),
            ("INNERGRID",     (0, 0), (-1, -1), 0.25, colors.black),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING",   (0, 0), (-1, -1), 2),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 1),
        ]

        # ---- Header row 0: section labels ----
        dg[0][0]  = p("Medication Details", t7bc)
        dg[0][1]  = p("Commencing",         t7bc)
        dg[0][3]  = p("Week 1",  t7bc)
        dg[0][10] = p("Week 2",  t7bc)
        dg[0][17] = p("Week 3",  t7bc)
        dg[0][24] = p("Week 4",  t7bc)

        sc += [
            # "Medication Details" spans col 0, rows 0-2
            ("SPAN", (0,  0), (0,  2)),
            # "Commencing" spans cols 1-2, rows 0-1
            ("SPAN", (1,  0), (2,  1)),
            # Week headers: row 0 only (7 cols each starting at col 3)
            ("SPAN", (3,  0), (9,  0)),
            ("SPAN", (10, 0), (16, 0)),
            ("SPAN", (17, 0), (23, 0)),
            ("SPAN", (24, 0), (30, 0)),
            # Header background & alignment
            ("BACKGROUND", (0, 0), (-1, 2), colors.HexColor("#DDEEFF")),
            ("LINEBELOW",  (0, 2), (-1, 2), 1,  colors.black),
            ("ALIGN",      (0, 0), (-1, 2), "CENTER"),
        ]

        # ---- Header row 1: day-of-month numbers (start at col 3) ----
        dg[1][1] = p("Date", t6bc)
        for i, dt in enumerate(all_dates):
            dg[1][3 + i] = p(str(dt.day), t6bc)

        # ---- Header row 2: Hour/Dose + day abbreviations ----
        dg[2][1] = p("Hour", t6b)
        dg[2][2] = p("Dose", t6b)
        for i, dt in enumerate(all_dates):
            dg[2][3 + i] = p(DAY_ABBRS[dt.weekday()], t5bc)

        # ---- Medication slot rows ----
        for slot_idx, med in enumerate(slots):
            base = N_HDR + slot_idx * slot_rows

            # Medication description cell (col 0) spans all 4 round rows
            if med is not None:
                txt = f"<b>{med.name}</b>"
                if med.instructions:
                    txt += f"<br/><font size='5.5'>{med.instructions}</font>"
                if med.container:
                    txt += f"<br/><font size='5.5'><u><b>{med.container}</b></u></font>"
                dg[base][0] = p(txt, t6)

            sc += [
                ("SPAN",       (0, base), (0, base + len(ROUNDS) - 1)),
                ("VALIGN",     (0, base), (0, base + len(ROUNDS) - 1), "TOP"),
                ("TOPPADDING", (0, base), (0, base),     3),
            ]

            if med is not None and med.dose:
                dg[base][2] = p(med.dose, t6bc)
                sc += [
                    ("SPAN", (2, base), (2, base + len(ROUNDS) - 1)),
                    ("VALIGN", (2, base), (2, base + len(ROUNDS) - 1), "MIDDLE"),
                ]

            # Round label column
            for r_idx, rnd in enumerate(ROUNDS):
                dg[base + r_idx][1] = p(rnd, t6bc)

            # Thick line below round rows
            sc.append(("LINEBELOW", (0, base + len(ROUNDS) - 1), (-1, base + len(ROUNDS) - 1), 0.75, colors.black))

            # Extra blank row after rounds, then Received / Returned / Destroyed row
            rcvd = base + len(ROUNDS) + 1
            dg[rcvd][0] = _make_received_row()
            sc += [
                ("SPAN",          (0, rcvd), (30, rcvd)),
                ("TOPPADDING",    (0, rcvd), (-1, rcvd), 0),
                ("BOTTOMPADDING", (0, rcvd), (-1, rcvd), 0),
                ("LEFTPADDING",   (0, rcvd), (-1, rcvd), 0),
                ("RIGHTPADDING",  (0, rcvd), (-1, rcvd), 0),
            ]

        # Round-label column centred; day cells centred
        sc.append(("ALIGN", (1, N_HDR), (1,  -1), "CENTER"))
        sc.append(("ALIGN", (2, N_HDR), (2,  -1), "CENTER"))
        sc.append(("ALIGN", (3, N_HDR), (-1, -1), "CENTER"))

        # Keep rows compact enough to avoid front-page overflow with 5 rounds.
        row_heights = [5.2 * mm, 4.6 * mm, 4.6 * mm]
        for _ in range(3):
            row_heights.extend(([5.1 * mm] * len(ROUNDS)) + [3.8 * mm, 4.3 * mm])

        tbl = Table(dg, colWidths=grid_col_w, rowHeights=row_heights, repeatRows=N_HDR)
        tbl.setStyle(TableStyle(sc))
        return tbl

    # ================================================================
    # Patient information table
    # ================================================================
    def _build_patient_table() -> Table:
        w0 = usable_w * 0.41
        w1 = usable_w * 0.21
        w2 = usable_w * 0.18
        w3 = usable_w - w0 - w1 - w2

        pi = [
            [
                p(f"Name: {data.patient_name}", t7b),
                p(f"NHS Number: {data.nhs_number}", t7b),
                p(f"D.O.B.:  {data.patient_dob}", t7b),
                p(f"Gender: {data.gender}", t7b),
            ],
            [
                p(f"Allergies/Conditions: {data.allergies}", t7b),
                "", "",
                p(f"Doctor: {data.doctor}", t7b),
            ],
            [
                p(f"Address:    {data.patient_address}", t7b),
                "", "", "",
            ],
            [
                p(f"Start Date: {_format_start_date(data.start_date)}", t7b),
                p(f"Period:  {_format_period(data.start_date)}", t7b),
                p(f"Patient ID.  {data.patient_id}", t7b),
                p(f"Room: {data.room}", t7b),
            ],
            [
                p(f"Prescribing Organization: {data.prescribing_org}", t7b),
                "", "", "",
            ],
        ]

        style = TableStyle([
            ("BOX",          (0, 0), (-1, -1), 0.75, colors.black),
            ("INNERGRID",    (0, 0), (-1, -1), 0.5,  colors.black),
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",   (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
            ("LEFTPADDING",  (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            # Allergies spans cols 0-2
            ("SPAN", (0, 1), (2, 1)),
            # Address spans cols 0-2
            ("SPAN", (0, 2), (2, 2)),
            # Prescribing Org spans all 4 cols
            ("SPAN", (0, 4), (3, 4)),
        ])
        return Table(pi, colWidths=[w0, w1, w2, w3], style=style)

    # ================================================================
    # Document header  (Medication Administration | Org Name | Address)
    # ================================================================
    def _build_doc_header() -> Table:
        left_w  = 72 * mm
        cen_w   = 80 * mm
        right_w = usable_w - left_w - cen_w

        addr_html = data.org_address.replace("\n", "<br/>")
        if data.phone:
            addr_html += f"<br/>{data.phone}"
        if data.pharmacy_no:
            addr_html += f"<br/>Pharmacy No.: {data.pharmacy_no}"

        left_inner = Table(
            [
                [p("Medication Administration", t9b)],
                [p("Record Sheet",              t9b)],
                [Spacer(1, 1 * mm)],
                [p(f"Document No.: {data.document_no}", t7)],
            ],
            colWidths=[left_w],
            style=TableStyle([
                ("TOPPADDING",    (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ]),
        )

        hdr = Table(
            [[
                left_inner,
                p(data.org_name, t14b),
                p(addr_html, sty("r_addr", 7, align=1)),
            ]],
            colWidths=[left_w, cen_w, right_w],
            style=TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING",    (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ]),
        )
        return hdr

    # ================================================================
    # Back page – Carers Medication Notes
    # ================================================================
    def _build_back_page() -> list:
        els: list = []
        els.append(p("CARERS MEDICATION NOTES",
                      sty("notes_ttl", 12, bold=True, align=1)))
        els.append(Spacer(1, 6 * mm))

        col_names = [
            "DATE", "TIME", "INITIALS", "MEDICATION",
            "DOSE", "REASON", "RESULT", "TIME", "INITIALS",
        ]
        ratios = [0.07, 0.06, 0.08, 0.18, 0.08, 0.22, 0.15, 0.06, 0.10]
        s = sum(ratios)
        cws = [usable_w * r / s for r in ratios]

        rows: list = [[p(h, sty("nh_bc", 7, bold=True, align=1)) for h in col_names]]
        rows += [[""] * len(col_names) for _ in range(30)]

        tbl = Table(rows, colWidths=cws)
        tbl.setStyle(TableStyle([
            ("BOX",          (0, 0), (-1, -1), 1,   colors.black),
            ("INNERGRID",    (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN",        (0, 0), (-1, 0),  "CENTER"),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("LEFTPADDING",  (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("LINEBELOW",    (0, 0), (-1, 0),  1.5, colors.black),
            ("LINEAFTER",    (2, 0), (2, -1),  1.5, colors.black),
            ("LINEAFTER",    (5, 0), (5, -1),  1.5, colors.black),
            ("LINEAFTER",    (6, 0), (6, -1),  1.5, colors.black),
        ]))
        els.append(tbl)
        els.append(Spacer(1, 5 * mm))
        els.append(p(f"<b>AYP</b> {data.org_name}",
                     sty("ayp_br", 12, bold=False, align=2)))
        return els

    # ================================================================
    # Body Map diagram – custom Flowable
    # Draws FRONT and BACK human silhouettes side-by-side.
    # Zones listed in application_sites are filled with amber highlight.
    # ================================================================
    class _BodyMapDiagram(Flowable):
        """Two-view (front / back) body diagram with highlighted application zones."""

        # Zone tuples: (name, cx_frac, cy_frac, rx_frac, ry_frac)
        # cx/cy fractions are measured from the top-left of the figure box.
        _FRONT = [
            ("Head",            0.50, 0.07, 0.17, 0.07),
            ("Neck",            0.50, 0.16, 0.08, 0.025),
            ("Left Shoulder",   0.28, 0.22, 0.13, 0.05),
            ("Right Shoulder",  0.72, 0.22, 0.13, 0.05),
            ("Chest",           0.50, 0.32, 0.20, 0.08),
            ("Abdomen",         0.50, 0.46, 0.20, 0.08),
            ("Left Arm",        0.18, 0.37, 0.07, 0.12),
            ("Right Arm",       0.82, 0.37, 0.07, 0.12),
            ("Left Hand",       0.12, 0.56, 0.07, 0.04),
            ("Right Hand",      0.88, 0.56, 0.07, 0.04),
            ("Left Hip",        0.35, 0.58, 0.12, 0.05),
            ("Right Hip",       0.65, 0.58, 0.12, 0.05),
            ("Left Thigh",      0.34, 0.70, 0.10, 0.08),
            ("Right Thigh",     0.66, 0.70, 0.10, 0.08),
            ("Left Lower Leg",  0.34, 0.84, 0.09, 0.08),
            ("Right Lower Leg", 0.66, 0.84, 0.09, 0.08),
            ("Left Foot",       0.31, 0.95, 0.12, 0.03),
            ("Right Foot",      0.69, 0.95, 0.12, 0.03),
        ]
        _BACK = [
            ("Head",            0.50, 0.07, 0.17, 0.07),
            ("Neck",            0.50, 0.16, 0.08, 0.025),
            ("Left Shoulder",   0.28, 0.22, 0.13, 0.05),
            ("Right Shoulder",  0.72, 0.22, 0.13, 0.05),
            ("Back",            0.50, 0.39, 0.20, 0.14),
            ("Left Arm",        0.18, 0.37, 0.07, 0.12),
            ("Right Arm",       0.82, 0.37, 0.07, 0.12),
            ("Left Hand",       0.12, 0.56, 0.07, 0.04),
            ("Right Hand",      0.88, 0.56, 0.07, 0.04),
            ("Left Hip",        0.35, 0.58, 0.12, 0.05),
            ("Right Hip",       0.65, 0.58, 0.12, 0.05),
            ("Left Thigh",      0.34, 0.70, 0.10, 0.08),
            ("Right Thigh",     0.66, 0.70, 0.10, 0.08),
            ("Left Lower Leg",  0.34, 0.84, 0.09, 0.08),
            ("Right Lower Leg", 0.66, 0.84, 0.09, 0.08),
            ("Left Foot",       0.31, 0.95, 0.12, 0.03),
            ("Right Foot",      0.69, 0.95, 0.12, 0.03),
        ]

        _AMBER_HIGHLIGHT = colors.HexColor("#FF8C00")
        _HL_STROKE = colors.HexColor("#CC5500")
        _ZONE_FILL = colors.HexColor("#DDE8F5")
        _ZONE_STROKE = colors.HexColor("#6688AA")
        _LBL_H = 14     # pt: space above each figure for the FRONT / BACK label
        _FIG_W = 155    # pt: width of each silhouette figure
        _FIG_H = 265    # pt: height of each silhouette figure
        _GAP   = 22     # pt: horizontal gap between the two figures
        _ZONE_LABEL_FONT_SIZE = 3.8  # pt: label text inside each zone ellipse

        def __init__(self, application_sites):
            super().__init__()
            self.sites = set(application_sites)
            self.width  = 2 * self._FIG_W + self._GAP
            self.height = self._LBL_H + self._FIG_H

        def _draw_figure(self, c, ox, oy_base, zones):
            """Draw one silhouette (front or back) at canvas offset (ox, oy_base).
            oy_base is the bottom of the figure area (ReportLab y is bottom-up)."""
            fig_h = self._FIG_H
            fig_w = self._FIG_W
            for (name, cx_f, cy_f, rx_f, ry_f) in zones:
                cx = ox + cx_f * fig_w
                # Convert top-down cy_frac → bottom-up canvas y
                cy = oy_base + fig_h * (1.0 - cy_f)
                rx = rx_f * fig_w
                ry = ry_f * fig_h
                if name in self.sites:
                    c.setFillColor(self._AMBER_HIGHLIGHT)
                    c.setStrokeColor(self._HL_STROKE)
                    c.setLineWidth(1.2)
                else:
                    c.setFillColor(self._ZONE_FILL)
                    c.setStrokeColor(self._ZONE_STROKE)
                    c.setLineWidth(0.5)
                c.ellipse(cx - rx, cy - ry, cx + rx, cy + ry, fill=1)
                # zone label
                c.setFillColor(colors.black)
                font_sz = self._ZONE_LABEL_FONT_SIZE
                c.setFont("Helvetica", font_sz)
                # short abbreviations for narrow zones
                short = name.replace("Left ", "L.").replace("Right ", "R.")
                c.drawCentredString(cx, cy - font_sz * 0.45, short)

        def draw(self):
            c = self.canv
            fig_y_base = 0       # bottom of figure area
            label_y    = self._FIG_H + self._LBL_H * 0.3

            for idx, (view_label, zones) in enumerate(
                [("FRONT VIEW", self._FRONT), ("BACK VIEW", self._BACK)]
            ):
                ox = idx * (self._FIG_W + self._GAP)
                # View label centred above figure
                c.setFont("Helvetica-Bold", 7)
                c.setFillColor(colors.HexColor("#2C5F8A"))
                c.drawCentredString(ox + self._FIG_W / 2, label_y, view_label)
                # Draw outer bounding box for the figure
                c.setStrokeColor(colors.HexColor("#AABBCC"))
                c.setLineWidth(0.4)
                c.rect(ox, fig_y_base, self._FIG_W, self._FIG_H, fill=0)
                self._draw_figure(c, ox, fig_y_base, zones)

    # ================================================================
    # Body Map eMAR page  – completely separate page per topical med
    # ================================================================
    def _build_body_map_page(med: Medication) -> list:
        els: list = []

        # ---- Page title ----
        els.append(p(
            f"<b>BODY MAP – TOPICAL CREAM APPLICATION RECORD</b>",
            sty("bm_ttl", 11, bold=True, align=1),
        ))
        els.append(Spacer(1, 3 * mm))

        # ---- Patient + medication mini-header ----
        hdr_style = TableStyle([
            ("BOX",           (0, 0), (-1, -1), 0.75, colors.black),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5,  colors.black),
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#DDE8F5")),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ])
        mini_hdr_data = [[
            p(f"<b>Patient:</b> {data.patient_name}", t7b),
            p(f"<b>DOB:</b> {data.patient_dob}", t7b),
            p(f"<b>NHS No:</b> {data.nhs_number}", t7b),
            p(f"<b>Room:</b> {data.room}", t7b),
        ], [
            p(f"<b>Medication:</b> {med.name}", t7b),
            p(f"<b>Dose:</b> {med.dose}", t7b),
            p(f"<b>Route:</b> {med.route}", t7b),
            p(f"<b>Doctor:</b> {data.doctor}", t7b),
        ]]
        w_each = usable_w / 4
        mini_hdr = Table(mini_hdr_data, colWidths=[w_each] * 4, style=hdr_style)
        els.append(mini_hdr)
        els.append(Spacer(1, 3 * mm))

        # ---- Middle: diagram (left) + highlighted zones legend (right) ----
        diagram = _BodyMapDiagram(med.application_sites)

        # Legend: list of all zones, highlighted ones shown in amber
        legend_rows = []
        legend_title_style = sty("bm_leg_ttl", 7, bold=True)
        legend_rows.append([p("<b>Application Site(s)</b>", legend_title_style)])
        for zone in BODY_ZONES:
            if zone in med.application_sites:
                zone_sty = sty(f"bm_z_hl_{zone}", 7, bold=True)
                txt = f'<font color="#CC5500">● {zone}</font>'
            else:
                zone_sty = sty(f"bm_z_{zone}", 7)
                txt = f'<font color="#888888">○ {zone}</font>'
            legend_rows.append([p(txt, zone_sty)])

        if med.instructions:
            legend_rows.append([p("", t7)])
            legend_rows.append([p(f"<b>Instructions:</b>", t7b)])
            legend_rows.append([p(med.instructions, t7)])

        legend_tbl = Table(legend_rows, colWidths=[usable_w - diagram.width - 8 * mm])
        legend_tbl.setStyle(TableStyle([
            ("TOPPADDING",    (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("LINEBELOW",     (0, 0), (-1, 0),  0.75, colors.HexColor("#2C5F8A")),
        ]))

        mid_tbl = Table(
            [[diagram, Spacer(8 * mm, 1), legend_tbl]],
            colWidths=[diagram.width, 8 * mm, usable_w - diagram.width - 8 * mm],
        )
        mid_tbl.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ]))
        els.append(mid_tbl)
        els.append(Spacer(1, 4 * mm))

        # ---- eMAR log table ----
        els.append(p("<b>ADMINISTRATION LOG</b>", sty("bm_log_ttl", 8, bold=True)))
        els.append(Spacer(1, 2 * mm))

        log_cols = ["DATE", "TIME", "SITE(S) APPLIED", "SKIN CONDITION",
                    "AMOUNT APPLIED", "CARER INITIALS", "SIGNATURE"]
        log_ratios = [0.10, 0.08, 0.22, 0.18, 0.14, 0.13, 0.15]
        s = sum(log_ratios)
        log_cws = [usable_w * r / s for r in log_ratios]

        log_hdr = [p(h, sty(f"bm_lh_{h}", 7, bold=True, align=1)) for h in log_cols]
        log_rows = [log_hdr] + [[""] * len(log_cols) for _ in range(22)]

        log_tbl = Table(log_rows, colWidths=log_cws)
        log_tbl.setStyle(TableStyle([
            ("BOX",           (0, 0), (-1, -1), 0.75, colors.black),
            ("INNERGRID",     (0, 0), (-1, -1), 0.4,  colors.black),
            ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#DDE8F5")),
            ("LINEBELOW",     (0, 0), (-1, 0),  1.2,  colors.black),
            ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 2),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 2),
        ]))
        els.append(log_tbl)
        els.append(Spacer(1, 4 * mm))
        els.append(p(f"<b>AYP</b> {data.org_name}",
                     sty("bm_brand", 9, bold=False, align=2)))
        return els

    # ================================================================
    # Assemble story
    # ================================================================
    legend = (
        "<b>R</b> \u2013 Refused \u00a0\u00a0 "
        "<b>B</b> \u2013 Nausea or Vomiting \u00a0\u00a0 "
        "<b>C</b> \u2013 Hospitalized \u00a0\u00a0 "
        "<b>D</b> \u2013 Social Leave \u00a0\u00a0 "
        "<b>E</b> \u2013 Refused &amp; Destroyed \u00a0\u00a0 "
        "<b>F</b>: Other (define) :"
    )

    story: list = []
    # --- Front page ---
    story.append(_build_doc_header())
    story.append(Spacer(1, 3 * mm))
    story.append(_build_patient_table())
    story.append(Spacer(1, 3 * mm))
    story.append(_build_med_grid(data.medications[:3]))
    story.append(Spacer(1, 2 * mm))
    story.append(p(legend, t7))

    # --- Back page: Carers Medication Notes ---
    story.append(PageBreak())
    story.extend(_build_back_page())

    # --- Body Map pages: one separate page per medication with application sites ---
    for med in data.medications:
        if med.application_sites:
            story.append(PageBreak())
            story.extend(_build_body_map_page(med))

    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Word document generation (python-docx)
# ---------------------------------------------------------------------------

def generate_word(data: MARData) -> bytes:
    from docx import Document
    from docx.enum.table import WD_ALIGN_VERTICAL, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    weeks = _get_four_weeks(data.start_date)
    all_dates = [d for week in weeks for d in week]

    doc = Document()
    section = doc.sections[0]
    section.page_width   = Cm(29.7)
    section.page_height  = Cm(21.0)
    section.left_margin  = section.right_margin  = Cm(1.0)
    section.top_margin   = section.bottom_margin = Cm(1.0)
    usable_cm = 27.7

    # ---- Helpers ----

    def _cell_write(cell, text: str, bold: bool = False, size: float = 7,
                    align: WD_ALIGN_PARAGRAPH = WD_ALIGN_PARAGRAPH.LEFT,
                    color=None) -> None:
        cell.text = ""
        para = cell.paragraphs[0]
        para.alignment = align
        if text:
            run = para.add_run(str(text))
            run.bold = bold
            run.font.size = Pt(size)
            if color:
                run.font.color.rgb = RGBColor(*color)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    def _set_bg(cell, hex_color: str) -> None:
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color)
        tcPr.append(shd)

    def _remove_borders(cell) -> None:
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcB = OxmlElement("w:tcBorders")
        for side in ("top", "left", "bottom", "right"):
            el = OxmlElement(f"w:{side}")
            el.set(qn("w:val"), "none")
            tcB.append(el)
        tcPr.append(tcB)

    CENTER = WD_ALIGN_PARAGRAPH.CENTER
    LEFT   = WD_ALIGN_PARAGRAPH.LEFT
    RIGHT  = WD_ALIGN_PARAGRAPH.RIGHT
    HEADER_BG = "DDEEFF"

    # ================================================================
    # Document header  (3-column borderless table)
    # ================================================================
    hdr_tbl = doc.add_table(rows=1, cols=3)
    hdr_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    lw = Cm(7.2); cw_h = Cm(8.0); rw = Cm(usable_cm) - lw - cw_h
    hdr_cells = hdr_tbl.rows[0].cells
    hdr_cells[0].width = lw
    hdr_cells[1].width = cw_h
    hdr_cells[2].width = rw

    # Left: titles + document number
    p0 = hdr_cells[0].paragraphs[0]
    r0 = p0.add_run("Medication Administration\n")
    r0.bold = True; r0.font.size = Pt(9)
    r1 = p0.add_run("Record Sheet\n")
    r1.bold = True; r1.font.size = Pt(9)
    r2 = p0.add_run(f"Document No.: {data.document_no}")
    r2.font.size = Pt(7)

    # Centre: organisation name
    _cell_write(hdr_cells[1], data.org_name, bold=True, size=14, align=CENTER)

    # Right: address block
    addr = data.org_address
    if data.phone:
        addr += f"\n{data.phone}"
    if data.pharmacy_no:
        addr += f"\nPharmacy No.: {data.pharmacy_no}"
    _cell_write(hdr_cells[2], addr, size=7, align=CENTER)

    for cell in hdr_cells:
        _remove_borders(cell)

    doc.add_paragraph()

    # ================================================================
    # Patient information table  (5 rows × 4 cols)
    # ================================================================
    pi_tbl = doc.add_table(rows=5, cols=4)
    pi_tbl.style = "Table Grid"
    pi_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    pi_cws = [Cm(usable_cm * r) for r in (0.41, 0.21, 0.18, 0.20)]
    for c_i, cw in enumerate(pi_cws):
        for row in pi_tbl.rows:
            row.cells[c_i].width = cw

    pi_rows_data = [
        [f"Name: {data.patient_name}", f"NHS Number: {data.nhs_number}",
         f"D.O.B.: {data.patient_dob}", f"Gender: {data.gender}"],
        [f"Allergies/Conditions: {data.allergies}", None, None,
         f"Doctor: {data.doctor}"],
        [f"Address: {data.patient_address}", None, None, ""],
        [f"Start Date: {_format_start_date(data.start_date)}",
         f"Period: {_format_period(data.start_date)}",
         f"Patient ID. {data.patient_id}", f"Room: {data.room}"],
        [f"Prescribing Organization: {data.prescribing_org}", None, None, None],
    ]
    for r_i, row_data in enumerate(pi_rows_data):
        row = pi_tbl.rows[r_i]
        for c_i, txt in enumerate(row_data):
            if txt is not None:
                _cell_write(row.cells[c_i], txt, bold=True, size=7)

    # Merge spans
    pi_tbl.rows[1].cells[0].merge(pi_tbl.rows[1].cells[2])  # Allergies
    pi_tbl.rows[2].cells[0].merge(pi_tbl.rows[2].cells[2])  # Address
    pi_tbl.rows[4].cells[0].merge(pi_tbl.rows[4].cells[3])  # Prescribing Org

    doc.add_paragraph()

    # ================================================================
    # Medication administration grid  (31 cols, dynamic round rows)
    # ================================================================
    N_HDR  = 3
    slot_rows = len(ROUNDS) + 2
    N_ROWS = N_HDR + 3 * slot_rows
    NCOLS  = 31

    med_tbl = doc.add_table(rows=N_ROWS, cols=NCOLS)
    med_tbl.style = "Table Grid"
    med_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT

    # Column widths (no Hour column)
    med_w_cm  = 6.0
    rnd_w_cm  = 1.05
    dose_w_cm = 1.3
    day_w_cm  = max((usable_cm - med_w_cm - rnd_w_cm - dose_w_cm) / 28, 0.55)
    col_w_list = [med_w_cm, rnd_w_cm, dose_w_cm] + [day_w_cm] * 28

    for c_i, cw in enumerate(col_w_list):
        for r_i in range(N_ROWS):
            med_tbl.rows[r_i].cells[c_i].width = Cm(cw)

    # Keep rows compact enough to avoid front-page overflow with 5 rounds.
    med_tbl.rows[0].height = Cm(0.52)
    med_tbl.rows[1].height = Cm(0.46)
    med_tbl.rows[2].height = Cm(0.46)
    med_tbl.rows[0].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    med_tbl.rows[1].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    med_tbl.rows[2].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    for i in range(3, N_ROWS):
        slot_pos = (i - N_HDR) % slot_rows
        if slot_pos == len(ROUNDS):
            med_tbl.rows[i].height = Cm(0.38)
        elif slot_pos == len(ROUNDS) + 1:
            med_tbl.rows[i].height = Cm(0.43)
        else:
            med_tbl.rows[i].height = Cm(0.51)
        med_tbl.rows[i].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY

    # ---- Header spans ----
    # "Medication Details" col 0, rows 0-2
    med_tbl.cell(0, 0).merge(med_tbl.cell(2, 0))
    _cell_write(med_tbl.cell(0, 0), "Medication Details",
                bold=True, size=7, align=CENTER)
    _set_bg(med_tbl.cell(0, 0), HEADER_BG)

    # "Commencing" cols 1-2, rows 0-1
    med_tbl.cell(0, 1).merge(med_tbl.cell(1, 2))
    _cell_write(med_tbl.cell(0, 1), "Commencing",
                bold=True, size=7, align=CENTER)
    _set_bg(med_tbl.cell(0, 1), HEADER_BG)

    # Date/Hour/Dose labels
    _cell_write(med_tbl.cell(1, 1), "Date", bold=True, size=6, align=CENTER)
    _set_bg(med_tbl.cell(1, 1), HEADER_BG)
    _cell_write(med_tbl.cell(2, 1), "Hour", bold=True, size=6, align=CENTER)
    _set_bg(med_tbl.cell(2, 1), HEADER_BG)
    _cell_write(med_tbl.cell(2, 2), "Dose", bold=True, size=6, align=CENTER)
    _set_bg(med_tbl.cell(2, 2), HEADER_BG)

    # Keep row-2 col-2 for dose only and clear row-1 col-2
    _cell_write(med_tbl.cell(1, 2), "", bold=False, size=6, align=CENTER)

    # Week headers (row 0, 7 cols each, starting at col 3)
    for w_idx, wlabel in enumerate(["Week 1", "Week 2", "Week 3", "Week 4"]):
        sc = 3 + w_idx * 7
        med_tbl.cell(0, sc).merge(med_tbl.cell(0, sc + 6))
        _cell_write(med_tbl.cell(0, sc), wlabel, bold=True, size=7, align=CENTER)
        _set_bg(med_tbl.cell(0, sc), HEADER_BG)

    # Date numbers (row 1) and day abbreviations (row 2) starting at col 3
    for i, dt in enumerate(all_dates):
        col = 3 + i
        _cell_write(med_tbl.cell(1, col), str(dt.day), bold=True, size=6, align=CENTER)
        _set_bg(med_tbl.cell(1, col), HEADER_BG)
        _cell_write(med_tbl.cell(2, col), DAY_ABBRS[dt.weekday()],
                    bold=True, size=5, align=CENTER)
        _set_bg(med_tbl.cell(2, col), HEADER_BG)

    # ---- Medication slots ----
    slots = (list(data.medications[:3]) + [None, None, None])[:3]
    for slot_idx, med in enumerate(slots):
        base = N_HDR + slot_idx * slot_rows

        # Medication description spans rows base..base+len(ROUNDS)-1 in col 0
        med_tbl.cell(base, 0).merge(med_tbl.cell(base + len(ROUNDS) - 1, 0))
        if med is not None:
            cell = med_tbl.cell(base, 0)
            cell.text = ""
            para = cell.paragraphs[0]
            name_run = para.add_run(med.name)
            name_run.bold = True
            name_run.font.size = Pt(7)

            if med.instructions:
                para.add_run("\n")
                inst_run = para.add_run(med.instructions)
                inst_run.font.size = Pt(6)

            if med.container:
                para.add_run("\n")
                container_run = para.add_run(med.container)
                container_run.bold = True
                container_run.underline = True
                container_run.font.size = Pt(6)

            cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP

        if med is not None and med.dose:
            med_tbl.cell(base, 2).merge(med_tbl.cell(base + len(ROUNDS) - 1, 2))
            _cell_write(med_tbl.cell(base, 2), med.dose,
                        bold=True, size=6, align=CENTER)

        # Round labels
        for r_idx, rnd in enumerate(ROUNDS):
            _cell_write(med_tbl.cell(base + r_idx, 1), rnd,
                        bold=True, size=6, align=CENTER)

        # Extra blank row after rounds, then Received / Returned / Destroyed row
        rcvd = base + len(ROUNDS) + 1
        med_tbl.cell(rcvd, 0).merge(med_tbl.cell(rcvd, NCOLS - 1))
        rcvd_txt = (
            "Received:              Qty:                    "
            "Returned:              Qty:          By:                    "
            "Destroyed:              Qty:          By:"
        )
        _cell_write(med_tbl.cell(rcvd, 0), rcvd_txt, bold=True, size=6)

    doc.add_page_break()

    # ================================================================
    # Back page – Carers Medication Notes
    # ================================================================
    title_para = doc.add_paragraph()
    title_para.alignment = CENTER
    tr = title_para.add_run("CARERS MEDICATION NOTES")
    tr.bold = True
    tr.font.size = Pt(14)

    doc.add_paragraph()

    col_names = [
        "DATE", "TIME", "INITIALS", "MEDICATION",
        "DOSE", "REASON", "RESULT", "TIME", "INITIALS",
    ]
    ratios = [0.07, 0.06, 0.08, 0.18, 0.08, 0.22, 0.15, 0.06, 0.10]
    s = sum(ratios)
    notes_cws = [Cm(usable_cm * r / s) for r in ratios]

    notes_tbl = doc.add_table(rows=31, cols=len(col_names))
    notes_tbl.style = "Table Grid"
    notes_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT

    for c_i, cw in enumerate(notes_cws):
        for r_i in range(31):
            notes_tbl.rows[r_i].cells[c_i].width = cw

    for c_i, col_name in enumerate(col_names):
        _cell_write(notes_tbl.rows[0].cells[c_i], col_name,
                    bold=True, size=7, align=CENTER)
        _set_bg(notes_tbl.rows[0].cells[c_i], HEADER_BG)

    # AYP branding bottom-right
    doc.add_paragraph()
    ayp_para = doc.add_paragraph()
    ayp_para.alignment = RIGHT
    ar = ayp_para.add_run(f"AYP  {data.org_name}")
    ar.bold = True
    ar.font.size = Pt(12)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
