"""
Phonetic Normalizer & Devanagari Transliteration Engine.
Provides deterministic, vowel-invariant phonetic representations to bridge
Marathi/Devanagari spoken outputs with English database master records.
"""

import re
import difflib

DEVANAGARI_TRANSLIT_MAP: dict[str, str] = {
    # Vowels
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    # Consonants
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h", "ळ": "l",
    "क्ष": "x", "ज्ञ": "dny",
    # Matras (Vowel signs)
    "ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ं": "n",
    "्": "", "ॅ": "a", "ॉ": "o",
    # Common Dairy Word Abbreviations
    "डेअरी": "dairy", "डेरी": "dairy", "सेंटर": "center",
}


def devanagari_to_latin(text: str) -> str:
    """Converts Devanagari script characters into phonetic Latin representation."""
    if not isinstance(text, str) or not text:
        return ""
    out = []
    i = 0
    while i < len(text):
        # Check 3-char, 2-char tokens first
        if i + 5 <= len(text) and text[i:i + 5] in DEVANAGARI_TRANSLIT_MAP:
            out.append(DEVANAGARI_TRANSLIT_MAP[text[i:i + 5]])
            i += 5
            continue
        if i + 4 <= len(text) and text[i:i + 4] in DEVANAGARI_TRANSLIT_MAP:
            out.append(DEVANAGARI_TRANSLIT_MAP[text[i:i + 4]])
            i += 4
            continue
        ch = text[i]
        out.append(DEVANAGARI_TRANSLIT_MAP.get(ch, ch))
        i += 1
    return "".join(out)


def phonetic_norm(s: str) -> str:
    """
    Produces a normalized vowel-invariant phonetic string.
    Bridges English vs Devanagari spelling variances (e.g. Laxmi vs Lakshmi, Dairy vs Deari).
    """
    if not isinstance(s, str) or not s:
        return ""

    # Step 1: Transliterate Devanagari if present
    lat = devanagari_to_latin(s.lower().strip())

    # Step 2: Normalize known homophones and common dairy terms
    lat = (
        lat.replace("ksh", "x")
        .replace("x", "ks")
        .replace("sh", "s")
        .replace("ph", "f")
        .replace("dairy", "dry")
        .replace("deari", "dry")
        .replace("dayri", "dry")
        .replace("center", "cntr")
        .replace("centre", "cntr")
        .replace("milk", "mlk")
        .replace("supplier", "splr")
    )

    # Step 3: Strip vowels (a, e, i, o, u) to eliminate implicit vowel mismatch
    vowels_removed = re.sub(r"[aeiou]", "", lat)

    # Step 4: Remove punctuation, whitespace, and special characters
    clean = re.sub(r"[^a-z0-9]", "", vowels_removed)
    return clean


def string_similarity(s1: str, s2: str) -> float:
    """Calculates SequenceMatcher ratio between two normalized strings."""
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    return difflib.SequenceMatcher(None, s1, s2).ratio()
