from datetime import date, timedelta
from pathlib import Path

from models.invoice import Invoice
from models.supplier import Supplier
from models.customer import Customer
from utils.calculations import berechne_rechnung


def generate_zugferd_pdf(
    invoice: Invoice,
    supplier: Supplier,
    customer: Customer,
    pdf_path: Path,
) -> Path:
    """
    Nimmt eine bestehende PDF und bettet ZUGFeRD-XML (Factur-X COMFORT) ein.
    Gibt den Pfad zur ZUGFeRD-PDF zurück.
    """
    try:
        from facturx import generate_from_file
    except ImportError:
        raise ImportError(
            "factur-x Bibliothek nicht installiert. "
            "Bitte installieren: pip install factur-x"
        )

    xml_content = _generate_xml(invoice, supplier, customer)

    # factur-x schreibt die Datei selbst; deshalb den Dateipfad uebergeben
    # statt eines read-only File-Handles.
    generate_from_file(
        str(pdf_path),
        xml_content.encode("utf-8"),
        flavor="factur-x",
        level="en16931",
    )

    return pdf_path


def _generate_xml(invoice: Invoice, supplier: Supplier, customer: Customer) -> str:
    """Generiert Factur-X XML im COMFORT-Profil (EN16931/CII)."""

    datum_str = ""
    if isinstance(invoice.datum, date):
        datum_str = invoice.datum.strftime("%Y%m%d")
    elif isinstance(invoice.datum, str):
        datum_str = invoice.datum.replace("-", "")

    zahlbar_str = ""
    if isinstance(invoice.datum, date):
        zahlbar = invoice.datum + timedelta(days=invoice.zahlungsziel)
        zahlbar_str = zahlbar.strftime("%Y%m%d")

    # Summen berechnen
    pos_data = [
        {"gesamt_netto": l.gesamt_netto, "mwst": l.mwst, "beguenstigt_35a": l.beguenstigt_35a}
        for l in invoice.positionen
    ]
    summen = berechne_rechnung(pos_data, invoice.rabatt_typ, invoice.rabatt_wert)

    # MwSt-Gruppen für XML
    mwst_xml = ""
    for satz, betrag in sorted(summen.mwst_details.items()):
        # Anteil der Basis berechnen
        if summen.netto > 0:
            gruppen_netto = sum(
                p["gesamt_netto"] for p in pos_data if p["mwst"] == satz
            )
            anteil = gruppen_netto / summen.netto
            basis = gruppen_netto - summen.rabatt_betrag * anteil
        else:
            basis = 0

        mwst_xml += f"""
            <ram:ApplicableTradeTax>
                <ram:CalculatedAmount>{betrag:.2f}</ram:CalculatedAmount>
                <ram:TypeCode>VAT</ram:TypeCode>
                <ram:BasisAmount>{basis:.2f}</ram:BasisAmount>
                <ram:CategoryCode>S</ram:CategoryCode>
                <ram:RateApplicablePercent>{satz:.2f}</ram:RateApplicablePercent>
            </ram:ApplicableTradeTax>"""

    # Positionen
    lines_xml = ""
    for line in invoice.positionen:
        lines_xml += f"""
        <ram:IncludedSupplyChainTradeLineItem>
            <ram:AssociatedDocumentLineDocument>
                <ram:LineID>{line.position}</ram:LineID>
            </ram:AssociatedDocumentLineDocument>
            <ram:SpecifiedTradeProduct>
                <ram:Name>{_xml_escape(line.beschreibung)}</ram:Name>
            </ram:SpecifiedTradeProduct>
            <ram:SpecifiedLineTradeAgreement>
                <ram:NetPriceProductTradePrice>
                    <ram:ChargeAmount>{line.einzelpreis:.2f}</ram:ChargeAmount>
                </ram:NetPriceProductTradePrice>
            </ram:SpecifiedLineTradeAgreement>
            <ram:SpecifiedLineTradeDelivery>
                <ram:BilledQuantity unitCode="C62">{line.menge:.2f}</ram:BilledQuantity>
            </ram:SpecifiedLineTradeDelivery>
            <ram:SpecifiedLineTradeSettlement>
                <ram:ApplicableTradeTax>
                    <ram:TypeCode>VAT</ram:TypeCode>
                    <ram:CategoryCode>S</ram:CategoryCode>
                    <ram:RateApplicablePercent>{line.mwst:.2f}</ram:RateApplicablePercent>
                </ram:ApplicableTradeTax>
                <ram:SpecifiedTradeSettlementLineMonetarySummation>
                    <ram:LineTotalAmount>{line.gesamt_netto:.2f}</ram:LineTotalAmount>
                </ram:SpecifiedTradeSettlementLineMonetarySummation>
            </ram:SpecifiedLineTradeSettlement>
        </ram:IncludedSupplyChainTradeLineItem>"""

    # Zahlungsanweisung
    payment_xml = ""
    if supplier.iban:
        payment_xml = f"""
            <ram:SpecifiedTradeSettlementPaymentMeans>
                <ram:TypeCode>58</ram:TypeCode>
                <ram:PayeePartyCreditorFinancialAccount>
                    <ram:IBANID>{_xml_escape(supplier.iban.replace(' ', ''))}</ram:IBANID>
                </ram:PayeePartyCreditorFinancialAccount>"""
        if supplier.bic:
            payment_xml += f"""
                <ram:PayeeSpecifiedCreditorFinancialInstitution>
                    <ram:BICID>{_xml_escape(supplier.bic)}</ram:BICID>
                </ram:PayeeSpecifiedCreditorFinancialInstitution>"""
        payment_xml += """
            </ram:SpecifiedTradeSettlementPaymentMeans>"""

    # Zahlungsfrist
    payment_terms = ""
    if zahlbar_str:
        payment_terms = f"""
            <ram:SpecifiedTradePaymentTerms>
                <ram:DueDateDateTime>
                    <udt:DateTimeString format="102">{zahlbar_str}</udt:DateTimeString>
                </ram:DueDateDateTime>
            </ram:SpecifiedTradePaymentTerms>"""

    # Supplier Steuer-ID
    seller_tax = ""
    if supplier.ustid:
        seller_tax += f"""
                <ram:SpecifiedTaxRegistration>
                    <ram:ID schemeID="VA">{_xml_escape(supplier.ustid)}</ram:ID>
                </ram:SpecifiedTaxRegistration>"""
    if supplier.steuernr:
        seller_tax += f"""
                <ram:SpecifiedTaxRegistration>
                    <ram:ID schemeID="FC">{_xml_escape(supplier.steuernr)}</ram:ID>
                </ram:SpecifiedTaxRegistration>"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice
    xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"
    xmlns:qdt="urn:un:unece:uncefact:data:standard:QualifiedDataType:100">

    <rsm:ExchangedDocumentContext>
        <ram:GuidelineSpecifiedDocumentContextParameter>
            <ram:ID>urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:comfort</ram:ID>
        </ram:GuidelineSpecifiedDocumentContextParameter>
    </rsm:ExchangedDocumentContext>

    <rsm:ExchangedDocument>
        <ram:ID>{_xml_escape(invoice.rechnungsnr)}</ram:ID>
        <ram:TypeCode>380</ram:TypeCode>
        <ram:IssueDateTime>
            <udt:DateTimeString format="102">{datum_str}</udt:DateTimeString>
        </ram:IssueDateTime>
    </rsm:ExchangedDocument>

    <rsm:SupplyChainTradeTransaction>
{lines_xml}
        <ram:ApplicableHeaderTradeAgreement>
            <ram:SellerTradeParty>
                <ram:Name>{_xml_escape(supplier.firma)}</ram:Name>
                <ram:PostalTradeAddress>
                    <ram:PostcodeCode>{_xml_escape(supplier.plz or '')}</ram:PostcodeCode>
                    <ram:LineOne>{_xml_escape(supplier.strasse or '')}</ram:LineOne>
                    <ram:CityName>{_xml_escape(supplier.ort or '')}</ram:CityName>
                    <ram:CountryID>DE</ram:CountryID>
                </ram:PostalTradeAddress>{seller_tax}
            </ram:SellerTradeParty>
            <ram:BuyerTradeParty>
                <ram:Name>{_xml_escape(customer.full_name)}</ram:Name>
                <ram:PostalTradeAddress>
                    <ram:PostcodeCode>{_xml_escape(customer.plz or '')}</ram:PostcodeCode>
                    <ram:LineOne>{_xml_escape(customer.strasse or '')}</ram:LineOne>
                    <ram:CityName>{_xml_escape(customer.ort or '')}</ram:CityName>
                    <ram:CountryID>DE</ram:CountryID>
                </ram:PostalTradeAddress>
            </ram:BuyerTradeParty>
        </ram:ApplicableHeaderTradeAgreement>

        <ram:ApplicableHeaderTradeDelivery/>

        <ram:ApplicableHeaderTradeSettlement>
            <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>{payment_xml}{mwst_xml}{payment_terms}
            <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
                <ram:LineTotalAmount>{summen.netto:.2f}</ram:LineTotalAmount>
                <ram:TaxBasisTotalAmount>{summen.netto_nach_rabatt:.2f}</ram:TaxBasisTotalAmount>
                <ram:TaxTotalAmount currencyID="EUR">{summen.mwst_gesamt:.2f}</ram:TaxTotalAmount>
                <ram:GrandTotalAmount>{summen.brutto:.2f}</ram:GrandTotalAmount>
                <ram:DuePayableAmount>{summen.brutto:.2f}</ram:DuePayableAmount>
            </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        </ram:ApplicableHeaderTradeSettlement>
    </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>"""

    return xml


def _xml_escape(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
