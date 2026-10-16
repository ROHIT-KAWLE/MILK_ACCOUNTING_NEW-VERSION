"""Stage 2 Unit Tests: Voice Provider, Normalization & Browser Speech Component."""

import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ai.voice.speech_provider import BrowserWebSpeechProvider, FallbackSpeechProvider, get_speech_provider
from ai.voice.transcription import normalize_speech_transcript
from ai.parser.command_parser import parse_command
from ai.parser.intent_classifier import IntentType


def test_speech_providers():
    print("[1/6] Testing Speech Providers...")
    p_browser = BrowserWebSpeechProvider()
    assert p_browser.is_available() is True
    res = p_browser.transcribe({"transcript": "गुलमोहर डेअरी २० म्हैस", "lang": "mr-IN"})
    assert res["success"] is True
    assert res["transcript"] == "गुलमोहर डेअरी २० म्हैस"
    assert res["language"] == "mr-IN"

    # Test empty payload handling
    res_empty = p_browser.transcribe(None)
    assert res_empty["success"] is False

    # Test fallback provider
    p_fallback = get_speech_provider("manual")
    assert isinstance(p_fallback, FallbackSpeechProvider)
    res_fb = p_fallback.transcribe("20 buffalo gupta dairy")
    assert res_fb["success"] is True
    assert res_fb["transcript"] == "20 buffalo gupta dairy"
    print("  [PASS] Speech Providers: PASS")


def test_transcript_normalization():
    print("[2/6] Testing Transcript Normalization & Filler Removal...")
    raw = "गुलमोहर डेअरी, म्हणजे २० म्हैस, रोख ५००० ओके!"
    norm = normalize_speech_transcript(raw, language="mr-IN")
    assert norm.is_valid is True
    # 'म्हणजे', 'ओके', commas and exclamation marks should be cleaned
    assert "म्हणजे" not in norm.transcript
    assert "ओके" not in norm.transcript
    assert "," not in norm.transcript
    assert "!" not in norm.transcript
    assert "गुलमोहर डेअरी" in norm.transcript
    assert "२० म्हैस" in norm.transcript
    print("  [PASS] Transcript Normalization & Filler Removal: PASS")


def test_english_filler_cleaning():
    print("[3/6] Testing English Speech Fillers...")
    raw = "uh 20 buffalo um gupta dairy cash 5000 please"
    norm = normalize_speech_transcript(raw, language="en-IN")
    assert norm.is_valid is True
    assert "uh" not in norm.transcript.lower().split()
    assert "um" not in norm.transcript.lower().split()
    assert "20 buffalo" in norm.transcript
    print("  [PASS] English Speech Fillers: PASS")


def test_frontend_files_integrity():
    print("[4/6] Testing Frontend Speech Widget Integrity...")
    frontend_dir = os.path.join(REPO_ROOT, "ai", "voice", "frontend")
    index_file = os.path.join(frontend_dir, "index.html")
    assert os.path.isfile(index_file), "index.html must exist in ai/voice/frontend"

    with open(index_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Must contain Web Speech API and Streamlit integration
    assert "SpeechRecognition" in html_content
    assert "mr-IN" in html_content
    assert "streamlit:componentReady" in html_content
    assert "streamlit:setComponentValue" in html_content
    assert "streamlit:setFrameHeight" in html_content
    assert "mic-btn" in html_content
    print("  [PASS] Frontend Speech Widget Integrity: PASS")


def test_e2e_spoken_marathi_pipeline():
    print("[5/6] Testing Spoken Marathi Voice to Command Pipeline...")
    spoken_payload = {
        "transcript": "अरे गुलमोहर डेअरी वीस म्हैस रोख पाच हजार",
        "lang": "mr-IN"
    }
    provider = BrowserWebSpeechProvider()
    trans_res = provider.transcribe(spoken_payload)
    assert trans_res["success"] is True

    normalized = normalize_speech_transcript(trans_res["transcript"], language=trans_res["language"])
    assert normalized.is_valid is True

    import pandas as pd
    retailers_df = pd.DataFrame([
        {"id": 101, "name": "Gulmohar Dairy", "marathi_name": "गुलमोहर डेअरी", "route_code": "R1"},
        {"id": 102, "name": "Laxmi Dairy", "marathi_name": "लक्ष्मी डेअरी", "route_code": "R1"},
    ])
    categories_df = pd.DataFrame([
        {"id": 1, "name": "Buffalo", "marathi_name": "म्हैस", "display_order": 1},
        {"id": 2, "name": "Cow", "marathi_name": "गाय", "display_order": 2},
    ])

    draft = parse_command(normalized.transcript, retailers_df, categories_df, mode_lock="retailer_delivery")
    assert draft.intent == IntentType.RETAILER_SALE
    assert draft.is_valid_draft is True
    assert draft.command is not None
    assert draft.command.retailer_id == 101
    assert len(draft.command.items) == 1
    assert draft.command.items[0].qty == 20.0
    assert draft.command.items[0].category_id == 1
    # Rate and amount MUST remain None for ERP master rate lookup
    assert draft.command.items[0].rate is None
    assert draft.command.cash_payment == 5000.0
    print("  [PASS] Spoken Marathi Voice to Command Pipeline: PASS")


def test_e2e_route_expense_pipeline():
    print("[6/6] Testing Spoken Route Expense Pipeline...")
    import pandas as pd
    raw_spoken = "डिझेल पंधराशे रोख"
    norm = normalize_speech_transcript(raw_spoken, language="mr-IN")
    draft = parse_command(norm.transcript, pd.DataFrame(), pd.DataFrame(), mode_lock="route_expense")
    assert draft.intent == IntentType.ROUTE_EXPENSE
    assert draft.is_valid_draft is True
    assert draft.command is not None
    assert draft.command.category == "Fuel"
    assert draft.command.amount == 1500.0
    print("  [PASS] Spoken Route Expense Pipeline: PASS")


if __name__ == "__main__":
    print("\n=======================================================")
    print("RUNNING STAGE 2 VOICE LAYER UNIT TESTS")
    print("=======================================================")
    test_speech_providers()
    test_transcript_normalization()
    test_english_filler_cleaning()
    test_frontend_files_integrity()
    test_e2e_spoken_marathi_pipeline()
    test_e2e_route_expense_pipeline()
    print("=======================================================")
    print("ALL 6 STAGE 2 TESTS PASSED WITH 100% SUCCESS!")
    print("=======================================================\n")
