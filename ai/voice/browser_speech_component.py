"""Streamlit Browser Speech Component wrapper."""

import os
from typing import Optional, Dict, Any
import streamlit.components.v1 as components
from ai.logging import log_ai_info, log_ai_error

_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

try:
    _component_func = components.declare_component(
        "browser_speech_recorder",
        path=_FRONTEND_DIR
    )
except Exception as e:
    log_ai_error(f"Failed to declare browser speech component: {e}")
    _component_func = None


def render_browser_speech_widget(
    key: str = "browser_speech_widget",
    default_mode: str = "retailer_delivery",
    default_lang: str = "mr-IN"
) -> Optional[Dict[str, Any]]:
    """Renders touch-friendly browser Web Speech microphone widget.
    
    Returns a dict with {'transcript': str, 'language': str, 'mode': str} if speech was captured,
    or None if waiting.
    """
    if _component_func is None:
        return None

    try:
        val = _component_func(
            default_mode=default_mode,
            default_lang=default_lang,
            key=key,
            default=None
        )
        if val and isinstance(val, dict) and val.get("transcript"):
            log_ai_info(f"Captured speech event: {val.get('transcript')} ({val.get('mode')})")
            return val
        return None
    except Exception as e:
        log_ai_error(f"Error rendering browser speech widget: {e}")
        return None
