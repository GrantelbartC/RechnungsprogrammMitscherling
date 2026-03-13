from pathlib import Path
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.pdfgen.canvas import Canvas

from models.invoice import Invoice
from models.supplier import Supplier
from models.customer import Customer
from utils.paths import get_mahnung_pdf_path


# Farben
COLOR_TEXT = HexColor("#111827")
COLOR_GRAY = HexColor("#6B7280")
COLOR_LINE = HexColor("#D1D5DB")

PAGE_W, PAGE_H = A4
MARGIN_L = 20 * mm
MARGIN_R = 20 * mm
MARGIN_T = 15 * mm
MARGIN_B = 20 * mm
USABLE_W = PAGE_W - MARGIN_L - MARGIN_R


def _fmt_eur(value: float) -> str:
    s = f"{value:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


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
        "MahnNormal", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, leading=13,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "MahnGray", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, leading=11,
        textColor=COLOR_GRAY,
    ))
    styles.add(ParagraphStyle(
        "MahnGraySmall", parent=styles["Normal"],
        fontName="Helvetica", fontSize=7, leading=9,
        textColor=COLOR_GRAY,
    ))
    styles.add(ParagraphStyle(
        "MahnBold", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10, leading=13,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "MahnTitle", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=14, leading=17,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "MahnBody", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, leading=15,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "MahnRight", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, leading=13,
        alignment=TA_RIGHT, textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "MahnFooterLabel", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=7, leading=9,
        textColor=COLOR_GRAY,
    ))
    styles.add(ParagraphStyle(
        "MahnFooterText", parent=styles["Normal"],
        fontName="Helvetica", fontSize=7, leading=9,
        textColor=COLOR_GRAY,
    ))
    return styles


class MahnCanvasHelper:
    """Zeichnet Footer auf jeder Seite."""

    def __init__(self, supplier: Supplier):
        self.supplier = supplier

    def on_page(self, canvas: Canvas, doc):
        self._draw_footer(canvas, doc)

    def _draw_footer(self, canvas: Canvas, doc):
        s = self.supplier
        y = MARGIN_B - 5 * mm
        col_w = USABLE_W / 3

        # Trennlinie
        canvas.setStrokeColor(COLOR_LINE)
        canvas.setLineWidth(0.75)
        canvas.line(MARGIN_L, y + 12, PAGE_W - MARGIN_R, y + 12)

        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(COLOR_GRAY)

        # Spalte 1: Bankverbindung
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

        # Spalte 2: Steuerdaten
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

        # Spalte 3: Kontakt
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


def get_mahnung_template_text(
    mahnung_typ: str,
    customer: Customer,
    invoice: Invoice,
) -> str:
    """Generiert den vorausgefüllten Brieftext (ohne Grußformel)."""
    brutto_fmt = _fmt_eur(invoice.brutto or 0.0)

    anrede_parts = []
    if customer.anrede:
        anrede_parts.append(customer.anrede)
    if customer.titel:
        anrede_parts.append(customer.titel)
    if customer.vorname:
        anrede_parts.append(customer.vorname)
    if customer.nachname:
        anrede_parts.append(customer.nachname)
    anrede_name = " ".join(anrede_parts).strip() or customer.firma or "Damen und Herren"

    if mahnung_typ == "Zahlungserinnerung":
        return (
            f"Sehr geehrte(r) {anrede_name},\n\n"
            "wir erlauben uns, Sie freundlich daran zu erinnern, dass folgende "
            "Rechnung noch offen ist.\n\n"
            "Möglicherweise hat sich diese Zahlung mit unserem Schreiben gekreuzt. "
            "Falls dies der Fall ist, betrachten Sie dieses Schreiben als gegenstandslos.\n\n"
            f"Wir bitten Sie, den ausstehenden Betrag von {brutto_fmt} "
            "baldmöglichst auf unser Konto zu überweisen."
        )
    else:  # "2. Mahnung"
        return (
            f"Sehr geehrte(r) {anrede_name},\n\n"
            "leider müssen wir feststellen, dass die folgende Rechnung trotz unserer "
            "Zahlungserinnerung bisher noch nicht beglichen wurde.\n\n"
            f"Wir bitten Sie dringend, den ausstehenden Betrag von {brutto_fmt} "
            "innerhalb von 7 Tagen auf unser Konto zu überweisen.\n\n"
            "Sollten Sie zwischenzeitlich gezahlt haben, bitten wir Sie, "
            "dieses Schreiben als gegenstandslos zu betrachten."
        )


