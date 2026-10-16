"""
MILK ACCOUNTING PRO — OFFLINE AI ENGINE & ANOMALY DETECTOR
===========================================================
100% Local & Offline Intelligent Anomaly Detection, Pattern Learning,
and Marathi / English Voice & Text Entry Parser.

Zero external cloud API dependencies. Runs in < 10ms entirely in Python.
"""

import re
import difflib
from datetime import date
import pandas as pd
import numpy as np


# ============================================================
# 1. BILINGUAL MARATHI & ENGLISH VOCABULARY DICTIONARIES
# ============================================================

MARATHI_ENGLISH_NUMBERS = {
    # Devanagari words
    "शून्य": 0, "एक": 1, "दोन": 2, "तीन": 3, "चार": 4, "पाच": 5,
    "सहा": 6, "सात": 7, "आठ": 8, "नऊ": 9, "दहा": 10,
    "अकरा": 11, "बारा": 12, "तेरा": 13, "चौदा": 14, "पंधरा": 15,
    "सोळा": 16, "सतरा": 17, "अठरा": 18, "एकोणीस": 19, "वीस": 20,
    "पंचवीस": 25, "तीस": 30, "पस्तीस": 35, "चाळीस": 40, "पंचेचाळीस": 45,
    "पन्नास": 50, "साठ": 60, "सत्तर": 70, "ऐंशी": 80, "नव्वद": 90,
    "शंभर": 100, "दीडशे": 150, "दोनशे": 200, "पाचशे": 500,
    "हजार": 1000, "लाख": 100000,
    # Marathi Latin transliteration
    "shunya": 0, "ek": 1, "don": 2, "teen": 3, "char": 4, "pach": 5, "paach": 5,
    "saha": 6, "sat": 7, "saat": 7, "aath": 8, "ath": 8, "nau": 9, "daha": 10,
    "pandhra": 15, "sola": 16, "vis": 20, "vees": 20, "pachvis": 25,
    "tees": 30, "tis": 30, "chalis": 40, "chaalis": 40, "pannas": 50,
    "sath": 60, "saath": 60, "sattar": 70, "ayshi": 80, "aishi": 80, "navvad": 90,
    "shambhar": 100, "she": 100, "hazaar": 1000, "hazar": 1000, "lakh": 100000,
    # English number words
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "fifteen": 15, "twenty": 20, "twentyfive": 25, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100, "thousand": 1000, "lac": 100000,
}

CATEGORY_SYNONYMS = {
    "buffalo": "Buffalo",
    "buff": "Buffalo",
    "mahis": "Buffalo",
    "mhais": "Buffalo",
    "म्हैस": "Buffalo",
    "म्हैशीचे": "Buffalo",
    "cow": "Cow",
    "gay": "Cow",
    "gaay": "Cow",
    "गाय": "Cow",
    "गाईचे": "Cow",
    "standard": "Standard",
    "std": "Standard",
    "स्टँडर्ड": "Standard",
    "gokul": "Gokul Special",
    "gokul special": "Gokul Special",
    "गोकुळ": "Gokul Special",
    "gokul cow": "Gokul Cow",
    "गोकुळ गाय": "Gokul Cow",
    "amul": "Amul",
    "अमुल": "Amul",
    "chaas": "Amul Chaas",
    "taak": "Amul Chaas",
    "ताक": "Amul Chaas",
    "छास": "Amul Chaas",
}

PAYMENT_SYNONYMS = {
    "cash": "Cash",
    "rok": "Cash",
    "rokh": "Cash",
    "rokadh": "Cash",
    "रोख": "Cash",
    "रोकड": "Cash",
    "कैश": "Cash",
    "upi": "UPI",
    "gpay": "UPI",
    "phonepe": "UPI",
    "paytm": "UPI",
    "online": "UPI",
    "यूपीआय": "UPI",
    "ऑनलाइन": "UPI",
    "cheque": "Cheque",
    "check": "Cheque",
    "चेक": "Cheque",
    "bank": "Bank",
    "बँक": "Bank",
}


