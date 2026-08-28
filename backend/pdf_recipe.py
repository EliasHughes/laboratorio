"""PDF renderer for Production Recipes (BOM).

Generates a printable, pixel-clean recipe document listing components,
quantities, unit cost, subtotals, total cost, unit cost and the process
instructions. Matches the visual language used by the rest of the
Yazoo lab forms (header + amber divider + dark headers).
"""
import io
import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
)

BRAND_DARK = colors.HexColor("#1A120E")
BRAND_AMBER = colors.HexColor("#B08D57")
GRAY_LIGHT = colors.HexColor("#F5F2ED")
GRAY_BORDER = colors.HexColor("#D8CFC1")
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "yazoo-logo.png")


def _fmt_money(n):
    try:
        return f"RD$ {float(n):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_num(n, digits=3):
    try:
        return f"{float(n):,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def recipe_to_pdf(recipe: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=13 * mm, bottomMargin=13 * mm,
        title=f"Receta {recipe.get('code','')}",
    )
    styles = getSampleStyleSheet()
    title_st = ParagraphStyle("t", parent=styles["Heading1"], fontName="Helvetica-Bold",
                              fontSize=13, textColor=BRAND_DARK, spaceAfter=2)
    sub_st = ParagraphStyle("s", parent=styles["Normal"], fontName="Helvetica",
                            fontSize=8.5, textColor=colors.HexColor("#5C5046"))
    body = ParagraphStyle("b", parent=styles["Normal"], fontName="Helvetica",
                          fontSize=9, textColor=BRAND_DARK)
    sec = ParagraphStyle("sec", parent=styles["Normal"], fontName="Helvetica-Bold",
                         fontSize=9.5, textColor=colors.white)

    story = []
    # --- Header
    header_left = [
        Paragraph("<b>RONES Y BEBIDAS DEL CARIBE YAZOO</b>", title_st),
        Paragraph("Producción · Recetas y Fórmulas (BOM)", sub_st),
        Paragraph(f"<b>{recipe.get('name','')}</b> · v{recipe.get('version','1.0')}", sub_st),
        Paragraph(f"Código: <b>{recipe.get('code','')}</b> · Estado: "
                  f"<b>{(recipe.get('status') or 'active').upper()}</b>", sub_st),
    ]
    if os.path.exists(LOGO_PATH):
        logo_img = Image(LOGO_PATH, width=22 * mm, height=22 * mm)
        header_tbl = Table([[header_left, logo_img]], colWidths=[155 * mm, 25 * mm])
        header_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(header_tbl)
    else:
        for it in header_left:
            story.append(it)
    story.append(Spacer(1, 4))
    bar = Table([[""]], colWidths=[180 * mm], rowHeights=[2])
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BRAND_AMBER)]))
    story.append(bar)
    story.append(Spacer(1, 6))

    # --- Metadata
    created_at = (recipe.get("created_at") or "")[:19].replace("T", " ")
    meta = [
        ["Creado por", recipe.get("created_by_name", "—"),
         "Fecha creación", created_at or "—"],
        ["Rendimiento", f"{recipe.get('yield_qty', 1)} {recipe.get('yield_unit', 'u')}",
         "Costo unitario", _fmt_money(recipe.get("unit_cost", 0))],
    ]
    if recipe.get("updated_at"):
        meta.append(["Última edición", (recipe["updated_at"] or "")[:19].replace("T", " "),
                     "Componentes", str(len(recipe.get("components") or []))])
    mt = Table(meta, colWidths=[35 * mm, 55 * mm, 30 * mm, 60 * mm])
    mt.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8),
        ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 8),
        ("BACKGROUND", (0, 0), (0, -1), GRAY_LIGHT),
        ("BACKGROUND", (2, 0), (2, -1), GRAY_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.3, GRAY_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(mt); story.append(Spacer(1, 8))

    # --- Components (BOM) table
    hdr = Table([[Paragraph("Componentes (BOM)", sec)]], colWidths=[180 * mm])
    hdr.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(hdr); story.append(Spacer(1, 2))

    rows = [["#", "Descripción", "Cantidad", "Unidad", "Costo/u (RD$)", "Subtotal (RD$)"]]
    total = 0.0
    for i, c in enumerate(recipe.get("components") or [], start=1):
        qty = float(c.get("quantity") or 0)
        cost = float(c.get("cost_per_unit") or 0)
        subtotal = qty * cost
        total += subtotal
        rows.append([
            str(i), c.get("description", ""),
            _fmt_num(qty), c.get("unit", ""),
            _fmt_money(cost) if cost else "—",
            _fmt_money(subtotal) if subtotal else "—",
        ])
    rows.append(["", "", "", "", "TOTAL", _fmt_money(total)])
    bom = Table(rows, colWidths=[10 * mm, 82 * mm, 22 * mm, 18 * mm, 24 * mm, 24 * mm])
    bom.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
        ("GRID", (0, 0), (-1, -1), 0.3, BRAND_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("BACKGROUND", (0, -1), (-1, -1), GRAY_LIGHT),
        ("FONT", (4, -1), (-1, -1), "Helvetica-Bold", 8.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(bom); story.append(Spacer(1, 8))

    # --- Process instructions
    hdr2 = Table([[Paragraph("Proceso · Instrucciones", sec)]], colWidths=[180 * mm])
    hdr2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(hdr2); story.append(Spacer(1, 2))
    instructions = (recipe.get("instructions") or "—").replace("\n", "<br/>")
    inst_tbl = Table([[Paragraph(instructions, body)]], colWidths=[180 * mm])
    inst_tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, GRAY_BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(inst_tbl); story.append(Spacer(1, 10))

    # --- Signature line
    sig_tbl = Table([
        ["", ""],
        [Paragraph("<b>Elaborado por</b>", body), Paragraph("<b>Autorizado por</b>", body)],
        [Paragraph(recipe.get("created_by_name", "—"), body), Paragraph("—", body)],
    ], colWidths=[90 * mm, 90 * mm])
    sig_tbl.setStyle(TableStyle([
        ("LINEABOVE", (0, 1), (-1, 1), 0.5, BRAND_DARK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(sig_tbl)

    # --- Footer
    footer = Table([[Paragraph(
        f"Documento controlado · YLMS · Impreso {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ParagraphStyle("ft", parent=body, fontSize=6.5, alignment=TA_CENTER,
                       textColor=colors.HexColor("#7A6E5F")))]],
        colWidths=[180 * mm])
    story.append(Spacer(1, 6))
    story.append(footer)

    doc.build(story); buf.seek(0)
    return buf.read()