def generate_mahnung_pdf(
    invoice: Invoice,
    supplier: Supplier,
    customer: Customer,
    mahnung_typ: str,
    mahnung_datum: date,
    body_text: str,
) -> Path:
    """Generiert die Mahnung/Zahlungserinnerung als PDF und gibt den Pfad zurück."""
    typ_slug = "Zahlungserinnerung" if mahnung_typ == "Zahlungserinnerung" else "2-Mahnung"
    pdf_path = get_mahnung_pdf_path(invoice.rechnungsnr, typ_slug, mahnung_datum)
    styles = _get_styles()
    canvas_helper = MahnCanvasHelper(supplier)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T,
        bottomMargin=MARGIN_B + 15 * mm,
    )

    elements = []

    # === ZONE 1: Kopfbereich (Logo + Firmendaten) ===
    logo_cell = ""
    if supplier.logo_path and Path(supplier.logo_path).exists():
        try:
            logo_cell = Image(supplier.logo_path, width=50 * mm, height=25 * mm)
            logo_cell.hAlign = "LEFT"
        except Exception:
            logo_cell = ""

    firm_lines = []
    firm_lines.append(Paragraph(supplier.firma, styles["MahnTitle"]))
    if supplier.inhaber:
        firm_lines.append(Paragraph(supplier.inhaber, styles["MahnGray"]))
    if supplier.strasse:
        firm_lines.append(Paragraph(supplier.strasse, styles["MahnGray"]))
    postfach_text = _fmt_postfach(getattr(supplier, "postfach", None))
    if postfach_text:
        firm_lines.append(Paragraph(postfach_text, styles["MahnGray"]))
    plz_ort = f"{supplier.plz or ''} {supplier.ort or ''}".strip()
    if plz_ort:
        firm_lines.append(Paragraph(plz_ort, styles["MahnGray"]))
    if supplier.telefon:
        firm_lines.append(Paragraph(f"Tel: {supplier.telefon}", styles["MahnGraySmall"]))
    if supplier.email:
        firm_lines.append(Paragraph(supplier.email, styles["MahnGraySmall"]))

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

    # Trennlinie
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
    elements.append(Paragraph(absender_text, styles["MahnGraySmall"]))
    elements.append(Spacer(1, 3 * mm))

    # === ZONE 3: Empfänger (links) + Datum (rechts) ===
    emp_lines = []
    if customer.firma:
        emp_lines.append(Paragraph(customer.firma, styles["MahnNormal"]))
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
        emp_lines.append(Paragraph(" ".join(name_parts), styles["MahnNormal"]))
    if customer.strasse:
        emp_lines.append(Paragraph(customer.strasse, styles["MahnNormal"]))
    cust_plz_ort = f"{customer.plz or ''} {customer.ort or ''}".strip()
    if cust_plz_ort:
        emp_lines.append(Paragraph(cust_plz_ort, styles["MahnNormal"]))

    datum_block = [
        Spacer(1, 2 * mm),
        Paragraph(_fmt_date(mahnung_datum), styles["MahnRight"]),
    ]

    addr_date_table = Table(
        [[emp_lines, datum_block]],
        colWidths=[USABLE_W - 50 * mm, 50 * mm],
    )
    addr_date_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(addr_date_table)
    elements.append(Spacer(1, 8 * mm))

    # === ZONE 4: Titel ===
    elements.append(Paragraph(mahnung_typ, styles["MahnTitle"]))
    elements.append(Spacer(1, 2 * mm))

    # === ZONE 5: Bezug zur Rechnung ===
    ref_text = f"Rechnung Nr. {invoice.rechnungsnr} vom {_fmt_date(invoice.datum)}"
    elements.append(Paragraph(ref_text, styles["MahnNormal"]))
    elements.append(Spacer(1, 8 * mm))

    # === ZONE 6: Body-Text ===
    for line in body_text.split("\n"):
        if line.strip():
            elements.append(Paragraph(line, styles["MahnBody"]))
            elements.append(Spacer(1, 2 * mm))
        else:
            elements.append(Spacer(1, 4 * mm))

    # === ZONE 7: Grußformel ===
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("Mit freundlichen Grüßen", styles["MahnNormal"]))
    elements.append(Spacer(1, 12 * mm))
    elements.append(Paragraph("Peter Mitscherling", styles["MahnBold"]))

    doc.build(
        elements,
        onFirstPage=canvas_helper.on_page,
        onLaterPages=canvas_helper.on_page,
    )

    return pdf_path
