"""Abstract Speech Provider interface and standard implementations."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from ai.logging import log_ai_info


class SpeechProvider(ABC):
    """Abstract interface for speech-to-text providers."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available in current environment."""
        pass

    @abstractmethod
    def transcribe(self, payload: Any, language: str = "mr-IN") -> Dict[str, Any]:
        """Transcribe speech payload into normalized text."""
        pass


class BrowserWebSpeechProvider(SpeechProvider):
    """Provider for browser-native Web Speech API (HTML5 SpeechRecognition).
    
    Zero latency, executes directly on client device (Android Chrome, Edge, desktop Chrome),
    requires no external heavy Python dependencies or cloud API keys.
    """

    def __init__(self):
        super().__init__("browser_web_speech")

    def is_available(self) -> bool:
        # Browser Web Speech API is executed on the frontend client
        return True

    def transcribe(self, payload: Any, language: str = "mr-IN") -> Dict[str, Any]:
        """Normalize raw payload received from browser Web Speech component."""
        if not payload:
            return {"success": False, "transcript": "", "error": "Empty speech payload"}

        if isinstance(payload, dict):
            raw_text = payload.get("transcript", "") or payload.get("text", "")
            confidence = float(payload.get("confidence", 0.95))
            detected_lang = payload.get("lang", language)
        elif isinstance(payload, str):
            raw_text = payload
            confidence = 0.90
            detected_lang = language
        else:
            raw_text = str(payload)
            confidence = 0.80
            detected_lang = language

        raw_text = raw_text.strip()
        if not raw_text:
            return {"success": False, "transcript": "", "error": "No speech recognized"}

        log_ai_info(f"Browser speech received ({detected_lang}): len={len(raw_text)}")
        return {
            "success": True,
            "transcript": raw_text,
            "confidence": confidence,
            "language": detected_lang,
            "provider": self.name,
        }


class FallbackSpeechProvider(SpeechProvider):
    """Graceful fallback provider for manual typing or unsupported clients."""

    def __init__(self):
        super().__init__("manual_text_fallback")

    def is_available(self) -> bool:
        return True

    def transcribe(self, payload: Any, language: str = "mr-IN") -> Dict[str, Any]:
        text = str(payload).strip() if payload else ""
        if not text:
            return {"success": False, "transcript": "", "error": "No text provided"}
        return {
            "success": True,
            "transcript": text,
            "confidence": 1.0,
            "language": language,
            "provider": self.name,
        }


def get_speech_provider(provider_type: Optional[str] = None) -> SpeechProvider:
    """Factory to retrieve appropriate speech provider."""
    if provider_type == "manual":
        return FallbackSpeechProvider()
    return BrowserWebSpeechProvider()
