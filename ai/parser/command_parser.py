"""
Deterministic Command Parser for Milk Accounting Pro Intelligence Layer.
Extracts structured financial transactions, detects missing fields, calculates component confidence,
and preserves strict pricing boundaries (rate is never invented).
"""

import re
import pandas as pd
from ai.schemas.command_types import (
    IntentType,
    ConfidenceScore,
    ParsedDraft,
    ParsedItem,
    SaleCommand,
    PaymentCommand,
    ExpenseCommand,
    PurchaseCommand,
)
from ai.parser.intent_classifier import classify_intent
from ai.parser.number_parser import parse_number_words, extract_quantities_with_units
from ai.entity_resolution.retailer_matcher import match_retailer
from ai.entity_resolution.category_matcher import match_category
from ai.entity_resolution.distributor_matcher import match_distributor

PAYMENT_MODE_SYNONYMS: dict[str, str] = {
    "cash": "Cash", "rok": "Cash", "rokh": "Cash", "rokadh": "Cash",
    "रोख": "Cash", "रोकड": "Cash", "कैश": "Cash",
    "upi": "UPI", "gpay": "UPI", "phonepe": "UPI", "paytm": "UPI", "online": "UPI",
    "यूपीआय": "UPI", "ऑनलाइन": "UPI",
    "cheque": "Cheque", "check": "Cheque", "चेक": "Cheque",
    "bank": "Bank", "बँक": "Bank", "neft": "Bank", "rtgs": "Bank",
}

EXPENSE_CATEGORY_SYNONYMS: dict[str, str] = {
    "fuel": "Fuel", "diesel": "Fuel", "petrol": "Fuel", "डिझेल": "Fuel", "पेट्रोल": "Fuel", "फ्युएल": "Fuel",
    "nasta": "Nasta", "snacks": "Nasta", "tea": "Nasta", "चहा": "Nasta", "नाष्टा": "Nasta", "नाश्ता": "Nasta",
    "toll": "Toll", "टोल": "Toll", "टोलनाका": "Toll",
    "repair": "Repair", "puncture": "Repair", "दुरुस्ती": "Repair", "पंचर": "Repair", "काम": "Repair",
    "police": "Police / Fine", "fine": "Police / Fine", "दंड": "Police / Fine", "पोलीस": "Police / Fine",
}


