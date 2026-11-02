"""PDF generation for daily schedules using ReportLab."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO


# Color mapping for categories
CATEGORY_COLORS = {
    "sleep":    colors.HexColor("#312E81"),
    "work":     colors.HexColor("#1E40AF"),
    "meal":     colors.HexColor("#B45309"),
    "exercise": colors.HexColor("#047857"),
    "study":    colors.HexColor("#7C3AED"),
    "personal": colors.HexColor("#0E7490"),
    "free":     colors.HexColor("#4F46E5"),
    "routine":  colors.HexColor("#6B7280"),
}

CATEGORY_BG = {
    "sleep":    colors.HexColor("#E0E7FF"),
    "work":     colors.HexColor("#DBEAFE"),
    "meal":     colors.HexColor("#FEF3C7"),
    "exercise": colors.HexColor("#D1FAE5"),
    "study":    colors.HexColor("#EDE9FE"),
    "personal": colors.HexColor("#CFFAFE"),
    "free":     colors.HexColor("#E0E7FF"),
    "routine":  colors.HexColor("#F3F4F6"),
}

CATEGORY_LABELS = {
    "sleep": "Dormir",
    "work": "Trabajo",
    "meal": "Comida",
    "exercise": "Ejercicio",
    "study": "Estudio",
    "personal": "Personal",
    "free": "Tiempo libre",
    "routine": "Rutina",
}


def _duration_str(start: str, end: str) -> str:
    """Calculate human-readable duration."""
    sh, sm = map(int, start.split(":"))
    eh, em = map(int, end.split(":"))
    total_start = sh * 60 + sm
    total_end = eh * 60 + em
    if total_end <= total_start:
        total_end += 1440
    diff = total_end - total_start
    hours = diff // 60
    mins = diff % 60
    if hours and mins:
        return f"{hours}h {mins}m"
    elif hours:
        return f"{hours}h"
    return f"{mins}m"


def generate_pdf(blocks: list[dict], schedule_date: str) -> bytes:
    """Generate a professionally formatted PDF of the daily schedule."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=22,
        spaceAfter=4 * mm,
        textColor=colors.HexColor("#1E293B"),
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#64748B"),
        alignment=TA_CENTER,
        spaceAfter=8 * mm,
    )
    cell_title = ParagraphStyle(
        "CellTitle",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1E293B"),
    )
    cell_desc = ParagraphStyle(
        "CellDesc",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#64748B"),
    )
    cell_time = ParagraphStyle(
        "CellTime",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#334155"),
    )
    cell_cat = ParagraphStyle(
        "CellCat",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#64748B"),
    )

    elements = []

    # Title
    elements.append(Paragraph("📋 Mi Planificación Diaria", title_style))
    elements.append(Paragraph(f"Fecha: {schedule_date}", subtitle_style))

    # Build table data
    header = ["Hora", "Actividad", "Categoría", "Duración"]
    table_data = [header]

    for block in sorted(blocks, key=lambda b: b["start_time"]):
        time_range = f"{block['start_time']} - {block['end_time']}"
        title = block["title"].replace("🌙", "").replace("🌅", "").replace(
            "🍳", "").replace("💪", "").replace("☕", "").replace(
            "💼", "").replace("🍽️", "").replace("📚", "").replace(
            "🎮", "").replace("🍲", "").strip()

        desc = block.get("description", "")
        title_text = Paragraph(title, cell_title)
        if desc:
            title_with_desc = Paragraph(
                f"<b>{title}</b><br/><font size='7' color='#94A3B8'>{desc}</font>",
                cell_title,
            )
        else:
            title_with_desc = title_text

        cat_label = CATEGORY_LABELS.get(block["category"], block["category"])
        duration = _duration_str(block["start_time"], block["end_time"])

        table_data.append([
            Paragraph(time_range, cell_time),
            title_with_desc,
            Paragraph(cat_label, cell_cat),
            Paragraph(duration, cell_cat),
        ])

    # Create table
    col_widths = [3.2 * cm, 8 * cm, 2.8 * cm, 2 * cm]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Table styling
    style_commands = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),

        # Body
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),

        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#1E293B")),

        # Rounded corners effect
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]

    # Alternate row colors by category
    for i, block in enumerate(sorted(blocks, key=lambda b: b["start_time"]), start=1):
        bg = CATEGORY_BG.get(block["category"], colors.white)
        style_commands.append(("BACKGROUND", (0, i), (-1, i), bg))

    table.setStyle(TableStyle(style_commands))
    elements.append(table)

    # Footer
    elements.append(Spacer(1, 10 * mm))
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#94A3B8"),
        alignment=TA_CENTER,
    )
    elements.append(Paragraph(
        "Generado por Smart Day Planner • Planificación inteligente de tu día",
        footer_style,
    ))

    # Build PDF
    doc.build(elements)
    return buffer.getvalue()
