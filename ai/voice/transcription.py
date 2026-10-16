"""Speech transcript normalization and preprocessing."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class SpeechTranscriptResult:
    """Standardized representation of a transcribed speech phrase."""
    transcript: str
    raw_text: str
    language: str
    confidence: float
    is_valid: bool
    error: Optional[str] = None


# Speech fillers commonly heard in dairy operational dictation
FILLER_WORDS = [
    r"(?:(?<=\s)|^)(?:um|uh|ah|oh|okay|ok)(?=\s|$)",
    r"(?:(?<=\s)|^)(?:म्हणजे|अरे|ना|ओके|सुनो|अहो|बघा)(?=\s|$)",
]


def normalize_speech_transcript(
    raw_text: str,
    language: str = "mr-IN",
    confidence: float = 0.90
) -> SpeechTranscriptResult:
    """Cleans and standardizes raw speech recognition output for parsing."""
    if not raw_text or not isinstance(raw_text, str):
        return SpeechTranscriptResult(
            transcript="",
            raw_text=str(raw_text or ""),
            language=language,
            confidence=0.0,
            is_valid=False,
            error="Empty or invalid speech input"
        )

    text = raw_text.strip()

    # Remove trailing punctuation often inserted by speech engines (period, comma, question mark)
    text = re.sub(r"[\.,;:!\?]", " ", text)

    # Clean redundant speech fillers at start/end
    for filler in FILLER_WORDS:
        text = re.sub(filler, " ", text, flags=re.IGNORECASE)

    # Normalize multiple whitespaces
    text = re.sub(r"\s+", " ", text).strip()

    is_valid = len(text) > 0

    return SpeechTranscriptResult(
        transcript=text,
        raw_text=raw_text,
        language=language,
        confidence=confidence if is_valid else 0.0,
        is_valid=is_valid,
        error=None if is_valid else "Normalized text is empty"
    )
