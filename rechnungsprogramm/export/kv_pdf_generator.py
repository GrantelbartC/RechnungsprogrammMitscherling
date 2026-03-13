from pathlib import Path
from datetime import date, timedelta

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfgen.canvas import Canvas

from models.kostenvoranschlag import Kostenvoranschlag
from models.supplier import Supplier
from models.customer import Customer
from utils.paths import get_kv_pdf_path
from utils.calculations import berechne_rechnung


# Farben
COLOR_TEXT = HexColor("#111827")
COLOR_GRAY = HexColor("#6B7280")
COLOR_LINE = HexColor("#D1D5DB")
COLOR_HEADER_BG = HexColor("#F3F4F6")
COLOR_ACCENT = HexColor("#1E40AF")
COLOR_WARN = HexColor("#D97706")

PAGE_W, PAGE_H = A4
MARGIN_L = 20 * mm
MARGIN_R = 20 * mm
MARGIN_T = 15 * mm
MARGIN_B = 20 * mm
USABLE_W = PAGE_W - MARGIN_L - MARGIN_R

DISCLAIMER_TEXT = (
    "Die genannten Preise sind unverbindliche Schätzungen und können je nach "
    "tatsächlichem Aufwand abweichen."
)


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
        "KVNormal", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, leading=13,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "KVSmall", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, leading=11,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "KVGray", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, leading=11,
        textColor=COLOR_GRAY,
    ))
    styles.add(ParagraphStyle(
        "KVGraySmall", parent=styles["Normal"],
        fontName="Helvetica", fontSize=7, leading=9,
        textColor=COLOR_GRAY,
    ))
    styles.add(ParagraphStyle(
        "KVBold", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10, leading=13,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "KVTitle", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=14, leading=17,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "KVBetreff", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=12, leading=15,
        textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "KVRight", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, leading=13,
        alignment=TA_RIGHT, textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "KVRightBold", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10, leading=13,
        alignment=TA_RIGHT, textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "KVBrutto", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=12, leading=15,
        alignment=TA_RIGHT, textColor=COLOR_TEXT,
    ))
    styles.add(ParagraphStyle(
        "KVDank", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, leading=13,
        textColor=HexColor("#374151"),
    ))
    styles.add(ParagraphStyle(
        "KVHinweis", parent=styles["Normal"],
        fontName="Helvetica-Oblique", fontSize=9, leading=11,
        textColor=COLOR_GRAY,
    ))
    styles.add(ParagraphStyle(
        "KVDisclaimer", parent=styles["Normal"],
        fontName="Helvetica", fontSize=7, leading=9,
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


class KVCanvasHelper:
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


def generate_kv_pdf(kv: Kostenvoranschlag, supplier: Supplier, customer: Customer) -> Path:
    pdf_path = get_kv_pdf_path(kv.kvnr, kv.datum)
    styles = _get_styles()

    page_count = [0]
    canvas_helper = KVCanvasHelper(supplier, page_count)

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
    firm_lines.append(Paragraph(supplier.firma, styles["KVTitle"]))
    if supplier.inhaber:
        firm_lines.append(Paragraph(supplier.inhaber, styles["KVGray"]))
    if supplier.strasse:
        firm_lines.append(Paragraph(supplier.strasse, styles["KVGray"]))
    postfach_text = _fmt_postfach(supplier.postfach)
    if postfach_text:
        firm_lines.append(Paragraph(postfach_text, styles["KVGray"]))
    plz_ort = f"{supplier.plz or ''} {supplier.ort or ''}".strip()
    if plz_ort:
        firm_lines.append(Paragraph(plz_ort, styles["KVGray"]))
    if supplier.telefon:
        firm_lines.append(Paragraph(f"Tel: {supplier.telefon}", styles["KVGraySmall"]))
    if supplier.email:
        firm_lines.append(Paragraph(supplier.email, styles["KVGraySmall"]))

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
    elements.append(Paragraph(absender_text, styles["KVGraySmall"]))
    elements.append(Spacer(1, 3 * mm))

    # === ZONE 3: Empfänger + KV-Info ===
    emp_lines = []
    if customer.firma:
        emp_lines.append(Paragraph(customer.firma, styles["KVNormal"]))
    name_parts = []
    if customer.anrede:
        name_parts.append(customer.anrede)
    if customer.titel:
        name_parts.append(customer.titel)
    name_parts.append(customer.vorname)
    name_parts.append(customer.nachname)
    emp_lines.append(Paragraph(" ".join(name_parts), styles["KVNormal"]))
    if customer.strasse:
        emp_lines.append(Paragraph(customer.strasse, styles["KVNormal"]))
    cust_plz_ort = f"{customer.plz or ''} {customer.ort or ''}".strip()
    if cust_plz_ort:
        emp_lines.append(Paragraph(cust_plz_ort, styles["KVNormal"]))

    datum_str = _fmt_date(kv.datum)
    gueltig_bis_str = ""
    if kv.datum and not isinstance(kv.datum, str) and kv.gueltig_tage > 0:
        gueltig_bis_str = _fmt_date(kv.datum + timedelta(days=kv.gueltig_tage))

    info_data = [
        [Paragraph("Kostenvoranschlag", styles["KVGray"]),
         Paragraph(kv.kvnr, styles["KVRightBold"])],
        [Paragraph("Datum", styles["KVGray"]),
         Paragraph(datum_str, styles["KVRight"])],
        [Paragraph("Kunden-Nr.", styles["KVGray"]),
         Paragraph(f"K-{customer.id}", styles["KVRight"])],
    ]
    if gueltig_bis_str:
        info_data.append([
            Paragraph("Gültig bis", styles["KVGray"]),
            Paragraph(gueltig_bis_str, styles["KVRight"]),
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
    if kv.betreff:
        elements.append(Paragraph(kv.betreff, styles["KVBetreff"]))
        elements.append(Spacer(1, 3 * mm))

    # === ZONE 5: Objekt/WEG ===
    if kv.objekt_weg:
        elements.append(Paragraph(f"Objekt: {kv.objekt_weg}", styles["KVNormal"]))
        elements.append(Spacer(1, 3 * mm))

    # === ZONE 6: Positionstabelle ===
    col_widths = [10 * mm, 80 * mm, 20 * mm, 25 * mm, 15 * mm, 25 * mm]

    pos_header = [
        Paragraph("<b>Pos.</b>", styles["KVSmall"]),
        Paragraph("<b>Beschreibung</b>", styles["KVSmall"]),
        Paragraph("<b>Menge</b>", styles["KVSmall"]),
        Paragraph("<b>Einzelpreis</b>", styles["KVSmall"]),
        Paragraph("<b>MwSt</b>", styles["KVSmall"]),
        Paragraph("<b>Gesamt</b>", styles["KVSmall"]),
    ]
    pos_data = [pos_header]

    for line in kv.positionen:
        pos_data.append([
            Paragraph(str(line.position), styles["KVSmall"]),
            Paragraph(line.beschreibung, styles["KVSmall"]),
            Paragraph(f"{line.menge:.2f}".replace(".", ","), styles["KVSmall"]),
            Paragraph(_fmt_eur(line.einzelpreis), styles["KVSmall"]),
            Paragraph(f"{line.mwst:.0f}%", styles["KVSmall"]),
            Paragraph(_fmt_eur(line.gesamt_netto), styles["KVSmall"]),
        ])

    pos_table = Table(pos_data, colWidths=col_widths, repeatRows=1)
    pos_style = [
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER_BG),
        ("LINEABOVE", (0, 0), (-1, 0), 0.75, COLOR_LINE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, COLOR_LINE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(pos_data)):
        if i == len(pos_data) - 1:
            pos_style.append(("LINEBELOW", (0, i), (-1, i), 1, COLOR_TEXT))
        else:
            pos_style.append(("LINEBELOW", (0, i), (-1, i), 0.5, HexColor("#E5E7EB")))

    pos_table.setStyle(TableStyle(pos_style))
    elements.append(pos_table)
    elements.append(Spacer(1, 6 * mm))

    # === ZONE 7: Summenblock ===
    pos_list = [
        {"gesamt_netto": l.gesamt_netto, "mwst": l.mwst, "beguenstigt_35a": False}
        for l in kv.positionen
    ]
    summen = berechne_rechnung(pos_list, kv.rabatt_typ, kv.rabatt_wert)

    sum_data = []
    sum_data.append([
        Paragraph("Nettobetrag", styles["KVNormal"]),
        Paragraph(_fmt_eur(summen.netto), styles["KVRight"]),
    ])

    if summen.rabatt_betrag > 0:
        if kv.rabatt_typ == "prozent":
            rabatt_label = f"Rabatt ({kv.rabatt_wert:.0f}%)"
        else:
            rabatt_label = "Rabatt"
        sum_data.append([
            Paragraph(rabatt_label, ParagraphStyle("RabattLabel", parent=styles["KVNormal"], textColor=COLOR_WARN)),
            Paragraph(f"−{_fmt_eur(summen.rabatt_betrag)}",
                      ParagraphStyle("RabattVal", parent=styles["KVRight"], textColor=COLOR_WARN)),
        ])
        sum_data.append([
            Paragraph("Netto nach Rabatt", styles["KVBold"]),
            Paragraph(_fmt_eur(summen.netto_nach_rabatt), styles["KVRightBold"]),
        ])

    for satz in sorted(summen.mwst_details.keys()):
        betrag = summen.mwst_details[satz]
        sum_data.append([
            Paragraph(f"zzgl. {satz:.0f}% MwSt", styles["KVNormal"]),
            Paragraph(_fmt_eur(betrag), styles["KVRight"]),
        ])

    sum_data.append([
        Paragraph("<b>Gesamtbetrag</b>", styles["KVBrutto"]),
        Paragraph(f"<b>{_fmt_eur(summen.brutto)}</b>", styles["KVBrutto"]),
    ])

    sum_table = Table(sum_data, colWidths=[USABLE_W - 30 * mm, 30 * mm])
    sum_style = [
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, COLOR_ACCENT),
    ]
    sum_table.setStyle(TableStyle(sum_style))
    sum_table.hAlign = "LEFT"
    elements.append(sum_table)
    elements.append(Spacer(1, 6 * mm))

    # === Disclaimer ===
    elements.append(Paragraph(DISCLAIMER_TEXT, styles["KVDisclaimer"]))
    elements.append(Spacer(1, 6 * mm))

    # === Dankessatz + Hinweise ===
    if kv.dankessatz:
        elements.append(Paragraph(kv.dankessatz, styles["KVDank"]))
        elements.append(Spacer(1, 4 * mm))

    if kv.hinweise:
        elements.append(Paragraph(kv.hinweise, styles["KVHinweis"]))

    doc.build(elements, onFirstPage=canvas_helper.on_page, onLaterPages=canvas_helper.on_page)

    return pdf_path
