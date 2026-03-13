import json
import re
import unicodedata
import urllib.error
import urllib.request

from services.ai_config import load_ai_config, load_ai_preferences, resolve_model
from services.ai_prompt_builder import (
    LetterContext,
    build_generation_messages,
    build_revision_messages,
)


REQUIRED_FIELDS = ("betreff", "anrede", "brieftext", "grussformel")

FIELD_ALIASES = {
    "betreff": "betreff",
    "betreffzeile": "betreff",
    "subject": "betreff",
    "anrede": "anrede",
    "salutation": "anrede",
    "brieftext": "brieftext",
    "text": "brieftext",
    "nachricht": "brieftext",
    "anschreiben": "brieftext",
    "grussformel": "grussformel",
    "schlussformel": "grussformel",
    "gruss": "grussformel",
    "closing": "grussformel",
}

FIELD_TRANSLATION = str.maketrans(
    {
        ord(chr(223)): "ss",
        ord(chr(228)): "ae",
        ord(chr(246)): "oe",
        ord(chr(252)): "ue",
    }
)


class AIServiceError(RuntimeError):
    pass


class AITextService:
    def __init__(self):
        self.config = load_ai_config()
        self.preferences = load_ai_preferences()

    def generate_letter(
        self,
        prompt: str,
        context: LetterContext | None = None,
        tone: str | None = None,
        structured: bool | None = None,
    ) -> dict[str, str]:
        prompt = (prompt or "").strip()
        if not prompt:
            raise AIServiceError("Bitte zuerst einen Prompt eingeben.")

        if structured is None:
            structured = self.preferences.structured_output

        messages = build_generation_messages(
            prompt=prompt,
            context=context,
            tone=tone or self.preferences.default_tone,
            structured=structured,
        )
        content = self._post_chat_completion(messages)
        return self._extract_structured_result(content)

    def revise_letter(
        self,
        current_draft: dict[str, str],
        instruction: str,
        context: LetterContext | None = None,
    ) -> dict[str, str]:
        if not any((current_draft.get(field) or "").strip() for field in REQUIRED_FIELDS):
            raise AIServiceError("Es liegt noch kein Entwurf zum Ueberarbeiten vor.")

        instruction = (instruction or "").strip()
        if not instruction:
            raise AIServiceError("Die Ueberarbeitungsanweisung ist leer.")

        messages = build_revision_messages(current_draft, instruction, context)
        content = self._post_chat_completion(messages)
        return self._extract_structured_result(content)

    def _post_chat_completion(self, messages: list[dict[str, str]]) -> str:
        if self.config.provider.lower() != "nvidia":
            raise AIServiceError(f"Nicht unterstuetzter Provider: {self.config.provider}")
        if not self.config.api_key:
            raise AIServiceError("TEXT_AI_API_KEY fehlt. Bitte die .env pruefen.")

        payload = {
            "model": resolve_model(self.config, self.preferences),
            "messages": messages,
            "temperature": self.preferences.temperature,
            "max_tokens": self.preferences.max_tokens,
            "stream": False,
        }

        url = self.config.base_url.rstrip("/") + "/chat/completions"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore")
            raise AIServiceError(self._format_http_error(exc.code, error_body)) from exc
        except urllib.error.URLError as exc:
            raise AIServiceError(f"Netzwerkfehler beim KI-Aufruf: {exc.reason}") from exc

        try:
            data = json.loads(body)
            message = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIServiceError("Die NVIDIA-Antwort konnte nicht gelesen werden.") from exc

        return _content_to_text(message)

    def _extract_structured_result(self, raw_text: str) -> dict[str, str]:
        text = (raw_text or "").strip()
        if not text:
            raise AIServiceError("Die KI hat keinen Text zurueckgegeben.")

        for candidate in _json_candidates(text):
            parsed = _try_parse_json(candidate)
            if parsed is not None:
                normalized = _normalize_payload(parsed)
                if normalized:
                    return normalized

        fallback = _parse_labeled_text(text)
        if fallback:
            return fallback

        raise AIServiceError(
            "Die KI-Antwort konnte nicht in Betreff, Anrede, Brieftext und Grussformel aufgeteilt werden."
        )

    def _format_http_error(self, status_code: int, response_text: str) -> str:
        if status_code == 401:
            return "Der NVIDIA API-Key wurde nicht akzeptiert."
        if status_code == 403:
            return "Der NVIDIA-Zugriff wurde verweigert."
        if status_code == 429:
            return "Das NVIDIA API-Limit wurde erreicht. Bitte spaeter erneut versuchen."

        parsed = _try_parse_json(response_text)
        if isinstance(parsed, dict):
            error = parsed.get("error")
            if isinstance(error, dict):
                message = error.get("message")
                if message:
                    return f"NVIDIA API-Fehler ({status_code}): {message}"

        return f"NVIDIA API-Fehler ({status_code})."


def _content_to_text(message_content) -> str:
    if isinstance(message_content, str):
        return message_content

    if isinstance(message_content, list):
        parts = []
        for item in message_content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(part for part in parts if part)

    return str(message_content)


def _json_candidates(text: str) -> list[str]:
    candidates = [text]

    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    candidates.extend(fenced)

    brace_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if brace_match:
        candidates.append(brace_match.group(0))

    deduped = []
    seen = set()
    for candidate in candidates:
        normalized = candidate.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return deduped


def _try_parse_json(candidate: str):
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _normalize_payload(payload) -> dict[str, str] | None:
    if isinstance(payload, dict):
        if any(key in payload for key in REQUIRED_FIELDS):
            return {
                "betreff": str(payload.get("betreff", "") or "").strip(),
                "anrede": str(payload.get("anrede", "") or "").strip(),
                "brieftext": str(payload.get("brieftext", "") or "").strip(),
                "grussformel": str(payload.get("grussformel", "") or "").strip(),
            }

        for value in payload.values():
            nested = _normalize_payload(value)
            if nested is not None:
                return nested

    return None


def _parse_labeled_text(text: str) -> dict[str, str] | None:
    buffers = {field: [] for field in REQUIRED_FIELDS}
    current_field = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            target = current_field or "brieftext"
            if buffers[target] and buffers[target][-1] != "":
                buffers[target].append("")
            continue

        header_match = re.match(r"^([^:]{2,40}):\s*(.*)$", stripped)
        if header_match:
            label = _normalize_field_label(header_match.group(1))
            mapped_field = FIELD_ALIASES.get(label)
            if mapped_field:
                current_field = mapped_field
                remainder = header_match.group(2).strip()
                if remainder:
                    buffers[mapped_field].append(remainder)
                continue

        target = current_field or "brieftext"
        buffers[target].append(stripped)

    result = {
        field: "\n".join(parts).strip()
        for field, parts in buffers.items()
    }
    return result if any(result.values()) else None


def _normalize_field_label(label: str) -> str:
    normalized = label.strip().casefold().translate(FIELD_TRANSLATION)
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z]+", "", normalized)
