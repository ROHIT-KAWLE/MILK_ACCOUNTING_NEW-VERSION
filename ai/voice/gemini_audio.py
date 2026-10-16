"""Gemini 2.0 Flash Multimodal Audio Transcriber using lightweight REST API.

Requires zero heavy SDK dependencies (pure requests/urllib).
Transcribes continuous Marathi, Hindi, English, and Hinglish speech into structured transactions.
"""

import os
import base64
import requests
import streamlit as st
from ai.logging import log_ai_info, log_ai_error


def get_gemini_api_key() -> str | None:
    """Retrieves Gemini API Key from secrets, env vars, or session state."""
    # 1. Check Streamlit secrets
    try:
        if "gemini" in st.secrets and "api_key" in st.secrets["gemini"]:
            return st.secrets["gemini"]["api_key"].strip()
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"].strip()
    except Exception:
        pass

    # 2. Check environment variable
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key

    # 3. Check Streamlit session state
    if "user_gemini_api_key" in st.session_state and st.session_state["user_gemini_api_key"].strip():
        return st.session_state["user_gemini_api_key"].strip()

    return None


def is_gemini_audio_available() -> bool:
    """Checks whether Gemini Audio API is ready to use."""
    key = get_gemini_api_key()
    return bool(key and len(key) > 10)


def transcribe_route_audio(
    audio_bytes: bytes,
    retailer_names: list[str] = None,
    category_names: list[str] = None,
) -> dict:
    """Transcribes continuous route delivery audio into formatted multi-customer text.
    
    Returns:
      {'success': bool, 'transcript': str, 'error': str | None}
    """
    api_key = get_gemini_api_key()
    if not api_key:
        return {
            "success": False,
            "transcript": "",
            "error": "No Gemini API key found. Add GEMINI_API_KEY to secrets or enter in settings.",
        }

    if not audio_bytes or len(audio_bytes) < 100:
        return {
            "success": False,
            "transcript": "",
            "error": "Empty audio recording.",
        }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    # Context hints for 100% entity recognition accuracy
    ret_hint = ", ".join(retailer_names[:30]) if retailer_names else "Gupta Dairy, Laxmi Dairy, Sai Dairy"
    cat_hint = ", ".join(category_names) if category_names else "Buffalo, Cow, Standard, Special"

    prompt = f"""You are an expert audio transcription assistant for a milk delivery business in Maharashtra, India.
The speaker is dictating delivery entries and expenses in Marathi, Hindi, English, or Hinglish.

Known Customers in this Route: [{ret_hint}]
Known Milk Categories: [{cat_hint}]
Known Expenses: Fuel / डिझेल, Nasta / नाश्ता, Toll, Repair / पंचर.

Task:
Listen to the audio carefully and transcribe EVERY customer delivery, payment collection, and route expense into a single comma-separated text stream.
Keep the original numbers and names. Format each transaction clearly, separated by a comma or newline.
Examples:
- "गुलमोहर डेअरी २० म्हैस रोख ५०००, साई डेअरी १० गाय, डिझेल १५०० रोख, नाश्ता २०० रोख"
- "Gupta Dairy 20 buffalo cash 5000, Laxmi Dairy 15 cow, fuel 600 cash"

Return ONLY the transcribed transactions without markdown code blocks, explanations, or greeting.
"""

    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "audio/wav",
                            "data": b64_audio,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1000,
        },
    }

    try:
        log_ai_info(f"Calling Gemini 2.0 Flash Audio ({len(audio_bytes)} bytes)...")
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=25,
        )

        if resp.status_code != 200:
            err_msg = f"Gemini API error (HTTP {resp.status_code}): {resp.text[:200]}"
            log_ai_error(err_msg)
            return {"success": False, "transcript": "", "error": err_msg}

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return {"success": False, "transcript": "", "error": "No transcription returned."}

        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        cleaned_text = text.replace("```json", "").replace("```", "").strip()
        log_ai_info(f"Gemini Audio Transcribed: '{cleaned_text[:100]}...'")
        return {"success": True, "transcript": cleaned_text, "error": None}

    except Exception as e:
        log_ai_error(f"Gemini Audio request exception: {e}")
        return {"success": False, "transcript": "", "error": str(e)}