def parse_command(
    raw_text: str,
    retailers_df: pd.DataFrame,
    categories_df: pd.DataFrame,
    distributors_df: pd.DataFrame = None,
    active_zone: str | None = None,
    mode_lock: str | None = None,
) -> ParsedDraft:
    """
    Parses conversational speech or typed text into a structured ParsedDraft.
    Enforces validation:
      - Does not guess missing amounts or quantities
      - Flags ambiguous matches for user clarification
      - Leaves rates strictly None (designated for deterministic ERP lookup)
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return ParsedDraft(
            is_valid_draft=False,
            error_message="Empty speech or text input. (रिक्त नोंद)",
        )

    text = raw_text.strip()
    clean_text = re.sub(r"[,;।]", " ", text)
    tokens = clean_text.split()

    # Step 1: Classify intent
    intent, intent_conf = classify_intent(clean_text, mode_lock=mode_lock)

    # Step 2: Detect payment mode if present
    detected_pay_mode = "Cash"
    pay_mode_conf = 0.80
    for syn, canonical_mode in PAYMENT_MODE_SYNONYMS.items():
        if re.search(rf"\b{re.escape(syn)}\b", clean_text, re.IGNORECASE):
            detected_pay_mode = canonical_mode
            pay_mode_conf = 0.95
            break

    missing_fields: list[str] = []
    confidence = ConfidenceScore(intent=intent_conf, payment_mode=pay_mode_conf)

    # =========================================================
    # INTENT: ROUTE EXPENSE
    # =========================================================
    if intent == IntentType.ROUTE_EXPENSE:
        # Resolve expense category (default: Fuel)
        exp_cat = "Fuel"
        for syn, canonical_cat in EXPENSE_CATEGORY_SYNONYMS.items():
            if re.search(rf"\b{re.escape(syn)}\b", clean_text, re.IGNORECASE):
                exp_cat = canonical_cat
                break

        # Extract expense amount
        # Search for numbers in text
        amount_val = None
        # Try extracting numbers
        quantities = extract_quantities_with_units(clean_text)
        if quantities:
            amount_val = quantities[-1]["val"]
        else:
            amount_val = parse_number_words(tokens)

        if amount_val is None or amount_val <= 0:
            missing_fields.append("Expense amount missing (खर्चाची रक्कम आवश्यक)")
            confidence.amount = 0.0
        else:
            confidence.amount = 0.90

        confidence.entity = 0.90
        confidence.overall = round((confidence.intent + confidence.amount + confidence.payment_mode) / 3.0, 2)
        confidence.compute_level()

        exp_cmd = ExpenseCommand(
            category=exp_cat,
            amount=amount_val or 0.0,
            payment_mode=detected_pay_mode,
            zone=active_zone,
            note=text,
        )

        return ParsedDraft(
            intent=intent,
            command=exp_cmd,
            confidence=confidence,
            raw_text=text,
            normalized_text=clean_text,
            missing_fields=missing_fields,
            is_valid_draft=(len(missing_fields) == 0),
        )

    # =========================================================
    # INTENT: DISTRIBUTOR PURCHASE / PAYMENT
    # =========================================================
    if intent in (IntentType.DISTRIBUTOR_PURCHASE, IntentType.DISTRIBUTOR_PAYMENT):
        dist_match, amb, dist_conf = match_distributor(clean_text, distributors_df)
        confidence.entity = dist_conf

        if amb:
            return ParsedDraft(
                intent=intent,
                confidence=confidence,
                raw_text=text,
                ambiguity=amb,
                is_valid_draft=False,
                missing_fields=["Ambiguous distributor name (अनेक सप्लायर पर्याय)"],
            )

        if not dist_match:
            missing_fields.append("Distributor name missing or not found (सप्लायरचे नाव आढळले नाही)")

        if intent == IntentType.DISTRIBUTOR_PAYMENT:
            amt = parse_number_words(tokens)
            if not amt or amt <= 0:
                missing_fields.append("Payment amount missing (पेमेंट रक्कम आवश्यक)")
                confidence.amount = 0.0
            else:
                confidence.amount = 0.90

            confidence.overall = round((confidence.intent + confidence.entity + confidence.amount) / 3.0, 2)
            confidence.compute_level()

            cmd = PaymentCommand(
                retailer_id=dist_match["id"] if dist_match else 0,
                retailer_name=dist_match["name"] if dist_match else "",
                amount=amt or 0.0,
                payment_mode=detected_pay_mode,
            )
            return ParsedDraft(
                intent=intent,
                command=cmd,
                confidence=confidence,
                raw_text=text,
                missing_fields=missing_fields,
                is_valid_draft=(len(missing_fields) == 0),
            )

        # Distributor Purchase
        cat_match, cat_conf = match_category(clean_text, categories_df)
        confidence.category = cat_conf
        qty_val = parse_number_words(tokens)
        if not qty_val or qty_val <= 0:
            missing_fields.append("Purchase quantity missing (खरेदी प्रमाण आवश्यक)")
            confidence.quantity = 0.0
        else:
            confidence.quantity = 0.90

        confidence.overall = round((confidence.intent + confidence.entity + confidence.category + confidence.quantity) / 4.0, 2)
        confidence.compute_level()

        pur_cmd = PurchaseCommand(
            distributor_id=dist_match["id"] if dist_match else 0,
            distributor_name=dist_match["name"] if dist_match else "",
            category_id=cat_match["id"] if cat_match else 0,
            category_name=cat_match["name"] if cat_match else "",
            qty=qty_val or 0.0,
            rate=None,  # NEVER guess rate
        )
        return ParsedDraft(
            intent=intent,
            command=pur_cmd,
            confidence=confidence,
            raw_text=text,
            missing_fields=missing_fields,
            is_valid_draft=(len(missing_fields) == 0),
        )

    # =========================================================
    # INTENT: RETAILER PAYMENT
    # =========================================================
    if intent == IntentType.RETAILER_PAYMENT:
        ret_match, amb, ret_conf = match_retailer(clean_text, retailers_df, active_zone=active_zone)
        confidence.entity = ret_conf

        if amb:
            return ParsedDraft(
                intent=intent,
                confidence=confidence,
                raw_text=text,
                ambiguity=amb,
                is_valid_draft=False,
                missing_fields=["Ambiguous customer name (एकापेक्षा जास्त ग्राहक पर्याय)"],
            )

        if not ret_match:
            missing_fields.append("Customer name missing or not found (ग्राहकाचे नाव आवश्यक)")

        # Extract payment amount
        # Search numbers around payment tokens
        pay_amount = None
        # Try extracting digits
        digits = extract_quantities_with_units(clean_text)
        if digits:
            pay_amount = digits[-1]["val"]
        else:
            pay_amount = parse_number_words(tokens)

        if not pay_amount or pay_amount <= 0:
            missing_fields.append("Payment amount missing (पेमेंट रक्कम आवश्यक)")
            confidence.amount = 0.0
        else:
            confidence.amount = 0.90

        confidence.overall = round((confidence.intent + confidence.entity + confidence.amount + confidence.payment_mode) / 4.0, 2)
        confidence.compute_level()

        pay_cmd = PaymentCommand(
            retailer_id=ret_match["id"] if ret_match else 0,
            retailer_name=ret_match["name"] if ret_match else "",
            amount=pay_amount or 0.0,
            payment_mode=detected_pay_mode,
            zone=ret_match.get("zone") if ret_match else active_zone,
        )

        return ParsedDraft(
            intent=intent,
            command=pay_cmd,
            confidence=confidence,
            raw_text=text,
            normalized_text=clean_text,
            missing_fields=missing_fields,
            is_valid_draft=(len(missing_fields) == 0),
        )

    # =========================================================
    # INTENT: RETAILER SALE (DEFAULT MILK DELIVERY)
    # =========================================================
    ret_match, amb, ret_conf = match_retailer(clean_text, retailers_df, active_zone=active_zone)
    confidence.entity = ret_conf

    if amb:
        return ParsedDraft(
            intent=IntentType.RETAILER_SALE,
            confidence=confidence,
            raw_text=text,
            ambiguity=amb,
            is_valid_draft=False,
            missing_fields=["Ambiguous customer name (एकापेक्षा जास्त ग्राहक पर्याय)"],
        )

    if not ret_match:
        missing_fields.append("Customer name missing or not found (ग्राहकाचे नाव आवश्यक)")

    # Separate delivery clause from optional payment clause
    delivery_text = clean_text
    payment_text = ""
    for kw in ["payment", "पेमेंट", "cash", "रोख", "रोकड", "कैश", "upi", "यूपीआय", "online", "cheque", "चेक", "जमा", "jama"]:
        m = re.search(rf"(?:(?<=\s)|^){re.escape(kw)}(?=\s|$)", clean_text, re.IGNORECASE)
        if m:
            delivery_text = clean_text[:m.start()].strip()
            payment_text = clean_text[m.start():].strip()
            break

    del_tokens = delivery_text.split()

    # Match Category
    cat_match, cat_conf = match_category(delivery_text, categories_df)
    confidence.category = cat_conf
    if not cat_match:
        # Default fallback to first active category if only 1 category exists, else flag missing
        if categories_df is not None and len(categories_df) == 1:
            first_c = categories_df.iloc[0]
            cat_id = int(first_c.get("category_id", first_c.get("id", 1)))
            cat_match = {"id": cat_id, "name": str(first_c["name"])}
            confidence.category = 0.70
        else:
            missing_fields.append("Milk category missing (दुधाचा प्रकार आवश्यक: Buffalo / Cow)")

    # Extract Quantity from delivery clause
    qty_val = None
    units_found = extract_quantities_with_units(delivery_text)
    if units_found:
        qty_val = units_found[0]["val"]
    else:
        qty_val = parse_number_words(del_tokens)

    if not qty_val or qty_val <= 0:
        missing_fields.append("Milk quantity missing (दुधाचे प्रमाण आवश्यक)")
        confidence.quantity = 0.0
    else:
        confidence.quantity = 0.90

    # Extract optional payment amount and mode
    cash_pay = 0.0
    upi_pay = 0.0
    cheque_pay = 0.0
    if payment_text:
        pay_units = extract_quantities_with_units(payment_text)
        if pay_units:
            pay_amt = pay_units[-1]["val"]
        else:
            pay_amt = parse_number_words(payment_text.split())

        if pay_amt and pay_amt > 0:
            if detected_pay_mode == "UPI":
                upi_pay = float(pay_amt)
            elif detected_pay_mode == "Cheque":
                cheque_pay = float(pay_amt)
            else:
                cash_pay = float(pay_amt)

    confidence.overall = round((confidence.intent + confidence.entity + confidence.category + confidence.quantity) / 4.0, 2)
    confidence.compute_level()

    items = []
    if cat_match and qty_val:
        items.append(ParsedItem(
            category_id=cat_match["id"],
            category_name=cat_match["name"],
            qty=qty_val,
            rate=None,  # NEVER guess rate. Retained for ERP lookup.
        ))

    sale_cmd = SaleCommand(
        retailer_id=ret_match["id"] if ret_match else 0,
        retailer_name=ret_match["name"] if ret_match else "",
        items=items,
        cash_payment=cash_pay,
        upi_payment=upi_pay,
        cheque_payment=cheque_pay,
        zone=ret_match.get("zone") if ret_match else active_zone,
    )

    return ParsedDraft(
        intent=IntentType.RETAILER_SALE,
        command=sale_cmd,
        confidence=confidence,
        raw_text=text,
        normalized_text=clean_text,
        missing_fields=missing_fields,
        is_valid_draft=(len(missing_fields) == 0),
    )
