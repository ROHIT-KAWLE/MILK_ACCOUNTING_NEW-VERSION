"""
Deterministic Multilingual Number & Quantity Parser for Marathi, Hindi, English, and Romanized text.
Supports digits, word numbers 0-100, common fractions, hundreds, thousands, and lakhs.
Zero external cloud or LLM dependencies.
"""

import re
from typing import Sequence

# -------------------------------------------------------------
# 1. ATOMIC NUMBER VOCABULARY MAPPINGS
# -------------------------------------------------------------

NUMERIC_WORDS: dict[str, float] = {
    # Digits 0-9
    "0": 0.0, "1": 1.0, "2": 2.0, "3": 3.0, "4": 4.0,
    "5": 5.0, "6": 6.0, "7": 7.0, "8": 8.0, "9": 9.0,
    "०": 0.0, "१": 1.0, "२": 2.0, "३": 3.0, "४": 4.0,
    "५": 5.0, "६": 6.0, "७": 7.0, "८": 8.0, "९": 9.0,

    # English word numbers (0 - 20)
    "zero": 0.0, "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0,
    "six": 6.0, "seven": 7.0, "eight": 8.0, "nine": 9.0, "ten": 10.0,
    "eleven": 11.0, "twelve": 12.0, "thirteen": 13.0, "fourteen": 14.0, "fifteen": 15.0,
    "sixteen": 16.0, "seventeen": 17.0, "eighteen": 18.0, "nineteen": 19.0, "twenty": 20.0,
    # English tens
    "thirty": 30.0, "forty": 40.0, "fifty": 50.0, "sixty": 60.0, "seventy": 70.0,
    "eighty": 80.0, "ninety": 90.0, "hundred": 100.0, "thousand": 1000.0, "lakh": 100000.0, "lac": 100000.0,

    # Marathi Devanagari (0 - 30)
    "शून्य": 0.0, "एक": 1.0, "दोन": 2.0, "तीन": 3.0, "चार": 4.0, "पाच": 5.0,
    "सहा": 6.0, "सात": 7.0, "आठ": 8.0, "नऊ": 9.0, "दहा": 10.0,
    "अकरा": 11.0, "बारा": 12.0, "तेरा": 13.0, "चौदा": 14.0, "पंधरा": 15.0,
    "सोळा": 16.0, "सतरा": 17.0, "अठरा": 18.0, "एकोणीस": 19.0, "वीस": 20.0,
    "एकवीस": 21.0, "बावीस": 22.0, "तेवीस": 23.0, "चोवीस": 24.0, "पंचवीस": 25.0,
    "सव्वीस": 26.0, "सत्तावीस": 27.0, "अठ्ठावीस": 28.0, "एकोणतीस": 29.0, "तीस": 30.0,
    # Marathi Devanagari (31 - 100 milestones)
    "एकतीस": 31.0, "बत्तीस": 32.0, "पस्तीस": 35.0, "चाळीस": 40.0, "पंचेचाळीस": 45.0,
    "पन्नास": 50.0, "पंचावन्न": 55.0, "साठ": 60.0, "पासष्ट": 65.0, "सत्तर": 70.0,
    "पंच्याहत्तर": 75.0, "ऐंशी": 80.0, "पंच्याऐंशी": 85.0, "नव्वद": 90.0, "पंच्याण्णव": 95.0,
    "शंभर": 100.0, "दोनशे": 200.0, "तीनशे": 300.0, "चारशे": 400.0, "पाचशे": 500.0,
    "सहाशे": 600.0, "सातशे": 700.0, "आठशे": 800.0, "नऊशे": 900.0,
    "अकराशे": 1100.0, "बाराशे": 1200.0, "तेराशे": 1300.0, "चौदाशे": 1400.0,
    "पंधराशे": 1500.0, "सोळाशे": 1600.0, "सतराशे": 1700.0, "अठराशे": 1800.0, "एकोणीसशे": 1900.0,
    "हजार": 1000.0, "दोन हजार": 2000.0, "पाच हजार": 5000.0, "दहा हजार": 10000.0, "लाख": 100000.0,

    # Marathi Latin / Transliteration (0 - 100)
    "shunya": 0.0, "ek": 1.0, "don": 2.0, "teen": 3.0, "char": 4.0, "pach": 5.0, "paach": 5.0,
    "saha": 6.0, "sat": 7.0, "saat": 7.0, "aath": 8.0, "ath": 8.0, "nau": 9.0, "daha": 10.0,
    "akra": 11.0, "bara": 12.0, "baara": 12.0, "tera": 13.0, "chauda": 14.0, "pandhra": 15.0,
    "sola": 16.0, "satra": 17.0, "athra": 18.0, "ekonis": 19.0, "vis": 20.0, "vees": 20.0,
    "ekvis": 21.0, "bavis": 22.0, "tevis": 23.0, "chovis": 24.0, "pachvis": 25.0,
    "tis": 30.0, "tees": 30.0, "pastis": 35.0, "chalis": 40.0, "chaalis": 40.0,
    "panchechalis": 45.0, "pannas": 50.0, "panchavanna": 55.0, "sath": 60.0, "saath": 60.0,
    "pasasht": 65.0, "sattar": 70.0, "panchyahattar": 75.0, "ayshi": 80.0, "aishi": 80.0,
    "navvad": 90.0, "panchyannav": 95.0, "shambhar": 100.0, "she": 100.0,
    "donshe": 200.0, "teenshe": 300.0, "charshe": 400.0, "pachshe": 500.0,
    "hazaar": 1000.0, "hazar": 1000.0,

    # Hindi numbers (ek, do, teen, char, paanch...)
    "do": 2.0, "paanch": 5.0, "panch": 5.0, "chhah": 6.0, "das": 10.0,
    "gyarah": 11.0, "barah": 12.0, "terah": 13.0, "chaudah": 14.0, "pandrah": 15.0,
    "solah": 16.0, "satrah": 17.0, "atharah": 18.0, "unnis": 19.0, "bees": 20.0,
    "pachees": 25.0, "pachis": 25.0, "pachaas": 50.0, "sau": 100.0, "ek sau": 100.0,
    "hajaar": 1000.0, "laakh": 100000.0,
}

