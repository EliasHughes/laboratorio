"""PDF renderer for EHS records (incidents, inspections, PPE deliveries).

Two modes:
  * with_evidence=True  → embed uploaded images (up to 20) as thumbnails
  * with_evidence=False → clean audit format without any photo attachments
"""
import io
import os
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
)

BRAND_AMBER = colors.HexColor("#DCA54C")
BRAND_DARK = colors.HexColor("#1A120E")
GRAY_LIGHT = colors.HexColor("#F5F2ED")
GRAY_BORDER = colors.HexColor("#D8CFC1")
SEV_COLORS = {
    "low":    (colors.HexColor("#E6F5EA"), colors.HexColor("#1E5732")),
    "medium": (colors.HexColor("#FFF3D6"), colors.HexColor("#7A5B00")),
    "high":   (colors.HexColor("#FCE8E8"), colors.HexColor("#8B1E1E")),
}
STATUS_LABELS = {"open": "ABIERTO", "investigating": "INVESTIGANDO", "closed": "CERRADO"}
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "yazoo-logo.png")


def _kv_row(k, v, body):
    return [Paragraph(f"<b>{k}</b>", body), Paragraph(v or "—", body)]


def render_ehs_incident_pdf(incident: dict, attachments: list,
                             with_evidence: bool = True) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
        title=f"EHS {incident.get('code', '')}",
    )
    body = ParagraphStyle("b", fontName="Helvetica", fontSize=9, textColor=BRAND_DARK, leading=11)
    small = ParagraphStyle("s", parent=body, fontSize=7.5)
    sec_st = ParagraphStyle("sec", fontName="Helvetica-Bold", fontSize=9.5, textColor=colors.white)
    caption = ParagraphStyle("cap", parent=small, textColor=colors.HexColor("#7A6E5F"),
                              alignment=TA_CENTER)

    story = []
    # --- Header
    if os.path.exists(LOGO_PATH):
        logo = Image(LOGO_PATH, width=20 * mm, height=20 * mm)
    else:
        logo = Paragraph("<b>YAZOO</b>", ParagraphStyle("lg", parent=body, fontSize=11, alignment=TA_CENTER))
    company_col = [
        Paragraph("<b>RONES Y BEBIDAS DEL CARIBE YAZOO, S.R.L.</b>",
                   ParagraphStyle("co", parent=body, fontName="Helvetica-Bold",
                                   fontSize=10, alignment=TA_CENTER)),
        Paragraph("<b>EHS · Registro de Incidentes / Casi-accidentes</b>",
                   ParagraphStyle("co2", parent=body, fontName="Helvetica-Bold",
                                   fontSize=10, alignment=TA_CENTER, textColor=BRAND_DARK)),
        Paragraph("ISO 45001 · OSHA 29 CFR 1904 · Rev. 01",
                   ParagraphStyle("co3", parent=body, fontSize=7.5,
                                   alignment=TA_CENTER, textColor=colors.HexColor("#5C5046"))),
    ]
    ctrl = Table([
        ["Código:",   incident.get("code", "—")],
        ["Revisión:", "01"],
        ["Modo:",     "CON EVIDENCIAS" if with_evidence else "SIN EVIDENCIAS"],
    ], colWidths=[18 * mm, 26 * mm])
    ctrl.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 7),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 7),
        ("GRID", (0, 0), (-1, -1), 0.4, BRAND_DARK),
        ("BACKGROUND", (0, 0), (0, -1), GRAY_LIGHT),
    ]))
    hdr = Table([[logo, company_col, ctrl]], colWidths=[24 * mm, 114 * mm, 44 * mm])
    hdr.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, BRAND_DARK),
        ("LINEBEFORE", (1, 0), (1, 0), 0.4, BRAND_DARK),
        ("LINEBEFORE", (2, 0), (2, 0), 0.4, BRAND_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(hdr)
    story.append(Table([[""]], colWidths=[182 * mm], rowHeights=[2],
                        style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), BRAND_AMBER)])))
    story.append(Spacer(1, 6))

    # --- Meta strip
    sev = (incident.get("severity") or "low").lower()
    sev_bg, sev_fg = SEV_COLORS.get(sev, SEV_COLORS["low"])
    status = STATUS_LABELS.get(incident.get("status", "open"), "ABIERTO")
    meta = Table([[
        Paragraph("<b>Fecha:</b>", small), incident.get("date", "—"),
        Paragraph("<b>Hora:</b>", small),  incident.get("time", "—"),
        Paragraph("<b>Área:</b>", small),  incident.get("area", "—"),
        Paragraph("<b>Tipo:</b>", small),  incident.get("incident_type", "—"),
    ]], colWidths=[16 * mm, 22 * mm, 14 * mm, 18 * mm, 14 * mm, 32 * mm, 14 * mm, 52 * mm])
    meta.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
        ("GRID", (0, 0), (-1, -1), 0.3, GRAY_BORDER),
        ("BACKGROUND", (0, 0), (0, -1), GRAY_LIGHT),
        ("BACKGROUND", (2, 0), (2, -1), GRAY_LIGHT),
        ("BACKGROUND", (4, 0), (4, -1), GRAY_LIGHT),
        ("BACKGROUND", (6, 0), (6, -1), GRAY_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(meta)
    # Severity + status pills
    pills = Table([[
        Paragraph(f"<b>Severidad:</b> {sev.upper()}",
                   ParagraphStyle("sp", parent=body, textColor=sev_fg,
                                   backColor=sev_bg, alignment=TA_CENTER)),
        Paragraph(f"<b>Estado:</b> {status}",
                   ParagraphStyle("st", parent=body, alignment=TA_CENTER,
                                   backColor=GRAY_LIGHT)),
    ]], colWidths=[91 * mm, 91 * mm])
    pills.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BRAND_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (0, -1), sev_bg),
        ("BACKGROUND", (1, 0), (1, -1), GRAY_LIGHT),
    ]))
    story.append(Spacer(1, 3)); story.append(pills); story.append(Spacer(1, 8))

    # --- Description / Root cause / Action
    def section(title, text):
        hdr = Table([[Paragraph(title, sec_st)]], colWidths=[182 * mm])
        hdr.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_DARK),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        content = Table([[Paragraph((text or "—").replace("\n", "<br/>"), body)]],
                         colWidths=[182 * mm])
        content.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.3, GRAY_BORDER),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return [hdr, Spacer(1, 2), content, Spacer(1, 5)]

    for it in section("Descripción del incidente", incident.get("description")):
        story.append(it)
    for it in section("Causa raíz", incident.get("root_cause")):
        story.append(it)
    for it in section("Acción correctiva", incident.get("corrective_action")):
        story.append(it)

    # --- Evidences
    if with_evidence and attachments:
        story.append(Spacer(1, 4))
        hdr = Table([[Paragraph(f"Evidencias fotográficas ({len(attachments)} adjunta{'s' if len(attachments) != 1 else ''})", sec_st)]],
                     colWidths=[182 * mm])
        hdr.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_DARK),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(hdr); story.append(Spacer(1, 3))
        # 3-column grid of thumbnails (max 60mm each)
        thumbs = []
        for a in attachments[:20]:
            ct = a.get("content_type") or ""
            path = a.get("stored_path")
            if ct.startswith("image/") and path and os.path.exists(path):
                try:
                    img = Image(path, width=55 * mm, height=40 * mm, kind="proportional")
                except Exception:
                    img = Paragraph("—", small)
            else:
                img = Paragraph(f"<b>{a.get('filename','—')}</b><br/><font size=6>{ct}</font>", small)
            caption_p = Paragraph(a.get("filename", "—"), small)
            thumbs.append([img, caption_p])
        # Split into rows of 3
        rows = []
        for i in range(0, len(thumbs), 3):
            chunk = thumbs[i:i + 3]
            while len(chunk) < 3: chunk.append([Paragraph("", small), Paragraph("", small)])
            rows.append([chunk[0][0], chunk[1][0], chunk[2][0]])
            rows.append([chunk[0][1], chunk[1][1], chunk[2][1]])
        if rows:
            tbl = Table(rows, colWidths=[60 * mm, 61 * mm, 61 * mm])
            tbl.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.3, GRAY_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ]))
            story.append(tbl)

    elif not with_evidence and attachments:
        # In "sin evidencias" mode we still list attachment metadata for traceability
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"<i>Este documento no incluye las {len(attachments)} evidencia(s) fotográfica(s) asociada(s). "
            f"Solicite la versión con evidencias para auditoría.</i>",
            ParagraphStyle("ne", parent=small, textColor=colors.HexColor("#7A6E5F"))))

    # --- Footer with signature block
    story.append(Spacer(1, 10))
    story.append(Table([[
        Paragraph("<b>Reportado por</b><br/>" + (incident.get("reported_by") or incident.get("created_by_name") or "—"), body),
        Paragraph("<b>Investigador</b><br/>—", body),
        Paragraph("<b>Cerrado por</b><br/>—", body),
    ]], colWidths=[60 * mm, 61 * mm, 61 * mm], style=TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, BRAND_DARK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ])))
    story.append(Spacer(1, 6))
    story.append(Table([[Paragraph(
        f"EHS-{incident.get('code','')} · Impreso {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
        f"Modo: {'CON EVIDENCIAS' if with_evidence else 'SIN EVIDENCIAS'}",
        caption)]], colWidths=[182 * mm], style=TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 0.3, BRAND_DARK),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
        ])))

    doc.build(story); buf.seek(0)
    return buf.read()
