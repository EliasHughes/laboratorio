"""Pixel-perfect PDF renderer for Yazoo lab forms.

Diseño fiel al PDF adjunto por el usuario (cambio-082026):
  * Cabecera tri-columna estilo formulario impreso:
      [ LOGO ] | [ Company + Título del formulario ] | [ Doc-control (Código/Rev/Página) ]
  * Sub-tira ámbar debajo del header
  * Meta compacta con banda gris a la izquierda de cada label
  * Secciones con banner oscuro y ancho completo
  * Tablas ajustadas a la orientación (portrait 180mm / landscape 267mm)
  * Firmas al pie con imagen embebida y líneas sobre el nombre
  * Footer "Y-FO-CS-001 REV.01 · Aprobado ..." estilo formato controlado

Uso desde `lab_forms._record_to_pdf`:
    from pdf_form_renderer import render_lab_form_pdf
    return render_lab_form_pdf(record, schema, signatures_lookup)
"""
import io
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether,
)

BRAND_AMBER = colors.HexColor("#DCA54C")
BRAND_DARK = colors.HexColor("#1A120E")
BRAND_BROWN = colors.HexColor("#6B4423")
GRAY_LIGHT = colors.HexColor("#F5F2ED")
GRAY_BORDER = colors.HexColor("#D8CFC1")
STATUS_ERROR = colors.HexColor("#8B1E1E")

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "yazoo-logo.png")

# Forms that require landscape orientation because their tables are wide
# (many columns per row). Anything else defaults to portrait A4.
LANDSCAPE_FORMS = {
    "water_analysis",         # 8 columnas de muestras por parámetro
    "aging_process",          # 5 envejecimientos + parámetros
    "packaging_control",      # 11 columnas de inspección por hora
    "aged_distilled_control", # 4 mezclados × parámetros × especif × incert
    "bulk_reception",         # 7 columnas × 19 filas horizontal · PDF pág 18
    "isotank_inspection",     # tabla ancha + diagramas de 7 puntos
}


def _fmt(v: Any) -> str:
    if v is None or v == "":
        return "—"
    if isinstance(v, bool):
        return "Sí" if v else "No"
    if isinstance(v, list):
        return ", ".join(str(x) for x in v) if v else "—"
    if isinstance(v, dict):
        return " · ".join(f"{k}: {vv}" for k, vv in v.items())
    return str(v)


# Mapping of textual results → glyph icons (per PDF cambios05082026 pág 20)
# ✓ verde para Conforme · ✗ rojo para No Conforme · ⊘ ámbar para No Aplica
ICON_MAP = {
    "conforme":     ("✓", colors.HexColor("#1E5732"), colors.HexColor("#E6F5EA")),
    "no conforme":  ("✗", colors.HexColor("#8B1E1E"), colors.HexColor("#FCE8E8")),
    "no aplica":    ("⊘", colors.HexColor("#7A5B00"), colors.HexColor("#FFF3D6")),
    "n/a":          ("⊘", colors.HexColor("#7A5B00"), colors.HexColor("#FFF3D6")),
    "bueno":        ("✓", colors.HexColor("#1E5732"), colors.HexColor("#E6F5EA")),
    "regular":      ("◐", colors.HexColor("#7A5B00"), colors.HexColor("#FFF3D6")),
    "deficiente":   ("✗", colors.HexColor("#8B1E1E"), colors.HexColor("#FCE8E8")),
}


def _icon_for(value):
    """Return (glyph, textColor, bgColor) if value maps to a known status."""
    if not isinstance(value, str):
        return None
    return ICON_MAP.get(value.strip().lower())


