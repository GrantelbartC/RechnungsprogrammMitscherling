from dataclasses import dataclass


STRUCTURED_SCHEMA = '{"betreff":"...", "anrede":"...", "brieftext":"...", "grussformel":"..."}'

TONE_GUIDANCE = {
    "neutral": "Sachlich, ruhig und professionell.",
    "freundlich": "Freundlich, zugewandt und professionell.",
    "foermlich": "Foermlich, verbindlich und klar.",
}


@dataclass
class LetterContext:
    supplier_name: str = ""
    supplier_contact: str = ""
    supplier_signatory: str = ""
    customer_name: str = ""
    customer_company: str = ""
    customer_contact: str = ""
    suggested_salutation: str = ""
    current_subject: str = ""
    current_salutation: str = ""
    current_body: str = ""
    current_closing: str = ""


def build_generation_messages(
    prompt: str,
    context: LetterContext | None,
    tone: str,
    structured: bool = True,
) -> list[dict[str, str]]:
    system_parts = [
        "Du verfasst deutsche Geschaeftskorrespondenz fuer kleine Unternehmen.",
        "Schreibe natuerlich, praezise und professionell.",
        "Verwende nur Informationen aus Aufgabe und Kontext.",
        "Erfinde keine Fakten, Fristen, Betraege, Ansprechpartner oder Zusagen.",
        "Wenn Informationen fehlen, formuliere neutral und ohne Platzhalter.",
        "Nutze grundsaetzlich die Sie-Form, sofern die Aufgabe nichts anderes verlangt.",
    ]
    if structured:
        system_parts.append(
            "Antworte ausschliesslich mit einem gueltigen JSON-Objekt ohne Markdown oder Codeblock."
        )
        system_parts.append(
            f"Schema: {STRUCTURED_SCHEMA}"
        )
        system_parts.append(
            "Der Betreff ist kurz und konkret. Die Anrede endet mit Komma. "
            "Der Brieftext enthaelt nur den eigentlichen Schreibeninhalt. "
            "Die Grussformel enthaelt keine Signatur oder Namenswiederholung."
        )
    else:
        system_parts.append(
            "Antworte ohne JSON, aber mit genau vier Abschnitten in dieser Reihenfolge: "
            "Betreff:, Anrede:, Brieftext:, Grussformel:."
        )
        system_parts.append(
            "Nutze die Labels exakt so, damit die Antwort sicher in die Formularfelder uebernommen werden kann."
        )

    user_parts = [
        f"Aufgabe:\n{prompt.strip()}",
        f"Gewuenschter Stil: {_describe_tone(tone)}",
        "Ziel: Erzeuge ein sofort verwendbares Firmenschreiben mit Betreff, Anrede, Brieftext und Grussformel.",
    ]

    context_block = _format_context_block(context)
    if context_block:
        user_parts.append(context_block)

    return [
        {"role": "system", "content": "\n".join(system_parts)},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def build_revision_messages(
    current_draft: dict[str, str],
    instruction: str,
    context: LetterContext | None,
) -> list[dict[str, str]]:
    system = "\n".join(
        [
            "Du ueberarbeitest deutsche Geschaeftskorrespondenz.",
            "Aendere nur so viel wie fuer die Anweisung noetig ist.",
            "Behalte bekannte Fakten, Fristen, Namen und den Kern der Aussage bei.",
            "Erfinde keine neuen Details.",
            "Antworte ausschliesslich mit einem gueltigen JSON-Objekt ohne Markdown oder Codeblock.",
            f"Schema: {STRUCTURED_SCHEMA}",
        ]
    )

    user_parts = [
        f"Ueberarbeite den bestehenden Entwurf mit dieser Anweisung:\n{instruction.strip()}",
        "Behalte Anlass und Sachverhalt bei, sofern die Anweisung nichts anderes verlangt.",
        "Aktueller Entwurf:",
        _format_draft(current_draft),
    ]

    context_block = _format_context_block(context)
    if context_block:
        user_parts.append(context_block)

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def _format_context_block(context: LetterContext | None) -> str:
    if not context:
        return ""

    sender_lines = []
    if context.supplier_name:
        sender_lines.append(f"Absender/Firma: {context.supplier_name}")
    if context.supplier_signatory:
        sender_lines.append(f"Unterzeichner: {context.supplier_signatory}")
    if context.supplier_contact:
        sender_lines.append(f"Absenderdaten: {context.supplier_contact}")

    recipient_lines = []
    if context.customer_name:
        recipient_lines.append(f"Empfaengername: {context.customer_name}")
    if context.customer_company:
        recipient_lines.append(f"Empfaengerfirma: {context.customer_company}")
    if context.customer_contact:
        recipient_lines.append(f"Empfaengerdaten: {context.customer_contact}")
    if context.suggested_salutation:
        recipient_lines.append(f"Anredevorschlag: {context.suggested_salutation}")

    draft_lines = []
    if context.current_subject:
        draft_lines.append(f"Betreff: {context.current_subject}")
    if context.current_salutation:
        draft_lines.append(f"Anrede: {context.current_salutation}")
    if context.current_body:
        draft_lines.append(f"Brieftext: {context.current_body}")
    if context.current_closing:
        draft_lines.append(f"Grussformel: {context.current_closing}")

    blocks = []
    if sender_lines:
        blocks.append("Absender:\n" + "\n".join(sender_lines))
    if recipient_lines:
        blocks.append("Empfaenger:\n" + "\n".join(recipient_lines))
    if draft_lines:
        blocks.append("Bestehender Entwurf:\n" + "\n".join(draft_lines))

    if not blocks:
        return ""

    return "Kontext:\n" + "\n\n".join(blocks)


def _format_draft(current_draft: dict[str, str]) -> str:
    return "\n".join(
        [
            f"Betreff: {current_draft.get('betreff', '').strip()}",
            f"Anrede: {current_draft.get('anrede', '').strip()}",
            f"Brieftext: {current_draft.get('brieftext', '').strip()}",
            f"Grussformel: {current_draft.get('grussformel', '').strip()}",
        ]
    )


def _describe_tone(tone: str | None) -> str:
    normalized = (tone or "neutral").strip().lower()
    return TONE_GUIDANCE.get(normalized, TONE_GUIDANCE["neutral"])
