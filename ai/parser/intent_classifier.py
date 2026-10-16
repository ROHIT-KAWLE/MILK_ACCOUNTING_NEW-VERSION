"""
Intent Classifier for Intelligence Pipeline.
Determines whether spoken command is a Retailer Sale, Customer Payment, Route Expense,
or Distributor Purchase/Payment. Supports explicit mode locking and auto-detection.
"""

from ai.schemas.command_types import IntentType

EXPENSE_KEYWORDS: set[str] = {
    "खर्च", "expense", "exp", "expenses", "fuel", "डिझेल", "diesel", "petrol", "पेट्रोल",
    "nasta", "नाष्टा", "नाश्ता", "snacks", "tea", "चहा", "toll", "टोल", "repair", "दुरुस्ती",
    "puncture", "पंचर", "fine", "police", "दंड", "पोलीस", "चालक खर्च",
}

DISTRIBUTOR_KEYWORDS: set[str] = {
    "खरेदी", "purchase", "distributor", "डिस्ट्रीब्यूटर", "procurement", "सप्लायर", "vendor",
    "खरेदीचे", "खरेदी बिल",
}

PAYMENT_KEYWORDS: set[str] = {
    "पेमेंट", "payment", "जमा", "jama", "dile", "diya", "paid", "दिले", "दिलेले",
    "रक्कम", "vasuli", "वसुली", "rokh", "rok", "रोख", "cheque", "चेक", "upi",
}

MILK_ITEM_KEYWORDS: set[str] = {
    "buffalo", "cow", "mahis", "gaay", "gay", "म्हैस", "गाय", "दूध", "मिल्क",
    "standard", "special", "paneer", "पनीर", "chaas", "ताक", "gokul", "amul",
    "लिटर", "liter", "litre", "liters", "litres",
}


def classify_intent(
    text: str,
    mode_lock: str | None = None,
) -> tuple[IntentType, float]:
    """
    Classifies the user's spoken or typed intent.
    mode_lock options:
      - 'RETAILER' / 'retailer_delivery': restricts to RETAILER_SALE or RETAILER_PAYMENT
      - 'EXPENSE' / 'route_expense': restricts to ROUTE_EXPENSE
      - 'DISTRIBUTOR' / 'distributor_procurement': restricts to DISTRIBUTOR_PURCHASE or DISTRIBUTOR_PAYMENT
      - None or 'AUTO': auto-detects from full vocabulary
    Returns:
      (IntentType, confidence_score)
    """
    if not text:
        return IntentType.UNKNOWN, 0.0

    lower = text.lower().strip()
    tokens = set(lower.split())

    has_milk_item = any(k in tokens or k in lower for k in MILK_ITEM_KEYWORDS)
    has_payment_keyword = any(k in tokens or k in lower for k in PAYMENT_KEYWORDS)
    has_expense_keyword = any(k in tokens or k in lower for k in EXPENSE_KEYWORDS)
    has_distributor_keyword = any(k in tokens or k in lower for k in DISTRIBUTOR_KEYWORDS)

    m = (mode_lock or "").upper()

    # Case 1: Mode is locked to Expense
    if "EXPENSE" in m:
        return IntentType.ROUTE_EXPENSE, 1.0

    # Case 2: Mode is locked to Distributor
    if "DISTRIBUTOR" in m or "PURCHASE" in m:
        if has_payment_keyword and not has_milk_item:
            return IntentType.DISTRIBUTOR_PAYMENT, 0.95
        return IntentType.DISTRIBUTOR_PURCHASE, 0.90

    # Case 3: Mode is locked to Retailer
    if "RETAILER" in m or "DELIVERY" in m or "SALE" in m:
        if has_payment_keyword and not has_milk_item:
            return IntentType.RETAILER_PAYMENT, 0.95
        return IntentType.RETAILER_SALE, 0.90

    # Case 4: AUTO Detection
    # 4a. Check Route Expense triggers
    if has_expense_keyword:
        return IntentType.ROUTE_EXPENSE, 0.95

    # 4b. Check Distributor triggers
    if has_distributor_keyword:
        if has_payment_keyword and not has_milk_item:
            return IntentType.DISTRIBUTOR_PAYMENT, 0.92
        return IntentType.DISTRIBUTOR_PURCHASE, 0.90

    # 4c. Check Retailer Payment triggers (pure payment without milk items)
    if has_payment_keyword and not has_milk_item:
        return IntentType.RETAILER_PAYMENT, 0.88

    # 4d. Default to Retailer Sale
    return IntentType.RETAILER_SALE, 0.80
