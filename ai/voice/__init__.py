"""Voice acquisition, transcription, and tablet speech interface module."""

from ai.voice.speech_provider import SpeechProvider, FallbackSpeechProvider
from ai.voice.transcription import normalize_speech_transcript, SpeechTranscriptResult

__all__ = [
    "SpeechProvider",
    "FallbackSpeechProvider",
    "normalize_speech_transcript",
    "SpeechTranscriptResult",
]