def _parse_spec(s):
    import re
    if s is None or isinstance(s, (int, float)):
        return None
    txt = str(s).strip()
    if not txt or txt == "—":
        return None
    m = re.match(r"^\s*([-+]?\d+(?:[.,]\d+)?)\s*(?:-|—|–|a|to)\s*([-+]?\d+(?:[.,]\d+)?)", txt, re.I)
    if m:
        try:
            return {"min": float(m.group(1).replace(",", ".")),
                    "max": float(m.group(2).replace(",", "."))}
        except ValueError:
            return None
    m = re.search(r"(?:≥|>=|>|min\.?|mínimo)\s*([-+]?\d+(?:[.,]\d+)?)", txt, re.I)
    if m:
        try: return {"min": float(m.group(1).replace(",", "."))}
        except ValueError: pass
    m = re.search(r"(?:≤|<=|<|max\.?|máx(?:imo)?\.?)\s*([-+]?\d+(?:[.,]\d+)?)", txt, re.I)
    if m:
        try: return {"max": float(m.group(1).replace(",", "."))}
        except ValueError: pass
    return None


def _oos(value, spec) -> bool:
    if value is None or value == "" or not spec:
        return False
    try:
        v = float(value) if isinstance(value, (int, float)) else float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return False
    if spec.get("min") is not None and v < spec["min"]:
        return True
    if spec.get("max") is not None and v > spec["max"]:
        return True
    return False


