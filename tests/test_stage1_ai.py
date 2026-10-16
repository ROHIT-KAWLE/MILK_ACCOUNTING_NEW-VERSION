"""
STAGE 1 COMPREHENSIVE TEST SUITE
================================
Tests Core Interfaces, Multilingual Number Parser, Intent Classifier,
Phonetic Normalizer, Entity Resolution (with Ambiguity Checking),
and Command Parser (with Missing-Field & Rate-Protection Verification).
"""

import sys
import os
import pandas as pd
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.schemas.command_types import (
    IntentType,
    SaleCommand,
    ExpenseCommand,
)
from ai.parser.number_parser import parse_number_words, parse_single_token
from ai.parser.intent_classifier import classify_intent
from ai.entity_resolution.phonetic import phonetic_norm
from ai.entity_resolution.retailer_matcher import match_retailer
from ai.entity_resolution.category_matcher import match_category
from ai.entity_resolution.distributor_matcher import match_distributor
from ai.parser.command_parser import parse_command


# ============================================================
# 1. NUMBER PARSER TESTS (Multilingual & Fractions)
# ============================================================

def test_number_parser_digits_and_english():
    assert parse_single_token("20") == 20.0
    assert parse_single_token("5000") == 5000.0
    assert parse_single_token("0.5") == 0.5
    assert parse_single_token("twenty") == 20.0
    assert parse_single_token("thirty") == 30.0
    assert parse_single_token("fifty") == 50.0
    assert parse_number_words("five thousand") == 5000.0
    assert parse_number_words("two hundred") == 200.0


def test_number_parser_marathi_devanagari():
    assert parse_single_token("वीस") == 20.0
    assert parse_single_token("पन्नास") == 50.0
    assert parse_single_token("शंभर") == 100.0
    assert parse_number_words("पाच हजार") == 5000.0
    assert parse_number_words("तीन हजार") == 3000.0
    assert parse_number_words("दोनशे") == 200.0


def test_number_parser_marathi_romanized():
    assert parse_single_token("vis") == 20.0
    assert parse_single_token("vees") == 20.0
    assert parse_single_token("pannas") == 50.0
    assert parse_single_token("shambhar") == 100.0
    assert parse_number_words("pach hazaar") == 5000.0
    assert parse_number_words("teen hazaar") == 3000.0
    assert parse_number_words("don she") == 200.0


def test_number_parser_fractions_and_modifiers():
    assert parse_single_token("पाव") == 0.25
    assert parse_single_token("अर्धा") == 0.50
    assert parse_single_token("पाऊण") == 0.75
    assert parse_single_token("दीड") == 1.50
    assert parse_single_token("अडीच") == 2.50
    assert parse_number_words("साडे तीन") == 3.50
    assert parse_number_words("साडे तीन हजार") == 3500.0
    assert parse_number_words("सव्वा पाच") == 5.25
    assert parse_number_words("पावणे चार") == 3.75


# ============================================================
# 2. INTENT CLASSIFIER TESTS
# ============================================================

def test_intent_classification():
    # Retailer delivery (sale)
    i1, _ = classify_intent("Gupta dairy 20 buffalo")
    assert i1 == IntentType.RETAILER_SALE

    # Retailer payment
    i2, _ = classify_intent("Gupta dairy payment 5000 cash")
    assert i2 == IntentType.RETAILER_PAYMENT

    i3, _ = classify_intent("Laxmi dairy 3000 jama rokh")
    assert i3 == IntentType.RETAILER_PAYMENT

    # Route expense
    i4, _ = classify_intent("खर्च डिझेल 500 रुपये कैश")
    assert i4 == IntentType.ROUTE_EXPENSE

    i5, _ = classify_intent("Fuel 600 cash diesel")
    assert i5 == IntentType.ROUTE_EXPENSE

    i6, _ = classify_intent("Nasta 120 cash snacks tea")
    assert i6 == IntentType.ROUTE_EXPENSE

    # Distributor purchase
    i7, _ = classify_intent("खरेदी संगम डेअरी 500 म्हैस")
    assert i7 == IntentType.DISTRIBUTOR_PURCHASE

    i8, _ = classify_intent("Warna dairy purchase 300 buffalo")
    assert i8 == IntentType.DISTRIBUTOR_PURCHASE

    # Mode locking
    i_locked, _ = classify_intent("500 diesel", mode_lock="EXPENSE")
    assert i_locked == IntentType.ROUTE_EXPENSE


