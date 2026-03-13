from pathlib import Path
from datetime import date
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.pdfgen.canvas import Canvas

from models.firmenschreiben import Firmenschreiben
from models.supplier import Supplier
from models.customer import Customer
from utils.paths import get_fs_pdf_path


# Farben (identisch mit kv_pdf_generator)
COLOR_TEXT = HexColor("#111827")
COLOR_GRAY = HexColor("#6B7280")
COLOR_LINE = HexColor("#D1D5DB")
COLOR_HEADER_BG = HexColor("#F3F4F6")
COLOR_ACCENT = HexColor("#1E40AF")

PAGE_W, PAGE_H = A4
MARGIN_L = 20 * mm
MARGIN_R = 20 * mm
MARGIN_T = 15 * mm
MARGIN_B = 20 * mm
USABLE_W = PAGE_W - MARGIN_L - MARGIN_R


def _fmt_date(d) -> str:
    if isinstance(d, str):
        parts = d.split("-")
        if len(parts) == 3:
            return f"{parts[2]}.{parts[1]}.{parts[0]}"
        return d
    if isinstance(d, date):
        return d.strftime("%d.%m.%Y")
    return ""


def _fmt_postfach(postfach: str | None) -> str:
    if not postfach:
        return ""
    val = postfach.strip()
    if not val:
        return ""
    if val.lower().startswith("postfach"):
        return val
    return f"Postfach {val}"


def _get_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "FSNormal", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, leading=14,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "FSSmall", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, leading=11,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "FSGray", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, leading=11,
        textColor=COLOR_GRAY,
    ))
    styles.add(ParagraphStyle(
        "FSGraySmall", parent=styles["Normal"],
        fontName="Helvetica", fontSize=7, leading=9,
        textColor=COLOR_GRAY,
    ))
    styles.add(ParagraphStyle(
        "FSBold", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10, leading=13,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "FSTitle", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=14, leading=17,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "FSBetreff", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=12, leading=15,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "FSRight", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, leading=13,
        alignment=TA_RIGHT, textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "FSRightBold", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10, leading=13,
        alignment=TA_RIGHT, textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "FSGruss", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, leading=14,
        textColor=COLOR_TEXT,
    ))
    return styles


class FSCanvasHelper:
    """Zeichnet Footer auf jeder Seite."""

    def __init__(self, supplier: Optional[Supplier], page_count_holder: list):
        self.supplier = supplier
        self.page_count_holder = page_count_holder

    def on_page(self, canvas: Canvas, doc):
        self.page_count_holder[0] += 1
        if self.supplier:
            self._draw_footer(canvas, doc)

    def _draw_footer(self, canvas: Canvas, doc):
        s = self.supplier
        y = MARGIN_B - 5 * mm
        col_w = USABLE_W / 3

        canvas.setStrokeColor(COLOR_LINE)
        canvas.setLineWidth(0.75)
        canvas.line(MARGIN_L, y + 12, PAGE_W - MARGIN_R, y + 12)

        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(COLOR_GRAY)

        x1 = MARGIN_L
        canvas.drawString(x1, y, "Bankverbindung")
        canvas.setFont("Helvetica", 7)
        if s.bank:
            y -= 9
            canvas.drawString(x1, y, s.bank)
        if s.iban:
            y -= 9
            canvas.drawString(x1, y, f"IBAN: {s.iban}")
        if s.bic:
            y -= 9
            canvas.drawString(x1, y, f"BIC: {s.bic}")

        x2 = MARGIN_L + col_w
        y2 = MARGIN_B - 5 * mm
        canvas.setFont("Helvetica-Bold", 7)
        canvas.drawString(x2, y2, "Steuerdaten")
        canvas.setFont("Helvetica", 7)
        if s.steuernr:
            y2 -= 9
            canvas.drawString(x2, y2, f"St.-Nr.: {s.steuernr}")
        if s.ustid:
            y2 -= 9
            canvas.drawString(x2, y2, f"USt-IdNr.: {s.ustid}")

        x3 = MARGIN_L + 2 * col_w
        y3 = MARGIN_B - 5 * mm
        canvas.setFont("Helvetica-Bold", 7)
        canvas.drawString(x3, y3, "Kontakt")
        canvas.setFont("Helvetica", 7)
        if s.telefon:
            y3 -= 9
            canvas.drawString(x3, y3, f"Tel: {s.telefon}")
        if s.telefax:
            y3 -= 9
            canvas.drawString(x3, y3, f"Fax: {s.telefax}")
        if s.email:
            y3 -= 9
            canvas.drawString(x3, y3, s.email)
        if s.web:
            y3 -= 9
            canvas.drawString(x3, y3, s.web)