# Standalone Fractions
FRACTION_WORDS: dict[str, float] = {
    "पाव": 0.25, "pav": 0.25, "paav": 0.25, "quarter": 0.25,
    "अर्धा": 0.50, "ardha": 0.50, "aadha": 0.50, "half": 0.50,
    "पाऊण": 0.75, "paun": 0.75, "paaun": 0.75,
    "दीड": 1.50, "deed": 1.50, "did": 1.50, "dhed": 1.50,
    "दीडशे": 150.0, "didshe": 150.0,
    "अडीच": 2.50, "adeech": 2.50, "adich": 2.50,
    "अडीचशे": 250.0, "adichshe": 250.0,
}

# Prefix Modifiers (e.g. साडे तीन = 3.5, सव्वा पाच = 5.25, पावणे चार = 3.75)
PREFIX_MODIFIERS: dict[str, float] = {
    "सव्वा": 0.25, "savva": 0.25, "savvaa": 0.25,
    "साडे": 0.50, "sade": 0.50, "saade": 0.50,
    "पावणे": -0.25, "pavne": -0.25, "paavne": -0.25,
}

MULTIPLIERS: dict[str, float] = {
    "शे": 100.0, "she": 100.0, "शंभर": 100.0, "shambhar": 100.0, "hundred": 100.0, "sau": 100.0, "सौ": 100.0,
    "हजार": 1000.0, "hazaar": 1000.0, "hazar": 1000.0, "thousand": 1000.0, "k": 1000.0,
    "लाख": 100000.0, "lakh": 100000.0, "lac": 100000.0, "laakh": 100000.0,
}

UNIT_KEYWORDS: set[str] = {
    "l", "ltr", "litre", "liter", "litres", "liters",
    "लिटर", "लीटर", "लीटर",
}