# ============================================================
# 3. PHONETIC & ENTITY RESOLUTION TESTS
# ============================================================

@pytest.fixture
def mock_retailers():
    return pd.DataFrame([
        {"retailer_id": 1, "name": "Gupta Dairy", "zone": "Route 1"},
        {"retailer_id": 2, "name": "Laxmi Dairy", "zone": "Route 2"},
        {"retailer_id": 3, "name": "Gupta Milk Center", "zone": "Route 1"},
        {"retailer_id": 4, "name": "Patel Milk Agency", "zone": "Route 3"},
    ])


@pytest.fixture
def mock_categories():
    return pd.DataFrame([
        {"category_id": 1, "name": "Buffalo"},
        {"category_id": 2, "name": "Cow"},
        {"category_id": 3, "name": "Amul Chaas"},
    ])


@pytest.fixture
def mock_distributors():
    return pd.DataFrame([
        {"distributor_id": 1, "name": "Sangam Dairy"},
        {"distributor_id": 2, "name": "Warna Dairy"},
    ])


def test_phonetic_normalization():
    assert phonetic_norm("Dairy") == phonetic_norm("डेअरी")
    assert phonetic_norm("Laxmi") == phonetic_norm("लक्ष्मी")


def test_retailer_matching_exact_and_phonetic(mock_retailers):
    # Match English exact
    m1, amb1, conf1 = match_retailer("20 buffalo patel milk agency", mock_retailers)
    assert m1 is not None and m1["id"] == 4
    assert amb1 is None
    assert conf1 >= 0.85

    # Match Devanagari script
    m2, amb2, conf2 = match_retailer("पन्नास गाय लक्ष्मी डेअरी", mock_retailers)
    assert m2 is not None and m2["id"] == 2
    assert amb2 is None
    assert conf2 >= 0.80


def test_retailer_ambiguity_detection(mock_retailers):
    # 'Gupta' is ambiguous between 'Gupta Dairy' and 'Gupta Milk Center'
    m, amb, _ = match_retailer("Gupta 20 buffalo", mock_retailers)
    assert m is None  # Never silently guess!
    assert amb is not None
    assert len(amb.candidates) >= 2
    cand_ids = {c.id for c in amb.candidates}
    assert 1 in cand_ids and 3 in cand_ids


def test_category_matching(mock_categories):
    # Buffalo match
    c1, conf1 = match_category("20 mahis", mock_categories)
    assert c1 is not None and c1["id"] == 1

    # Cow match in Devanagari
    c2, conf2 = match_category("पन्नास गाय", mock_categories)
    assert c2 is not None and c2["id"] == 2

    # Chaas match
    c3, conf3 = match_category("taak 10 packet", mock_categories)
    assert c3 is not None and c3["id"] == 3


def test_distributor_matching(mock_distributors):
    d1, amb1, conf1 = match_distributor("purchase sangam dairy 500 buffalo", mock_distributors)
    assert d1 is not None and d1["id"] == 1
    assert amb1 is None


# ============================================================
# 4. COMMAND PARSER & SAFETY RULES TESTS
# ============================================================

def test_command_parser_retailer_sale(mock_retailers, mock_categories):
    draft = parse_command("20 buffalo patel milk agency", mock_retailers, mock_categories)
    assert draft.is_valid_draft is True
    assert draft.intent == IntentType.RETAILER_SALE
    assert isinstance(draft.command, SaleCommand)
    assert draft.command.retailer_id == 4
    assert len(draft.command.items) == 1
    assert draft.command.items[0].qty == 20.0
    assert draft.command.items[0].category_id == 1
    # STRICT RATE PROTECTION: AI must NEVER guess or calculate rate!
    assert draft.command.items[0].rate is None


def test_command_parser_missing_quantity_rejection(mock_retailers, mock_categories):
    # Customer and category specified, but NO quantity!
    draft = parse_command("patel milk agency buffalo", mock_retailers, mock_categories)
    assert draft.is_valid_draft is False
    assert any("quantity missing" in m.lower() for m in draft.missing_fields)