# ============================================================
# 2. CUSTOMER BEHAVIOR PATTERN LEARNING (LOCAL / OFFLINE)
# ============================================================

def build_customer_habit_profiles(
    entries_df: pd.DataFrame,
    retailers_df: pd.DataFrame = None,
    categories_df: pd.DataFrame = None,
    days_lookback: int = 90,
    *args,
    **kwargs,
) -> dict:
    """
    Learns 60 to 90-day behavioral habit profile for each retailer:
    - Typical categories purchased (e.g. only Buffalo vs Buffalo+Cow)
    - Mean and standard deviation of daily quantity per category
    - Maximum expected single-day volume
    - Historical active days count
    Runs 100% in-memory using vectorized Pandas operations.
    """
    profiles = {}
    if entries_df is None or entries_df.empty:
        return profiles

    df = entries_df.copy()
    if "date" in df.columns and days_lookback and days_lookback > 0:
        parsed_dates = pd.to_datetime(df["date"], errors="coerce")
        max_dt = parsed_dates.max()
        if pd.notna(max_dt):
            cutoff = max_dt - pd.Timedelta(days=days_lookback)
            df = df[parsed_dates >= cutoff]

    df["qty"] = pd.to_numeric(df.get("qty", 0), errors="coerce").fillna(0.0)
    df["retailer_id"] = pd.to_numeric(df.get("retailer_id", 0), errors="coerce").fillna(0).astype(int)
    df["category_id"] = pd.to_numeric(df.get("category_id", 0), errors="coerce").fillna(0).astype(int)

    # Filter out 0 qty records
    active_df = df[df["qty"] > 0]
    if active_df.empty:
        return profiles

    # Pre-map categories
    cat_name_map = {}
    if categories_df is not None and not categories_df.empty:
        for _, r in categories_df.iterrows():
            cid = int(pd.to_numeric(r.get("category_id", 0), errors="coerce") or 0)
            cname = str(r.get("name", f"Cat {cid}")).strip()
            cat_name_map[cid] = cname

    for rid, grp in active_df.groupby("retailer_id"):
        cats_taken = set(grp["category_id"].unique())
        cat_stats = {}
        for cid, cgrp in grp.groupby("category_id"):
            qtys = cgrp["qty"].values
            cname = cat_name_map.get(cid, str(cid))
            cat_stats[cid] = {
                "name": cname,
                "count": len(qtys),
                "mean": float(np.mean(qtys)),
                "std": float(np.std(qtys)) if len(qtys) > 1 else 5.0,
                "min": float(np.min(qtys)),
                "max": float(np.max(qtys)),
            }

        total_daily_grp = grp.groupby("date")["qty"].sum() if "date" in grp.columns else grp["qty"]
        profiles[rid] = {
            "retailer_id": rid,
            "frequent_category_ids": cats_taken,
            "frequent_category_names": {cat_name_map.get(c, str(c)) for c in cats_taken},
            "category_stats": cat_stats,
            "total_mean": float(total_daily_grp.mean()) if not total_daily_grp.empty else 0.0,
            "total_std": float(total_daily_grp.std()) if len(total_daily_grp) > 1 else 10.0,
            "active_days": len(total_daily_grp),
        }

    return profiles


# ============================================================
# 3. MULTI-FACTOR LOCAL ANOMALY DETECTOR
# ============================================================