def render_lab_form_pdf(record: dict, schema: Optional[dict],
                        signature_file_path=None) -> bytes:
    """Render `record` (with data + signatures) to PDF using the schema layout.

    schema: as defined in form_schemas.FORM_SCHEMAS (dict with title, code, sections).
    signature_file_path: callable(user_id) -> Path|None to embed sig image.
    """
    form_type = record.get("form_type", "")
    is_landscape = form_type in LANDSCAPE_FORMS
    pagesize = landscape(A4) if is_landscape else A4
    page_w_mm = 267 if is_landscape else 180  # usable width after margins

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=pagesize,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=10 * mm, bottomMargin=12 * mm,
        title=f"{schema.get('code', 'Y-FO')} · {record.get('code', '')}" if schema else record.get("code", "Y-FO"),
    )

    styles = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=styles["Normal"], fontName="Helvetica",
                           fontSize=8.5, textColor=BRAND_DARK, leading=10)
    small = ParagraphStyle("s", parent=body, fontSize=7, leading=8)
    sec_title = ParagraphStyle("st", parent=body, fontName="Helvetica-Bold",
                                fontSize=9.5, textColor=colors.white)
    caption = ParagraphStyle("cap", parent=small, textColor=colors.HexColor("#7A6E5F"))

    story = []

    # ================= HEADER: [Logo] | [Company + form title] | [Doc control] =================
    if os.path.exists(LOGO_PATH):
        logo = Image(LOGO_PATH, width=20 * mm, height=20 * mm)
    else:
        logo = Paragraph("<b>YAZOO</b>",
                         ParagraphStyle("lg", parent=body, fontSize=11, alignment=TA_CENTER))

    company_col = [
        Paragraph("<b>RONES Y BEBIDAS DEL CARIBE YAZOO, S.R.L.</b>",
                  ParagraphStyle("co", parent=body, fontName="Helvetica-Bold",
                                  fontSize=10, alignment=TA_CENTER)),
        Paragraph(f"<b>{(schema.get('title') if schema else record.get('form_title','')).upper()}</b>",
                  ParagraphStyle("co2", parent=body, fontName="Helvetica-Bold",
                                  fontSize=10, alignment=TA_CENTER, textColor=BRAND_DARK)),
        Paragraph(schema.get("subtitle", "") if schema else "",
                  ParagraphStyle("co3", parent=body, fontSize=7.5,
                                  alignment=TA_CENTER, textColor=colors.HexColor("#5C5046"))),
    ]

    code = (schema or {}).get("code", "Y-FO")
    rev = _extract_rev(schema or {})
    doc_control = [
        ["Código:", code],
        ["Revisión:", rev],
        ["Página:", "1 de 1"],
    ]
    ctrl_tbl = Table(doc_control, colWidths=[15 * mm, 26 * mm])
    ctrl_tbl.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 7),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 7),
        ("GRID", (0, 0), (-1, -1), 0.4, BRAND_DARK),
        ("BACKGROUND", (0, 0), (0, -1), GRAY_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    header = Table(
        [[logo, company_col, ctrl_tbl]],
        colWidths=[24 * mm, (page_w_mm - 24 - 42) * mm, 42 * mm],
    )
    header.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, BRAND_DARK),
        ("LINEBEFORE", (1, 0), (1, 0), 0.4, BRAND_DARK),
        ("LINEBEFORE", (2, 0), (2, 0), 0.4, BRAND_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(header)
    # ámbar strip
    story.append(Table([[""]], colWidths=[page_w_mm * mm], rowHeights=[2],
                        style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), BRAND_AMBER)])))
    story.append(Spacer(1, 4))

    # Compact meta strip: Registrado por · Fecha · Estado
    created_at = (record.get("created_at") or "")[:19].replace("T", " ")
    approved_at = (record.get("approved_at") or "")[:10]
    meta_rows = [
        [Paragraph("<b>Código:</b>", small), record.get("code", "—"),
         Paragraph("<b>Registrado por:</b>", small), record.get("created_by_name") or "—",
         Paragraph("<b>Fecha:</b>", small), created_at or "—",
         Paragraph("<b>Estado:</b>", small),
         (record.get("status") or "draft").upper()],
    ]
    if approved_at:
        meta_rows.append([
            Paragraph("<b>Aprobado por:</b>", small), record.get("approved_by_name") or "—",
            Paragraph("<b>Fecha aprobación:</b>", small), approved_at,
            "", "", "", "",
        ])
    n_cells = 8
    col_w = [(page_w_mm / n_cells) * mm] * n_cells
    mt = Table(meta_rows, colWidths=col_w)
    mt.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 7.5),
        ("BACKGROUND", (0, 0), (0, -1), GRAY_LIGHT),
        ("BACKGROUND", (2, 0), (2, -1), GRAY_LIGHT),
        ("BACKGROUND", (4, 0), (4, -1), GRAY_LIGHT),
        ("BACKGROUND", (6, 0), (6, -1), GRAY_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.3, GRAY_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(mt)
    story.append(Spacer(1, 6))

    # ================= SECTIONS =================
    data = record.get("data", {}) or {}
    used_keys = set()

    if schema:
        for sec in schema.get("sections", []):
            _render_section(story, sec, data, used_keys, page_w_mm, sec_title, body, small)

    # ================= Observaciones =================
    if record.get("observations"):
        story.append(Spacer(1, 4))
        obs_hdr = _section_banner("Observaciones generales", page_w_mm, sec_title)
        story.append(obs_hdr)
        story.append(Table([[Paragraph(str(record.get("observations")), body)]],
                            colWidths=[page_w_mm * mm],
                            style=TableStyle([
                                ("GRID", (0, 0), (-1, -1), 0.3, GRAY_BORDER),
                                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                                ("TOPPADDING", (0, 0), (-1, -1), 4),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ])))
        story.append(Spacer(1, 4))

    # ================= FIRMAS =================
    signatures = record.get("signatures") or {}
    if signatures:
        story.append(Spacer(1, 6))
        story.append(_section_banner("Firmas", page_w_mm, sec_title))
        story.append(Spacer(1, 2))
        sig_cells: List[list] = []
        row_top, row_bot = [], []
        for slot, sig in signatures.items():
            img_cell = None
            uid = sig.get("user_id") if isinstance(sig, dict) else None
            if uid and signature_file_path:
                p = signature_file_path(uid)
                if p and os.path.exists(str(p)):
                    try:
                        img_cell = Image(str(p), width=45 * mm, height=15 * mm, kind='proportional')
                    except Exception:
                        img_cell = None
            row_top.append(img_cell or Paragraph("&nbsp;", body))
            name = (sig or {}).get("name") or "—"
            role = (sig or {}).get("role_label") or (sig or {}).get("role") or ""
            when = ((sig or {}).get("signed_at") or "")[:19].replace("T", " ")
            row_bot.append(Paragraph(
                f"<b>{name}</b><br/><font size=7>{slot.replace('_', ' ').title()} · {role}</font>"
                f"<br/><font size=6 color='#7A6E5F'>Firmado: {when}</font>", small))
        # Chunk into rows of 3
        chunk = 3
        for i in range(0, len(row_top), chunk):
            top = row_top[i:i + chunk]
            bot = row_bot[i:i + chunk]
            while len(top) < chunk: top.append(""); bot.append("")
            n = len(top)
            cw = [(page_w_mm / n) * mm] * n
            tbl = Table([top, bot], colWidths=cw)
            tbl.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, 0), "BOTTOM"),
                ("VALIGN", (0, 1), (-1, 1), "TOP"),
                ("LINEABOVE", (0, 1), (-1, 1), 0.4, BRAND_DARK),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (0, 1), (-1, 1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 4))

    # ================= FOOTER controlado =================
    story.append(Spacer(1, 4))
    footer = Table(
        [[Paragraph("<b>Y-FO-CS-001</b> REV.01", caption),
          Paragraph(f"Documento controlado · {record.get('code', '')}",
                     ParagraphStyle("f2", parent=caption, alignment=TA_CENTER)),
          Paragraph(f"Impreso {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                     ParagraphStyle("f3", parent=caption, alignment=TA_RIGHT))]],
        colWidths=[(page_w_mm / 3) * mm] * 3,
    )
    footer.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.4, BRAND_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(footer)

    doc.build(story)
    buf.seek(0)
    return buf.read()


def _extract_rev(schema: dict) -> str:
    """Try to derive a revision label from the subtitle (e.g. 'Rev. 04')."""
    import re
    sub = schema.get("subtitle") or ""
    m = re.search(r"Rev\.?\s*(\d+[a-zA-Z]?)", sub, re.I)
    if m:
        return m.group(1).zfill(2)
    return "01"


def _section_banner(title: str, page_w_mm: int, sec_style: ParagraphStyle) -> Table:
    hdr = Table([[Paragraph(title, sec_style)]], colWidths=[page_w_mm * mm])
    hdr.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return hdr


def _render_section(story, sec, data, used_keys, page_w_mm, sec_style, body, small):
    story.append(_section_banner(sec["title"], page_w_mm, sec_style))
    story.append(Spacer(1, 2))

    if sec.get("type") == "table":
        _render_table_section(story, sec, data, used_keys, page_w_mm, small)
    else:
        _render_fields_section(story, sec, data, used_keys, page_w_mm, body)
    story.append(Spacer(1, 5))


def _render_fields_section(story, sec, data, used_keys, page_w_mm, body):
    fields = sec.get("fields", [])
    if not fields:
        return
    # 4 columnas para landscape, 2 para portrait
    per_row = 4 if page_w_mm > 200 else 2
    rows: List[List] = []
    row: List = []
    for f in fields:
        val = data.get(f["name"])
        used_keys.add(f["name"])
        row += [Paragraph(f"<b>{f['label']}</b>", body), Paragraph(_fmt(val), body)]
        if len(row) >= per_row * 2:
            rows.append(row); row = []
    if row:
        while len(row) < per_row * 2: row.append("")
        rows.append(row)
    # Column widths: alternating label/value
    unit_w = page_w_mm / per_row
    label_w = unit_w * 0.42
    val_w = unit_w * 0.58
    col_widths = []
    for _ in range(per_row):
        col_widths += [label_w * mm, val_w * mm]
    tbl = Table(rows, colWidths=col_widths)
    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, GRAY_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    # Gray background on label columns (even indices)
    for i in range(per_row):
        style.append(("BACKGROUND", (i * 2, 0), (i * 2, -1), GRAY_LIGHT))
    tbl.setStyle(TableStyle(style))
    story.append(tbl)


def _render_table_section(story, sec, data, used_keys, page_w_mm, small):
    cols = sec.get("columns", [])
    rows_in_data = data.get(sec.get("name", "rows"))
    if not isinstance(rows_in_data, list):
        rows_in_data = sec.get("default_rows", [])
    used_keys.add(sec.get("name"))

    # header row
    header = [c["label"] for c in cols]
    tbl_rows: List[List] = [header]
    oos_cells: List = []

    # spec / result column indices for out-of-spec highlighting
    spec_col_idx = None
    result_col_idxs: List[int] = []
    for ci, c in enumerate(cols):
        key_l = (c.get("key") or "").lower()
        if "especifica" in key_l or "specification" in key_l or "limite" in key_l:
            spec_col_idx = ci
    for ci, c in enumerate(cols):
        key_l = (c.get("key") or "").lower()
        if ci == spec_col_idx: continue
        if any(t in key_l for t in ["resultado", "result", "env1", "env2", "env3", "env4", "env5",
                                     "col_1", "col_2", "col_3", "col_4", "col_5", "col_6", "col_7", "col_8"]):
            result_col_idxs.append(ci)

    for r_idx, row in enumerate(rows_in_data, start=1):
        if not isinstance(row, dict): continue
        line = []
        for c in cols:
            v = row.get(c["key"])
            icon = _icon_for(v)
            if icon:
                line.append(icon[0])  # will be styled below
            else:
                line.append(_fmt(v))
        tbl_rows.append(line)
        # apply icon styling once we know the cell coords
        for ci, c in enumerate(cols):
            icon = _icon_for(row.get(c["key"]))
            if icon:
                oos_cells.append((ci, r_idx, "icon", icon))
        if spec_col_idx is not None and result_col_idxs:
            spec = _parse_spec(row.get(cols[spec_col_idx]["key"]))
            if spec:
                for ci in result_col_idxs:
                    if _oos(row.get(cols[ci]["key"]), spec):
                        oos_cells.append((ci, r_idx, "oos", None))

    # Column widths: parameter/first col wider, rest evenly
    n = max(len(cols), 1)
    if n == 1:
        col_widths = [page_w_mm * mm]
    else:
        first = min(50, page_w_mm * 0.28)
        rest = (page_w_mm - first) / (n - 1)
        col_widths = [first * mm] + [rest * mm] * (n - 1)

    tbl = Table(tbl_rows, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.5),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 7.5),
        ("GRID", (0, 0), (-1, -1), 0.3, BRAND_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_LIGHT]),
    ]
    for entry in oos_cells:
        c, r_idx, kind, icon = entry if len(entry) == 4 else (*entry, "oos", None)
        if kind == "icon":
            glyph, text_color, bg_color = icon
            style.append(("BACKGROUND", (c, r_idx), (c, r_idx), bg_color))
            style.append(("TEXTCOLOR",  (c, r_idx), (c, r_idx), text_color))
            style.append(("FONT",       (c, r_idx), (c, r_idx), "Helvetica-Bold", 11))
            style.append(("ALIGN",      (c, r_idx), (c, r_idx), "CENTER"))
        else:
            style.append(("BACKGROUND", (c, r_idx), (c, r_idx), colors.HexColor("#FCE8E8")))
            style.append(("TEXTCOLOR",  (c, r_idx), (c, r_idx), STATUS_ERROR))
            style.append(("FONT",       (c, r_idx), (c, r_idx), "Helvetica-Bold", 7.5))
    tbl.setStyle(TableStyle(style))
    story.append(tbl)
    if sec.get("hint"):
        story.append(Spacer(1, 1))
        story.append(Paragraph(f"<i>{sec['hint']}</i>",
                                ParagraphStyle("hint", parent=small, textColor=colors.HexColor("#7A6E5F"))))
