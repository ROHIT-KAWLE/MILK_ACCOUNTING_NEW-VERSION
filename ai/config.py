"""
Configuration settings for the Milk Accounting Pro Intelligence Layer.
Strictly separates offline deterministic engines from optional external providers.
"""

from dataclasses import dataclass
import os


@dataclass
class AIConfig:
    # Master switch for intelligence assistant
    AI_ENABLED: bool = True

    # External cloud AI provider toggle (STRICTLY OPTIONAL & DISABLED BY DEFAULT)
    # The ERP must operate at 100% functionality even when this is False.
    EXTERNAL_AI_ENABLED: bool = False
    EXTERNAL_AI_PROVIDER: str = "none"  # "none", "gemini", "huggingface"

    # Entity matching thresholds (deterministic fuzzy matching)
    RETAILER_MATCH_THRESHOLD: float = 0.68
    CATEGORY_MATCH_THRESHOLD: float = 0.65
    DISTRIBUTOR_MATCH_THRESHOLD: float = 0.68

    # Ambiguity detection threshold:
    # If top 2 candidate entities have score difference <= this delta,
    # mark as AMBIGUOUS and ask user to choose. Never guess silently.
    AMBIGUITY_DELTA_THRESHOLD: float = 0.08

    # Default speech recognition locale
    DEFAULT_SPEECH_LOCALE: str = "mr-IN"
    SUPPORTED_LOCALES: tuple = ("mr-IN", "hi-IN", "en-IN")

    # Volume spike statistical thresholds
    VOLUME_SPIKE_ZSCORE: float = 2.8
    VOLUME_SPIKE_MULTIPLIER: float = 2.5
    MIN_DAYS_FOR_HABIT_LEARNING: int = 5


_GLOBAL_CONFIG = None


def get_ai_config() -> AIConfig:
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = AIConfig(
            AI_ENABLED=os.getenv("AI_ENABLED", "true").lower() in ("true", "1", "yes"),
            EXTERNAL_AI_ENABLED=os.getenv("EXTERNAL_AI_ENABLED", "false").lower() in ("true", "1", "yes"),
            EXTERNAL_AI_PROVIDER=os.getenv("EXTERNAL_AI_PROVIDER", "none").lower(),
        )
    return _GLOBAL_CONFIG