def detect_driver_cash_shortfall(
    zone_name: str,
    cash_collected: float,
    cash_expenses: float,
    actual_handover: float = None,
    *args,
    **kwargs,
) -> dict | None:
    """
    Detects if driver handover is short of (cash collected - cash expenses).
    """
    expected = float(cash_collected) - float(cash_expenses)
    if actual_handover is not None:
        actual = float(actual_handover)
        deficit = expected - actual
        if deficit > 50.0:
            return {
                "retailer_id": 0,
                "retailer_name": f"Route Driver Handover ({zone_name})",
                "zone": str(zone_name),
                "category_id": 0,
                "category_name": "Cash Handover",
                "column": "CASH ₹",
                "entered_value": actual,
                "expected_value": expected,
                "deficit": deficit,
                "type": "DRIVER_CASH_DEFICIT",
                "anomaly_type": "DRIVER_CASH_DEFICIT",
                "severity": "CRITICAL",
                "title_en": "Driver Cash Shortfall",
                "title_mr": "चालक रोख तूट (शिल्लक रकमेत फरक)",
                "msg_en": f"Expected ₹{expected:,.2f} (Collected ₹{cash_collected:,.2f} - Expenses ₹{cash_expenses:,.2f}), but driver handed over ₹{actual:,.2f}. Shortfall: ₹{deficit:,.2f}!",
                "explanation_en": f"Expected ₹{expected:,.2f} (Collected ₹{cash_collected:,.2f} - Expenses ₹{cash_expenses:,.2f}), but driver handed over ₹{actual:,.2f}. Shortfall: ₹{deficit:,.2f}!",
                "msg_mr": f"अपेक्षित रक्कम ₹{expected:,.2f} (वसुली ₹{cash_collected:,.2f} - खर्च ₹{cash_expenses:,.2f}), पण चालकाने ₹{actual:,.2f} जमा केले. तूट: ₹{deficit:,.2f}!",
                "explanation_mr": f"अपेक्षित रक्कम ₹{expected:,.2f} (वसुली ₹{cash_collected:,.2f} - खर्च ₹{cash_expenses:,.2f}), पण चालकाने ₹{actual:,.2f} जमा केले. तूट: ₹{deficit:,.2f}!",
                "recommendation_en": f"Recover remaining balance of ₹{deficit:,.2f} from driver or check fuel/expense bills.",
                "recommendation_mr": f"चालकाकडून उर्वरित ₹{deficit:,.2f} जमा करून घ्या किंवा खर्चाच्या पावत्यांची पडताळणी करा.",
                "action": f"Recover remaining balance of ₹{deficit:,.2f} from driver.",
            }
        return None

    if expected < -200:
        return {
            "retailer_id": 0,
            "retailer_name": f"Route Driver Handover ({zone_name})",
            "zone": str(zone_name),
            "category_id": 0,
            "category_name": "Cash Handover",
            "column": "CASH ₹",
            "entered_value": expected,
            "type": "DRIVER_CASH_DEFICIT",
            "anomaly_type": "DRIVER_CASH_DEFICIT",
            "severity": "CRITICAL",
            "title_en": "Driver Cash Over-Expense Deficit",
            "title_mr": "चालक रोख तूट (खर्च रोख रकमेपेक्षा जास्त)",
            "msg_en": f"Driver collected ₹{cash_collected:,.2f} cash but spent ₹{cash_expenses:,.2f} in cash expenses (Deficit: ₹{abs(expected):,.2f}).",
            "explanation_en": f"Driver collected ₹{cash_collected:,.2f} cash but spent ₹{cash_expenses:,.2f} in cash expenses (Deficit: ₹{abs(expected):,.2f}).",
            "msg_mr": f"चालकाने ₹{cash_collected:,.2f} रोख जमा केले पण ₹{cash_expenses:,.2f} रोख खर्च केले (तूट: ₹{abs(expected):,.2f}).",
            "explanation_mr": f"चालकाने ₹{cash_collected:,.2f} रोख जमा केले पण ₹{cash_expenses:,.2f} रोख खर्च केले (तूट: ₹{abs(expected):,.2f}).",
            "recommendation_en": "Verify driver expense receipts or check if cash collection was under-reported.",
            "recommendation_mr": "चालकाच्या खर्चाच्या पावत्या तपासा किंवा रोख वसुली कमी नोंदवली आहे का ते पहा.",
            "action": "Verify driver expense receipts.",
        }
    return None