def generate_fs_pdf(
    fs: Firmenschreiben,
    supplier: Optional[Supplier],
    customer: Optional[Customer],
) -> Path:
    pdf_path = get_fs_pdf_path(fs.fsnr, fs.datum)
    styles = _get_styles()

    page_count = [0]
    canvas_helper = FSCanvasHelper(supplier, page_count)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T,
        bottomMargin=MARGIN_B + (15 * mm if supplier else 5 * mm),
    )

    elements = []

    # === ZONE 1: Kopfbereich (Logo + Firmendaten) ===
    if supplier:
        logo_cell = ""
        if supplier.logo_path and Path(supplier.logo_path).exists():
            try:
                logo_cell = Image(supplier.logo_path, width=50 * mm, height=25 * mm)
                logo_cell.hAlign = "LEFT"
            except Exception:
                logo_cell = ""

        firm_lines = []
        firm_lines.append(Paragraph(supplier.firma, styles["FSTitle"]))
        if supplier.inhaber:
            firm_lines.append(Paragraph(supplier.inhaber, styles["FSGray"]))
        if supplier.strasse:
            firm_lines.append(Paragraph(supplier.strasse, styles["FSGray"]))
        postfach_text = _fmt_postfach(supplier.postfach)
        if postfach_text:
            firm_lines.append(Paragraph(postfach_text, styles["FSGray"]))
        plz_ort = f"{supplier.plz or ''} {supplier.ort or ''}".strip()
        if plz_ort:
            firm_lines.append(Paragraph(plz_ort, styles["FSGray"]))
        if supplier.telefon:
            firm_lines.append(Paragraph(f"Tel: {supplier.telefon}", styles["FSGraySmall"]))
        if supplier.email:
            firm_lines.append(Paragraph(supplier.email, styles["FSGraySmall"]))

        header_table = Table(
            [[logo_cell, firm_lines]],
            colWidths=[55 * mm, USABLE_W - 55 * mm],
        )
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 3 * mm))

        line_table = Table([[""]], colWidths=[USABLE_W])
        line_table.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, COLOR_LINE),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 2 * mm))

        # === ZONE 2: Absenderzeile ===
        absender_parts = [supplier.firma]
        if supplier.strasse:
            absender_parts.append(supplier.strasse)
        if postfach_text:
            absender_parts.append(postfach_text)
        if plz_ort:
            absender_parts.append(plz_ort)
        absender_text = " · ".join(absender_parts)
        elements.append(Paragraph(absender_text, styles["FSGraySmall"]))
        elements.append(Spacer(1, 3 * mm))
    else:
        plz_ort = ""
        postfach_text = ""

    # === ZONE 3: Empfängeradresse + Brief-Info ===
    emp_lines = []
    if customer:
        if customer.firma:
            emp_lines.append(Paragraph(customer.firma, styles["FSNormal"]))
        name_parts = []
        if customer.anrede:
            name_parts.append(customer.anrede)
        if customer.titel:
            name_parts.append(customer.titel)
        if customer.vorname:
            name_parts.append(customer.vorname)
        if customer.nachname:
            name_parts.append(customer.nachname)
        if name_parts:
            emp_lines.append(Paragraph(" ".join(name_parts), styles["FSNormal"]))
        if customer.strasse:
            emp_lines.append(Paragraph(customer.strasse, styles["FSNormal"]))
        cust_plz_ort = f"{customer.plz or ''} {customer.ort or ''}".strip()
        if cust_plz_ort:
            emp_lines.append(Paragraph(cust_plz_ort, styles["FSNormal"]))

    datum_str = _fmt_date(fs.datum)
    info_data = [
        [Paragraph("Firmenschreiben", styles["FSGray"]),
         Paragraph(fs.fsnr, styles["FSRightBold"])],
        [Paragraph("Datum", styles["FSGray"]),
         Paragraph(datum_str, styles["FSRight"])],
    ]
    if customer and customer.id:
        info_data.append([
            Paragraph("Kunden-Nr.", styles["FSGray"]),
            Paragraph(f"K-{customer.id}", styles["FSRight"]),
        ])

    info_table = Table(info_data, colWidths=[30 * mm, 40 * mm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    addr_info = Table(
        [[emp_lines, info_table]],
        colWidths=[USABLE_W - 75 * mm, 75 * mm],
    )
    addr_info.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(addr_info)
    elements.append(Spacer(1, 8 * mm))

    # === ZONE 4: Betreff ===
    if fs.betreff:
        elements.append(Paragraph(fs.betreff, styles["FSBetreff"]))
        elements.append(Spacer(1, 5 * mm))

    # === ZONE 5: Anrede ===
    if fs.anrede:
        elements.append(Paragraph(fs.anrede, styles["FSNormal"]))
        elements.append(Spacer(1, 4 * mm))

    # === ZONE 6: Brieftext ===
    if fs.brieftext:
        absaetze = fs.brieftext.split("\n\n")
        for i, absatz in enumerate(absaetze):
            text = absatz.replace("\n", "<br/>")
            elements.append(Paragraph(text, styles["FSNormal"]))
            if i < len(absaetze) - 1:
                elements.append(Spacer(1, 4 * mm))
        elements.append(Spacer(1, 8 * mm))

    # === ZONE 7: Grußformel + Unterschrift ===
    gruss = fs.grussformel or "Mit freundlichen Grüßen"
    elements.append(Paragraph(gruss, styles["FSGruss"]))
    elements.append(Spacer(1, 15 * mm))

    if supplier:
        elements.append(Paragraph(supplier.firma, styles["FSNormal"]))
        if supplier.inhaber:
            elements.append(Paragraph(supplier.inhaber, styles["FSGray"]))

    doc.build(elements, onFirstPage=canvas_helper.on_page, onLaterPages=canvas_helper.on_page)

    return pdf_path