def test_command_parser_missing_amount_payment_rejection(mock_retailers, mock_categories):
    # Customer specified payment, but NO amount!
    draft = parse_command("patel milk agency payment", mock_retailers, mock_categories)
    assert draft.is_valid_draft is False
    assert any("amount missing" in m.lower() for m in draft.missing_fields)


def test_command_parser_route_expense(mock_retailers, mock_categories):
    draft = parse_command("खर्च डिझेल 500 रुपये कैश", mock_retailers, mock_categories)
    assert draft.is_valid_draft is True
    assert draft.intent == IntentType.ROUTE_EXPENSE
    assert isinstance(draft.command, ExpenseCommand)
    assert draft.command.category == "Fuel"
    assert draft.command.amount == 500.0
    assert draft.command.payment_mode == "Cash"


def test_command_parser_empty_and_graceful_failure(mock_retailers, mock_categories):
    draft1 = parse_command("", mock_retailers, mock_categories)
    assert draft1.is_valid_draft is False

    draft2 = parse_command("   ", mock_retailers, mock_categories)
    assert draft2.is_valid_draft is False

    # Non-existent customer
    draft3 = parse_command("unknown customer 20 buffalo", mock_retailers, mock_categories)
    assert draft3.is_valid_draft is False
    assert any("missing or not found" in m.lower() for m in draft3.missing_fields)


if __name__ == "__main__":
    print("\n=======================================================")
    print("RUNNING STAGE 1 INTELLIGENCE LAYER UNIT TESTS")
    print("=======================================================")
    test_number_parser_digits_and_english()
    print("  [PASS] Number Parser (Digits & English): PASS")
    test_number_parser_marathi_devanagari()
    print("  [PASS] Number Parser (Marathi Devanagari): PASS")
    test_number_parser_marathi_romanized()
    print("  [PASS] Number Parser (Marathi Romanized): PASS")
    test_number_parser_fractions_and_modifiers()
    print("  [PASS] Number Parser (Fractions & Modifiers): PASS")
    test_intent_classification()
    print("  [PASS] Intent Classification & Mode Locking: PASS")
    test_phonetic_normalization()
    print("  [PASS] Phonetic Normalization & Transliteration: PASS")

    # Run entity resolution with fixtures
    rets = pd.DataFrame([
        {"retailer_id": 1, "name": "Gupta Dairy", "zone": "Route 1"},
        {"retailer_id": 2, "name": "Laxmi Dairy", "zone": "Route 2"},
        {"retailer_id": 3, "name": "Gupta Milk Center", "zone": "Route 1"},
        {"retailer_id": 4, "name": "Patel Milk Agency", "zone": "Route 3"},
    ])
    cats = pd.DataFrame([
        {"category_id": 1, "name": "Buffalo"},
        {"category_id": 2, "name": "Cow"},
        {"category_id": 3, "name": "Amul Chaas"},
    ])
    dists = pd.DataFrame([
        {"distributor_id": 1, "name": "Sangam Dairy"},
        {"distributor_id": 2, "name": "Warna Dairy"},
    ])

    test_retailer_matching_exact_and_phonetic(rets)
    print("  [PASS] Retailer Matching (Exact & Phonetic): PASS")
    test_retailer_ambiguity_detection(rets)
    print("  [PASS] Retailer Ambiguity Detection (No Blind Guessing): PASS")
    test_category_matching(cats)
    print("  [PASS] Milk Category Matching: PASS")
    test_distributor_matching(dists)
    print("  [PASS] Distributor Matching: PASS")
    test_command_parser_retailer_sale(rets, cats)
    print("  [PASS] Command Parser (Sale & Rate Protection): PASS")
    test_command_parser_missing_quantity_rejection(rets, cats)
    print("  [PASS] Missing Quantity Incomplete Rejection: PASS")
    test_command_parser_missing_amount_payment_rejection(rets, cats)
    print("  [PASS] Missing Payment Amount Incomplete Rejection: PASS")
    test_command_parser_route_expense(rets, cats)
    print("  [PASS] Route Expense Parsing: PASS")
    test_command_parser_empty_and_graceful_failure(rets, cats)
    print("  [PASS] Graceful Fallback on Malformed/Empty Input: PASS")

    print("=======================================================")
    print("ALL STAGE 1 TESTS PASSED WITH 100% SUCCESS!")
    print("=======================================================")