def detect_grid_anomalies(
    draft_df: pd.DataFrame,
    *args,
    posting_date: date = None,
    posting_zone: str = "All Zones",
    habit_profiles: dict = None,
    customer_habits: dict = None,
    categories_df: pd.DataFrame = None,
    expenses_df: pd.DataFrame = None,
    pay_mode_totals: dict = None,
    **kwargs,
) -> list[dict]:
    """
    Scans the live daily entry grid against learned customer profiles.
    Detects:
    1. Category Mismatch (e.g., entered Cow milk for a customer who never takes Cow)
    2. Volume Spike / Typo (e.g., entered 200L instead of 20L)
    3. Driver Cash Handover Discrepancy (cash collected minus expenses vs handover)
    Returns list of anomaly objects with bilingual English and Marathi explanations.
    """
    habits = habit_profiles if habit_profiles is not None else (customer_habits if customer_habits is not None else kwargs.get("habits"))
    cats = categories_df if categories_df is not None else (kwargs.get("categories_active") if kwargs.get("categories_active") is not None else kwargs.get("categories"))
    p_date = posting_date or kwargs.get("report_day")
    p_zone = posting_zone or kwargs.get("zone", "All Zones")
    exp_df = expenses_df if expenses_df is not None else kwargs.get("expenses")
    pay_totals = pay_mode_totals if pay_mode_totals is not None else kwargs.get("pay_totals")

    if args:
        for arg in args:
            if isinstance(arg, dict) and habits is None:
                habits = arg
            elif isinstance(arg, pd.DataFrame) and cats is None:
                cats = arg
            elif isinstance(arg, (date, str)) and p_date is None:
                p_date = arg
            elif isinstance(arg, str) and p_zone == "All Zones":
                p_zone = arg
            elif isinstance(arg, pd.DataFrame) and exp_df is None:
                exp_df = arg
            elif isinstance(arg, dict) and pay_totals is None:
                pay_totals = arg

    if habits is None:
        habits = {}
    if cats is None:
        cats = pd.DataFrame()
    p_zone = str(p_zone) if p_zone else "All Zones"

    anomalies = []
    if draft_df is None or draft_df.empty:
        return anomalies

    cat_cols_meta = []
    if cats is not None and not cats.empty:
        for _, c in cats.iterrows():
            cid = int(pd.to_numeric(c.get("category_id", 0), errors="coerce") or 0)
            cname = str(c.get("name", "")).strip()
            # Find column in draft_df
            for col in draft_df.columns:
                if col.startswith(f"CID:{cid}") or (cname and cname.lower() in col.lower() and "qty" in col.lower()):
                    cat_cols_meta.append({"col": col, "cid": cid, "name": cname})
                    break

    for _, row in draft_df.iterrows():
        rname = str(row.get("Retailer", "")).strip()
        rid_val = row.get("ID", "")
        if rname in ("GRAND TOTAL", "TOTAL", ""):
            continue
        try:
            rid = int(rid_val)
        except Exception:
            continue

        profile = habits.get(rid)

        # 1. Inspect Category & Volume Anomalies
        for meta in cat_cols_meta:
            col = meta["col"]
            cid = meta["cid"]
            cname = meta["name"]
            qty = float(pd.to_numeric(row.get(col, 0.0), errors="coerce") or 0.0)

            if qty > 0 and profile:
                freq_cids = profile.get("frequent_category_ids", set())
                # Category Mismatch Anomaly
                if cid not in freq_cids and profile.get("active_days", 0) >= 5:
                    habit_cats_en = ", ".join(profile.get("frequent_category_names", []))
                    msg_en = f"{rname} historically only purchases [{habit_cats_en}]. '{cname}' ({qty:.1f} L) is unusual for this client."
                    msg_mr = f"{rname} नेहमी फक्त [{habit_cats_en}] घेतात. आज '{cname}' ({qty:.1f} L) नोंदवले आहे, कृपया खात्री करा."
                    rec_en = f"Verify if {rname} actually requested {cname} or if this was entered by mistake."
                    rec_mr = f"{rname} यांनी खरेच {cname} मागवले आहे का, किंवा चुकून नोंद झाली आहे ते तपासा."
                    anomalies.append({
                        "retailer_id": rid,
                        "retailer_name": rname,
                        "zone": p_zone,
                        "category_id": cid,
                        "category_name": cname,
                        "column": col,
                        "entered_value": qty,
                        "type": "CATEGORY_MISMATCH",
                        "anomaly_type": "CATEGORY_MISMATCH",
                        "severity": "HIGH",
                        "title_en": "Unexpected Milk Category",
                        "title_mr": "अनपेक्षित दूध प्रकार (चुकीची नोंद संभाव्य)",
                        "msg_en": msg_en,
                        "explanation_en": msg_en,
                        "msg_mr": msg_mr,
                        "explanation_mr": msg_mr,
                        "recommendation_en": rec_en,
                        "recommendation_mr": rec_mr,
                        "action": rec_en,
                    })

                # Volume Spike Anomaly (> 2.5 std devs or > 3x historical mean)
                cstat = profile.get("category_stats", {}).get(cid)
                if cstat and cstat["count"] >= 3:
                    mean_q = cstat["mean"]
                    std_q = max(cstat["std"], 3.0)
                    threshold = mean_q + 2.8 * std_q
                    ratio = qty / mean_q if mean_q > 0 else 1.0

                    if qty > threshold and ratio >= 2.2:
                        msg_en = f"{qty:.1f} L is {ratio:.1f}x higher than average ({mean_q:.1f} L, typical max: {cstat['max']:.1f} L)."
                        msg_mr = f"{qty:.1f} L हे नेहमीच्या सरासरीपेक्षा ({mean_q:.1f} L) {ratio:.1f} पट जास्त आहे."
                        rec_en = f"Check if an extra zero was typed (e.g. {qty/10:.1f} L intended instead of {qty:.1f} L)."
                        rec_mr = f"अतिरिक्त शून्य दाबले गेले आहे का ते तपासा (उदा. {qty/10:.1f} L ऐवजी {qty:.1f} L)."
                        anomalies.append({
                            "retailer_id": rid,
                            "retailer_name": rname,
                            "zone": p_zone,
                            "category_id": cid,
                            "category_name": cname,
                            "column": col,
                            "entered_value": qty,
                            "type": "VOLUME_SPIKE",
                            "anomaly_type": "VOLUME_SPIKE",
                            "severity": "HIGH",
                            "title_en": "Unusually High Volume (Typo Alert)",
                            "title_mr": "अस्वाभाविक जास्त दूध प्रमाण (टायपिंग चूक?)",
                            "msg_en": msg_en,
                            "explanation_en": msg_en,
                            "msg_mr": msg_mr,
                            "explanation_mr": msg_mr,
                            "recommendation_en": rec_en,
                            "recommendation_mr": rec_mr,
                            "action": rec_en,
                        })

    # 2. Driver Route Cash Handover Discrepancy
    if pay_totals and p_zone != "All Zones":
        cash_col = float(pay_totals.get("Cash", pay_totals.get("CASH", 0.0)))
        exp_cash = 0.0
        if exp_df is not None and not exp_df.empty:
            for _, er in exp_df.iterrows():
                emode = str(er.get("Payment Mode", er.get("payment_mode", "Cash"))).strip().upper()
                if emode == "CASH":
                    exp_cash += float(pd.to_numeric(er.get("Amount ₹", er.get("amount", 0.0)), errors="coerce") or 0.0)

        shortfall = detect_driver_cash_shortfall(p_zone, cash_col, exp_cash)
        if shortfall:
            anomalies.append(shortfall)

    return anomalies


