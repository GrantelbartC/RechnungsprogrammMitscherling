from PySide6.QtCore import QObject, Signal, Slot

from services.ai_prompt_builder import LetterContext
from services.ai_text_service import AITextService


class GenerateLetterWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        prompt: str,
        context: LetterContext | None = None,
        tone: str | None = None,
        structured: bool = True,
        revision_instruction: str | None = None,
        current_draft: dict[str, str] | None = None,
    ):
        super().__init__()
        self.prompt = prompt
        self.context = context
        self.tone = tone
        self.structured = structured
        self.revision_instruction = revision_instruction
        self.current_draft = current_draft or {}

    @Slot()
    def run(self):
        try:
            service = AITextService()
            if self.revision_instruction and any(
                (self.current_draft.get(field) or "").strip()
                for field in ("betreff", "anrede", "brieftext", "grussformel")
            ):
                result = service.revise_letter(
                    current_draft=self.current_draft,
                    instruction=self.revision_instruction,
                    context=self.context,
                )
            else:
                effective_prompt = self.prompt
                if self.revision_instruction:
                    effective_prompt = f"{self.prompt.strip()}\n\nZusatzanweisung: {self.revision_instruction}"
                result = service.generate_letter(
                    prompt=effective_prompt,
                    context=self.context,
                    tone=self.tone,
                    structured=self.structured,
                )
        except Exception as exc:  # noqa: BLE001 - UI worker should surface all errors.
            self.failed.emit(str(exc))
            return

        self.finished.emit(result)
