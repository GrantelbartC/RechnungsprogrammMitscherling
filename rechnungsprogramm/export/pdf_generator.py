from pathlib import Path
from datetime import date, timedelta
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
    PageBreak, KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfgen.canvas import Canvas

from models.invoice import Invoice
from models.supplier import Supplier
from models.customer import Customer
from utils.paths import get_pdf_path
from utils.calculations import berechne_rechnung


# Farben
COLOR_TEXT = HexColor("#111827")
COLOR_GRAY = HexColor("#6B7280")
COLOR_LINE = HexColor("#D1D5DB")
COLOR_HEADER_BG = HexColor("#F3F4F6")
COLOR_ACCENT = HexColor("#1E40AF")
COLOR_35A_BG = HexColor("#F0FDF4")
COLOR_35A_BORDER = HexColor("#BBF7D0")
COLOR_WARN = HexColor("#D97706")

PAGE_W, PAGE_H = A4
MARGIN_L = 20 * mm
MARGIN_R = 20 * mm
MARGIN_T = 15 * mm
MARGIN_B = 20 * mm
USABLE_W = PAGE_W - MARGIN_L - MARGIN_R


def _fmt_eur(value: float) -> str:
    """Formatiert als deutsches Währungsformat."""
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


def _get_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "InvNormal", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, leading=13,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "InvSmall", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, leading=11,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "InvGray", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, leading=11,
        textColor=COLOR_GRAY,
    ))
    styles.add(ParagraphStyle(
        "InvGraySmall", parent=styles["Normal"],
        fontName="Helvetica", fontSize=7, leading=9,
        textColor=COLOR_GRAY,
    ))
    styles.add(ParagraphStyle(
        "InvBold", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10, leading=13,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "InvTitle", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=14, leading=17,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "InvBetreff", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=12, leading=15,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "InvRight", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, leading=13,
        alignment=TA_RIGHT, textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "InvRightBold", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10, leading=13,
        alignment=TA_RIGHT, textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "InvBrutto", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=12, leading=15,
        alignment=TA_RIGHT, textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "Inv35aTitle", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=9, leading=11,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "Inv35aText", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, leading=11,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "InvDank", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, leading=13,
        textColor=HexColor("#374151"),
    ))
    styles.add(ParagraphStyle(
        "InvHinweis", parent=styles["Normal"],
        fontName="Helvetica-Oblique", fontSize=9, leading=11,
        textColor=COLOR_GRAY,
    ))
    styles.add(ParagraphStyle(
        "FooterLabel", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=7, leading=9,
        textColor=COLOR_GRAY,
    ))
    styles.add(ParagraphStyle(
        "FooterText", parent=styles["Normal"],
        fontName="Helvetica", fontSize=7, leading=9,
        textColor=COLOR_GRAY,
    ))
    return styles


class InvoiceCanvasHelper:
    """Zeichnet Header und Footer auf jeder Seite."""

    def __init__(self, supplier: Supplier, page_count_holder: list):
        self.supplier = supplier
        self.page_count_holder = page_count_holder

    def on_page(self, canvas: Canvas, doc):
        self.page_count_holder[0] += 1
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


