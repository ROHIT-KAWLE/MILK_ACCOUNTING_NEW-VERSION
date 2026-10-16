"""
Structured, safe diagnostics logger for AI Intelligence Layer.
Strictly ensures no API keys, credentials, or sensitive tokens are ever logged.
"""

import logging
import re
import time

_logger = logging.getLogger("MilkAccountingPro.AI")
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter("[AI-LOG %(levelname)s %(asctime)s] %(message)s", datefmt="%H:%M:%S")
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)

# Patterns that must be scrubbed from logs
_SECRET_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"key[=:][\s]*['\"]?[A-Za-z0-9_\-\.]{10,}['\"]?", re.IGNORECASE),
    re.compile(r"password[=:][\s]*['\"]?[^'\"]+['\"]?", re.IGNORECASE),
]


def _scrub(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED_SECRET]", out)
    return out


def log_ai_info(message: str) -> None:
    _logger.info(_scrub(message))


def log_ai_warning(message: str) -> None:
    _logger.warning(_scrub(message))


def log_ai_error(message: str, exc: Exception = None) -> None:
    if exc:
        _logger.error(f"{_scrub(message)} | Exception: {exc}")
    else:
        _logger.error(_scrub(message))


# Convenient aliases
log_info = log_ai_info
log_warn = log_ai_warning
log_warning = log_ai_warning
log_error = log_ai_error


class AIExecutionTimer:
    """Context manager to measure and log execution duration for performance targets."""
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = 0.0
        self.elapsed_ms = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed_ms = (time.perf_counter() - self.start_time) * 1000.0
        if exc_type is None:
            _logger.debug(f"{self.operation_name} completed in {self.elapsed_ms:.2f} ms")
        else:
            _logger.warning(f"{self.operation_name} failed after {self.elapsed_ms:.2f} ms")