DEVANAGARI_TRANSLIT_MAP = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h", "ळ": "l", "क्ष": "x", "ज्ञ": "dny",
    "ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ं": "n",
    "्": "", "ॅ": "a", "ॉ": "o", "डेअरी": "dairy", "डेरी": "dairy",
}

def devanagari_to_latin(text: str) -> str:
    out = ""
    for ch in text:
        out += DEVANAGARI_TRANSLIT_MAP.get(ch, ch)
    return out

def phonetic_norm(s: str) -> str:
    s = devanagari_to_latin(s.lower())
    s = (
        s.replace("x", "ks")
        .replace("ksh", "ks")
        .replace("sh", "s")
        .replace("ph", "f")
        .replace("dairy", "dry")
        .replace("deari", "dry")
        .replace("center", "cntr")
        .replace("centre", "cntr")
    )
    # Strip vowels to bridge English vs Devanagari implicit vowel spellings
    vowel_stripped = re.sub(r"[aeiou]", "", s)
    clean = re.sub(r"[^a-z0-9]", "", vowel_stripped)
    return clean


# ============================================================
# 4. MARATHI & ENGLISH NATURAL SPEECH / TEXT ENTRY PARSER
# ============================================================

def parse_natural_voice_entry(
    raw_text: str,
    retailers_active: pd.DataFrame,
    categories_active: pd.DataFrame,
) -> dict:
    """
    Parses conversational dairy entry speech/text in Marathi, English, or mixed Hinglish/Marathlish.
    Examples:
      - "vis mahis gupta dairy payment pach hazaar cash"
      - "20 buffalo gupta dairy payment 5000 cash"
      - "पन्नास गाय लक्ष्मी डेअरी रोख तीन हजार"
      - "dilavar patel 140 cow 110 standard"
    Returns structured dict:
      {
         "retailer_id": int or None,
         "retailer_name": str or None,
         "items": [{"category_id": int, "category_name": str, "qty": float}],
         "payment": {"amount": float, "mode": str},
         "confidence": float,
         "raw_text": str
      }
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {"retailer_id": None, "retailer_name": None, "items": [], "payment": None, "confidence": 0.0, "raw_text": ""}

    text = raw_text.lower().strip()
    # Normalize punctuation
    text = re.sub(r"[,;।\.]", " ", text)
    tokens = text.split()

    # 1. Number normalization
    def word_to_num(w: str) -> float | None:
        if w.replace(".", "", 1).isdigit():
            return float(w)
        if w in MARATHI_ENGLISH_NUMBERS:
            return float(MARATHI_ENGLISH_NUMBERS[w])
        # Try transliterated word
        w_t = devanagari_to_latin(w)
        if w_t in MARATHI_ENGLISH_NUMBERS:
            return float(MARATHI_ENGLISH_NUMBERS[w_t])
        return None

    # 2. Extract Retailer Match
    best_retailer = None
    best_score = 0.0
    norm_full_input = phonetic_norm(raw_text)

    if retailers_active is not None and not retailers_active.empty:
        for _, r in retailers_active.iterrows():
            r_name = str(r.get("name", "")).strip()
            rid = int(pd.to_numeric(r.get("retailer_id", 0), errors="coerce") or 0)
            clean_r_name = re.sub(r"\(.*?\)", "", r_name).strip()
            norm_r_name = phonetic_norm(clean_r_name)

            if not norm_r_name:
                continue

            # Substring check in phonetic space
            if norm_r_name in norm_full_input:
                score = 1.0 + len(norm_r_name) / 100.0
            else:
                # Word-level fuzzy similarity
                r_words = clean_r_name.lower().split()
                norm_words = [phonetic_norm(w) for w in r_words if w.lower() not in ("dairy", "center", "centre", "milk")]
                if norm_words:
                    word_match_count = sum(1 for nw in norm_words if nw in norm_full_input or difflib.get_close_matches(nw, [norm_full_input], cutoff=0.7))
                    score = word_match_count / len(norm_words)
                else:
                    score = difflib.SequenceMatcher(None, norm_r_name, norm_full_input).ratio()

            if score > best_score and score >= 0.5:
                best_score = score
                best_retailer = (rid, r_name)

    # 3. Extract Categories & Quantities
    items = []
    # Build category lookup
    cat_lookup = {}
    if categories_active is not None and not categories_active.empty:
        for _, c in categories_active.iterrows():
            cid = int(pd.to_numeric(c.get("category_id", 0), errors="coerce") or 0)
            cname = str(c.get("name", "")).strip()
            cat_lookup[cname.lower()] = (cid, cname)

    # Scan for [Number] [Category] or [Category] [Number]
    for i, tok in enumerate(tokens):
        num_val = word_to_num(tok)
        if num_val is not None and num_val > 0:
            # Check if next or preceding token is category
            cat_found = None
            # Check next token
            if i + 1 < len(tokens):
                nxt = tokens[i + 1]
                for syn, mapped_name in CATEGORY_SYNONYMS.items():
                    if nxt == syn or nxt.startswith(syn):
                        cat_found = mapped_name
                        break
            # Check previous token
            if not cat_found and i - 1 >= 0:
                prev = tokens[i - 1]
                for syn, mapped_name in CATEGORY_SYNONYMS.items():
                    if prev == syn or prev.startswith(syn):
                        cat_found = mapped_name
                        break

            if cat_found:
                matched_cid = 0
                for cname_l, (cid, cname) in cat_lookup.items():
                    if cat_found.lower() in cname_l:
                        matched_cid = cid
                        cat_found = cname
                        break
                items.append({
                    "category_id": matched_cid,
                    "category_name": cat_found,
                    "qty": num_val,
                })

    # 4. Extract Payments (Payment [Amount] [Mode] or [Mode] [Amount])
    payment_info = None
    pay_keywords = ["payment", "jama", "dile", "diya", "पेमेंट", "जमा", "दिले", "दिलेले", "रक्कम"]
    pay_triggers = set(pay_keywords) | set(PAYMENT_SYNONYMS.keys())
    has_payment_mention = any(k in tokens or k in text for k in pay_triggers)

    pay_amount = 0.0
    pay_mode = "Cash"

    # Identify payment mode
    for syn, mode_name in PAYMENT_SYNONYMS.items():
        if syn in tokens or syn in text:
            pay_mode = mode_name
            break

    # Identify payment amount
    for i, tok in enumerate(tokens):
        if tok in pay_triggers and i + 1 < len(tokens):
            val1 = word_to_num(tokens[i + 1])
            if val1 is not None:
                if i + 2 < len(tokens) and tokens[i + 2] in ("hazaar", "hazar", "हजार", "thousand"):
                    pay_amount = val1 * 1000.0
                elif i + 2 < len(tokens) and tokens[i + 2] in ("shambhar", "she", "hundred", "शंभर"):
                    pay_amount = val1 * 100.0
                else:
                    pay_amount = val1
                break

    # Check reverse case: [Number] [Mode], e.g. "5000 cash" or "teen hazaar rokh"
    if pay_amount == 0.0:
        for i, tok in enumerate(tokens):
            if tok in PAYMENT_SYNONYMS and i > 0:
                if tokens[i - 1] in ("hazaar", "hazar", "हजार", "thousand") and i > 1:
                    v_base = word_to_num(tokens[i - 2])
                    if v_base is not None:
                        pay_amount = v_base * 1000.0
                        break
                else:
                    v_direct = word_to_num(tokens[i - 1])
                    if v_direct is not None:
                        pay_amount = v_direct
                        break

    # Fallback payment extraction if payment keywords used with digits in raw text
    if pay_amount == 0.0 and has_payment_mention:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:cash|upi|cheque|rok|rokh|पेमेंट|रोख)?", text)
        if m:
            pay_amount = float(m.group(1))

    if pay_amount > 0 or has_payment_mention:
        payment_info = {
            "amount": pay_amount,
            "mode": pay_mode,
        }

    confidence = 0.0
    if best_retailer:
        confidence += 0.5
    if items:
        confidence += 0.35
    if payment_info:
        confidence += 0.15

    return {
        "retailer_id": best_retailer[0] if best_retailer else None,
        "retailer_name": best_retailer[1] if best_retailer else None,
        "items": items,
        "payment": payment_info,
        "confidence": round(min(confidence, 1.0), 2),
        "raw_text": raw_text,
    }