def generate_pdf(invoice: Invoice, supplier: Supplier, customer: Customer) -> Path:
    pdf_path = get_pdf_path(invoice.rechnungsnr, invoice.datum)
    styles = _get_styles()

    page_count = [0]
    canvas_helper = InvoiceCanvasHelper(supplier, page_count)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T,
        bottomMargin=MARGIN_B + 15 * mm,  # Extra space for footer
    )

    elements = []

    # === ZONE 1: Kopfbereich (Logo + Firmendaten) ===
    header_data = []
    logo_cell = ""
    if supplier.logo_path and Path(supplier.logo_path).exists():
        try:
            logo_cell = Image(supplier.logo_path, width=50 * mm, height=25 * mm)
            logo_cell.hAlign = "LEFT"
        except Exception:
            logo_cell = ""

    firm_lines = []
    firm_lines.append(Paragraph(supplier.firma, styles["InvTitle"]))
    if supplier.inhaber:
        firm_lines.append(Paragraph(supplier.inhaber, styles["InvGray"]))
    if supplier.strasse:
        firm_lines.append(Paragraph(supplier.strasse, styles["InvGray"]))
    plz_ort = f"{supplier.plz or ''} {supplier.ort or ''}".strip()
    if plz_ort:
        firm_lines.append(Paragraph(plz_ort, styles["InvGray"]))
    if supplier.telefon:
        firm_lines.append(Paragraph(f"Tel: {supplier.telefon}", styles["InvGraySmall"]))
    if supplier.email:
        firm_lines.append(Paragraph(supplier.email, styles["InvGraySmall"]))

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
    if plz_ort:
        absender_parts.append(plz_ort)
    absender_text = " · ".join(absender_parts)
    elements.append(Paragraph(absender_text, styles["InvGraySmall"]))
    elements.append(Spacer(1, 3 * mm))

    # === ZONE 3: Empfänger + Rechnungsinfo ===
    # Empfänger
    emp_lines = []
    if customer.firma:
        emp_lines.append(Paragraph(customer.firma, styles["InvNormal"]))
    name_parts = []
    if customer.anrede:
        name_parts.append(customer.anrede)
    if customer.titel:
        name_parts.append(customer.titel)
    name_parts.append(customer.vorname)
    name_parts.append(customer.nachname)
    emp_lines.append(Paragraph(" ".join(name_parts), styles["InvNormal"]))
    if customer.strasse:
        emp_lines.append(Paragraph(customer.strasse, styles["InvNormal"]))
    cust_plz_ort = f"{customer.plz or ''} {customer.ort or ''}".strip()
    if cust_plz_ort:
        emp_lines.append(Paragraph(cust_plz_ort, styles["InvNormal"]))

    # Rechnungsinfo
    datum_str = _fmt_date(invoice.datum)
    zahlbar_bis = ""
    if invoice.datum:
        if isinstance(invoice.datum, str):
            zahlbar_bis = ""
        else:
            ziel_datum = invoice.datum + timedelta(days=invoice.zahlungsziel)
            zahlbar_bis = _fmt_date(ziel_datum)

    info_data = [
        [Paragraph("Rechnungsnr.", styles["InvGray"]),
         Paragraph(invoice.rechnungsnr, styles["InvRightBold"])],
        [Paragraph("Rechnungsdatum", styles["InvGray"]),
         Paragraph(datum_str, styles["InvRight"])],
        [Paragraph("Kunden-Nr.", styles["InvGray"]),
         Paragraph(f"K-{customer.id}", styles["InvRight"])],
    ]
    if zahlbar_bis:
        info_data.append([
            Paragraph("Zahlbar bis", styles["InvGray"]),
            Paragraph(zahlbar_bis, styles["InvRight"]),
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
    if invoice.betreff:
        elements.append(Paragraph(invoice.betreff, styles["InvBetreff"]))
        elements.append(Spacer(1, 3 * mm))

    # === ZONE 5: Objekt/WEG ===
    if invoice.objekt_weg:
        elements.append(Paragraph(f"Objekt: {invoice.objekt_weg}", styles["InvNormal"]))
        elements.append(Spacer(1, 3 * mm))

    # === ZONE 6: Ausführungshinweis ===
    if invoice.ausfuehrungsdatum:
        elements.append(Paragraph(
            f"Leistungsdatum: {_fmt_date(invoice.ausfuehrungsdatum)}",
            styles["InvNormal"]
        ))
        elements.append(Spacer(1, 3 * mm))
    elif invoice.zeitraum:
        elements.append(Paragraph(
            f"Leistungszeitraum: {invoice.zeitraum}",
            styles["InvNormal"]
        ))
        elements.append(Spacer(1, 3 * mm))

    # === ZONE 7: Positionstabelle ===
    col_widths = [10 * mm, 75 * mm, 20 * mm, 25 * mm, 15 * mm, 25 * mm]

    pos_header = [
        Paragraph("<b>Pos.</b>", styles["InvSmall"]),
        Paragraph("<b>Beschreibung</b>", styles["InvSmall"]),
        Paragraph("<b>Menge</b>", styles["InvSmall"]),
        Paragraph("<b>Einzelpreis</b>", styles["InvSmall"]),
        Paragraph("<b>MwSt</b>", styles["InvSmall"]),
        Paragraph("<b>Gesamt</b>", styles["InvSmall"]),
    ]
    pos_data = [pos_header]

    for line in invoice.positionen:
        pos_data.append([
            Paragraph(str(line.position), styles["InvSmall"]),
            Paragraph(line.beschreibung, styles["InvSmall"]),
            Paragraph(f"{line.menge:.2f}".replace(".", ","), styles["InvSmall"]),
            Paragraph(_fmt_eur(line.einzelpreis), styles["InvSmall"]),
            Paragraph(f"{line.mwst:.0f}%", styles["InvSmall"]),
            Paragraph(_fmt_eur(line.gesamt_netto), styles["InvSmall"]),
        ])

    pos_table = Table(pos_data, colWidths=col_widths, repeatRows=1)
    pos_style = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER_BG),
        ("LINEABOVE", (0, 0), (-1, 0), 0.75, COLOR_LINE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, COLOR_LINE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        # Alignment
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    # Zeilen-Trennlinien
    for i in range(1, len(pos_data)):
        if i == len(pos_data) - 1:
            pos_style.append(("LINEBELOW", (0, i), (-1, i), 1, COLOR_TEXT))
        else:
            pos_style.append(("LINEBELOW", (0, i), (-1, i), 0.5, HexColor("#E5E7EB")))

    pos_table.setStyle(TableStyle(pos_style))
    elements.append(pos_table)
    elements.append(Spacer(1, 6 * mm))

    # === ZONE 8: Summenblock ===
    pos_list = [
        {"gesamt_netto": l.gesamt_netto, "mwst": l.mwst, "beguenstigt_35a": l.beguenstigt_35a}
        for l in invoice.positionen
    ]
    summen = berechne_rechnung(pos_list, invoice.rabatt_typ, invoice.rabatt_wert)

    sum_data = []
    sum_data.append([
        Paragraph("Nettobetrag", styles["InvNormal"]),
        Paragraph(_fmt_eur(summen.netto), styles["InvRight"]),
    ])

    if summen.rabatt_betrag > 0:
        if invoice.rabatt_typ == "prozent":
            rabatt_label = f"Rabatt ({invoice.rabatt_wert:.0f}%)"
        else:
            rabatt_label = "Rabatt"
        sum_data.append([
            Paragraph(rabatt_label, ParagraphStyle("RabattLabel", parent=styles["InvNormal"], textColor=COLOR_WARN)),
            Paragraph(f"−{_fmt_eur(summen.rabatt_betrag)}",
                      ParagraphStyle("RabattVal", parent=styles["InvRight"], textColor=COLOR_WARN)),
        ])
        sum_data.append([
            Paragraph("Netto nach Rabatt", styles["InvBold"]),
            Paragraph(_fmt_eur(summen.netto_nach_rabatt), styles["InvRightBold"]),
        ])

    for satz in sorted(summen.mwst_details.keys()):
        betrag = summen.mwst_details[satz]
        sum_data.append([
            Paragraph(f"zzgl. {satz:.0f}% MwSt", styles["InvNormal"]),
            Paragraph(_fmt_eur(betrag), styles["InvRight"]),
        ])

    sum_data.append([
        Paragraph("<b>Bruttobetrag</b>", styles["InvBrutto"]),
        Paragraph(f"<b>{_fmt_eur(summen.brutto)}</b>", styles["InvBrutto"]),
    ])

    sum_table = Table(sum_data, colWidths=[45 * mm, 30 * mm])
    sum_style = [
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        # Linie über Brutto
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, COLOR_ACCENT),
    ]
    sum_table.setStyle(TableStyle(sum_style))
    sum_table.hAlign = "RIGHT"
    elements.append(sum_table)
    elements.append(Spacer(1, 8 * mm))

    # === ZONE 9: §35a-Hinweisbox ===
    betrag_35a = invoice.lohnanteil_35a + invoice.geraeteanteil_35a
    if betrag_35a > 0:
        box_content = []
        box_content.append(Paragraph("Begünstigte Anteile nach §35a EStG", styles["Inv35aTitle"]))
        box_content.append(Spacer(1, 2 * mm))
        box_content.append(Paragraph(
            f"In dem Rechnungsbetrag von {_fmt_eur(summen.brutto)} sind folgende begünstigte Anteile enthalten:",
            styles["Inv35aText"]
        ))
        box_content.append(Spacer(1, 2 * mm))

        detail_data = [
            [
                Paragraph("<b>Lohn- &amp; Geräteanteil §35a:</b>", styles["Inv35aText"]),
                Paragraph(f"<b>{_fmt_eur(betrag_35a)}</b>", styles["InvRight"]),
            ],
        ]

        detail_table = Table(detail_data, colWidths=[50 * mm, 30 * mm])
        detail_table.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        box_content.append(detail_table)

        # Wrap in box
        box_table = Table([[box_content]], colWidths=[USABLE_W - 4 * mm])
        box_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_35A_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_35A_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(box_table)
        elements.append(Spacer(1, 8 * mm))

    # === ZONE 10: Dankessatz + Hinweise ===
    if invoice.dankessatz:
        elements.append(Paragraph(invoice.dankessatz, styles["InvDank"]))
        elements.append(Spacer(1, 4 * mm))

    if invoice.hinweise:
        elements.append(Paragraph(invoice.hinweise, styles["InvHinweis"]))

    # Build PDF
    doc.build(elements, onFirstPage=canvas_helper.on_page, onLaterPages=canvas_helper.on_page)

    return pdf_path
