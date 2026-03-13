import os
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings


ENV_KEYS = {
    "provider": "TEXT_AI_PROVIDER",
    "api_key": "TEXT_AI_API_KEY",
    "base_url": "TEXT_AI_BASE_URL",
    "model": "TEXT_AI_MODEL",
}


@dataclass
class AIConfig:
    provider: str = "nvidia"
    api_key: str = ""
    base_url: str = "https://integrate.api.nvidia.com/v1"
    model: str = "minimaxai/minimax-m2.5"
    env_path: str = ""


@dataclass
class AIPreferences:
    model_override: str = ""
    default_tone: str = "neutral"
    include_customer_context: bool = True
    include_supplier_context: bool = True
    structured_output: bool = True
    temperature: float = 0.4
    max_tokens: int = 1200


def get_env_candidates() -> list[Path]:
    app_dir = Path(__file__).resolve().parents[1]
    project_root = app_dir.parent
    return [project_root / ".env", app_dir / ".env"]


def load_local_env() -> str:
    loaded_path = ""
    for path in get_env_candidates():
        if path.exists():
            _load_env_file(path)
            loaded_path = str(path)
    return loaded_path


def _load_env_file(path: Path):
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def load_ai_config() -> AIConfig:
    env_path = load_local_env()
    return AIConfig(
        provider=os.environ.get(ENV_KEYS["provider"], "nvidia").strip() or "nvidia",
        api_key=os.environ.get(ENV_KEYS["api_key"], "").strip(),
        base_url=os.environ.get(ENV_KEYS["base_url"], "https://integrate.api.nvidia.com/v1").strip(),
        model=os.environ.get(ENV_KEYS["model"], "minimaxai/minimax-m2.5").strip() or "minimaxai/minimax-m2.5",
        env_path=env_path,
    )


def load_ai_preferences() -> AIPreferences:
    settings = QSettings("Rechnungsprogramm", "Rechnungsprogramm")
    return AIPreferences(
        model_override=(settings.value("ai/model_override", "") or "").strip(),
        default_tone=(settings.value("ai/default_tone", "neutral") or "neutral").strip(),
        include_customer_context=_as_bool(settings.value("ai/include_customer_context", True)),
        include_supplier_context=_as_bool(settings.value("ai/include_supplier_context", True)),
        structured_output=_as_bool(settings.value("ai/structured_output", True)),
        temperature=float(settings.value("ai/temperature", 0.4) or 0.4),
        max_tokens=int(settings.value("ai/max_tokens", 1200) or 1200),
    )


def save_ai_preferences(preferences: AIPreferences):
    settings = QSettings("Rechnungsprogramm", "Rechnungsprogramm")
    settings.setValue("ai/model_override", preferences.model_override)
    settings.setValue("ai/default_tone", preferences.default_tone)
    settings.setValue("ai/include_customer_context", preferences.include_customer_context)
    settings.setValue("ai/include_supplier_context", preferences.include_supplier_context)
    settings.setValue("ai/structured_output", preferences.structured_output)
    settings.setValue("ai/temperature", preferences.temperature)
    settings.setValue("ai/max_tokens", preferences.max_tokens)


def resolve_model(config: AIConfig, preferences: AIPreferences) -> str:
    return preferences.model_override.strip() or config.model


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
