from dataclasses import dataclass, field


@dataclass
class RechnungsSummen:
    netto: float = 0.0
    rabatt_betrag: float = 0.0
    netto_nach_rabatt: float = 0.0
    mwst_details: dict[float, float] = field(default_factory=dict)
    mwst_gesamt: float = 0.0
    brutto: float = 0.0
    summe_35a: float = 0.0


def berechne_position(menge: float, einzelpreis: float) -> float:
    return round(menge * einzelpreis, 2)


def berechne_rechnung(
    positionen: list[dict],
    rabatt_typ: str | None = None,
    rabatt_wert: float = 0.0,
) -> RechnungsSummen:
    """
    Berechnet alle Summen einer Rechnung.

    positionen: Liste von dicts mit keys: gesamt_netto, mwst, beguenstigt_35a
    """
    summen = RechnungsSummen()

    if not positionen:
        return summen

    # Netto gesamt
    summen.netto = round(sum(p["gesamt_netto"] for p in positionen), 2)

    # Rabatt
    if rabatt_typ == "prozent" and rabatt_wert > 0:
        summen.rabatt_betrag = round(summen.netto * (rabatt_wert / 100), 2)
    elif rabatt_typ == "betrag" and rabatt_wert > 0:
        summen.rabatt_betrag = round(rabatt_wert, 2)

    summen.netto_nach_rabatt = round(summen.netto - summen.rabatt_betrag, 2)

    # MwSt nach Satz gruppiert, anteilig nach Rabatt
    mwst_gruppen: dict[float, float] = {}
    for p in positionen:
        satz = p["mwst"]
        mwst_gruppen[satz] = mwst_gruppen.get(satz, 0.0) + p["gesamt_netto"]

    for satz, summe_satz in mwst_gruppen.items():
        if summen.netto > 0:
            anteil = summe_satz / summen.netto
        else:
            anteil = 0.0
        netto_nach_rabatt_anteil = summe_satz - summen.rabatt_betrag * anteil
        mwst_betrag = round(netto_nach_rabatt_anteil * (satz / 100), 2)
        if satz > 0:
            summen.mwst_details[satz] = mwst_betrag

    summen.mwst_gesamt = round(sum(summen.mwst_details.values()), 2)
    summen.brutto = round(summen.netto_nach_rabatt + summen.mwst_gesamt, 2)

    # §35a Summe
    summen.summe_35a = round(
        sum(p["gesamt_netto"] for p in positionen if p.get("beguenstigt_35a")), 2
    )

    return summen