def parse_single_token(tok: str) -> float | None:
    """Parses a single word token into a number if recognized."""
    if not tok:
        return None
    tok_clean = tok.strip().lower()

    # Direct digit check (e.g., '20', '20.5', '5000')
    try:
        val = float(tok_clean)
        return val
    except ValueError:
        pass

    # Direct dictionary check
    if tok_clean in NUMERIC_WORDS:
        return NUMERIC_WORDS[tok_clean]

    # Direct fraction check
    if tok_clean in FRACTION_WORDS:
        return FRACTION_WORDS[tok_clean]

    return None


def parse_number_words(tokens: Sequence[str] | str) -> float | None:
    """
    Parses a sequence of words into a single computed number.
    Handles compound expressions:
      - 'five thousand' / 'pach hazaar' / 'पाच हजार' -> 5000.0
      - 'two hundred' / 'don she' / 'दोनशे' -> 200.0
      - 'saade teen' / 'साडे तीन' -> 3.5
      - 'savva pach' / 'सव्वा पाच' -> 5.25
      - 'pavne char' / 'पावणे चार' -> 3.75
      - 'saade teen hazaar' -> 3500.0
    """
    if isinstance(tokens, str):
        # Normalize punctuation
        clean = re.sub(r"[,;।\.]", " ", tokens)
        tok_list = clean.split()
    else:
        tok_list = list(tokens)

    if not tok_list:
        return None

    # Case 1: Single token
    if len(tok_list) == 1:
        return parse_single_token(tok_list[0])

    # Case 2: Multi-token sequence
    total = 0.0
    current_num = 0.0
    i = 0
    while i < len(tok_list):
        t = tok_list[i].lower().strip()

        # Check prefix modifiers (saade, savva, pavne)
        if t in PREFIX_MODIFIERS:
            mod = PREFIX_MODIFIERS[t]
            if i + 1 < len(tok_list):
                base_num = parse_single_token(tok_list[i + 1])
                if base_num is not None:
                    computed = base_num + mod
                    # Check if next token is a multiplier (e.g., hazaar)
                    if i + 2 < len(tok_list) and tok_list[i + 2] in MULTIPLIERS:
                        mult = MULTIPLIERS[tok_list[i + 2]]
                        current_num += computed * mult
                        i += 3
                        continue
                    else:
                        current_num += computed
                        i += 2
                        continue

        # Check standalone multiplier (e.g., 'don' + 'hazaar')
        if t in MULTIPLIERS:
            mult = MULTIPLIERS[t]
            if current_num > 0:
                current_num *= mult
            else:
                current_num = mult
            total += current_num
            current_num = 0.0
            i += 1
            continue

        # Standard token parsing
        val = parse_single_token(t)
        if val is not None:
            # Check if immediately followed by multiplier
            if i + 1 < len(tok_list) and tok_list[i + 1] in MULTIPLIERS:
                mult = MULTIPLIERS[tok_list[i + 1]]
                total += val * mult
                i += 2
                continue
            else:
                current_num += val
                i += 1
                continue

        i += 1

    final_val = total + current_num
    return final_val if final_val > 0 else None


def extract_quantities_with_units(text: str) -> list[dict]:
    """
    Extracts all numerical quantities and attached units (e.g. '20 L', '50 लिटर', '5000 rs').
    Returns list of dicts: [{'val': float, 'unit': str | None, 'start_pos': int, 'end_pos': int}]
    """
    results = []
    # Match patterns like: "20.5 l", "5000", "50 litre", "100लिटर"
    pattern = re.compile(r"(\d+(?:\.\d+)?)\s*([a-zA-Z\u0900-\u097F]*)")
    for m in pattern.finditer(text):
        val_str = m.group(1)
        raw_unit = m.group(2).lower().strip()
        try:
            val = float(val_str)
            unit = None
            if raw_unit in UNIT_KEYWORDS or raw_unit.startswith("lit") or raw_unit.startswith("लिटर"):
                unit = "L"
            elif raw_unit in ("rs", "rupee", "rupees", "रुपये", "रु"):
                unit = "INR"
            results.append({"val": val, "unit": unit, "raw_unit": raw_unit})
        except ValueError:
            continue
    return results
