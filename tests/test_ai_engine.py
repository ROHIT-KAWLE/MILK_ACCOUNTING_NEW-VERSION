"""
TEST SUITE FOR MILK ACCOUNTING PRO — OFFLINE AI ENGINE
======================================================
Tests local customer habit profiling, category & volume anomaly detection,
driver cash reconciliation deficit warnings, and bilingual Marathi/English voice parsing.
"""

import sys
import os
from datetime import date
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_engine import (
    build_customer_habit_profiles,
    detect_grid_anomalies,
    parse_natural_voice_entry,
)


import pytest

@pytest.fixture
def sample_habits_and_categories():
    entries_sample = pd.DataFrame([
        {"date": "2026-10-01", "retailer_id": 1, "category_id": 1, "qty": 120.0},
        {"date": "2026-10-02", "retailer_id": 1, "category_id": 1, "qty": 125.0},
        {"date": "2026-10-03", "retailer_id": 1, "category_id": 1, "qty": 118.0},
        {"date": "2026-10-04", "retailer_id": 1, "category_id": 1, "qty": 122.0},
        {"date": "2026-10-05", "retailer_id": 1, "category_id": 1, "qty": 120.0},
        # Retailer 2 takes only Cow (CID: 2)
        {"date": "2026-10-01", "retailer_id": 2, "category_id": 2, "qty": 20.0},
        {"date": "2026-10-02", "retailer_id": 2, "category_id": 2, "qty": 22.0},
        {"date": "2026-10-03", "retailer_id": 2, "category_id": 2, "qty": 19.0},
        {"date": "2026-10-04", "retailer_id": 2, "category_id": 2, "qty": 21.0},
        {"date": "2026-10-05", "retailer_id": 2, "category_id": 2, "qty": 20.0},
    ])
    retailers_sample = pd.DataFrame([
        {"retailer_id": 1, "name": "Gupta Dairy", "zone": "Route 1"},
        {"retailer_id": 2, "name": "Laxmi Dairy", "zone": "Route 1"},
    ])
    categories_sample = pd.DataFrame([
        {"category_id": 1, "name": "Buffalo"},
        {"category_id": 2, "name": "Cow"},
    ])
    habits = build_customer_habit_profiles(entries_sample, retailers_sample, categories_sample)
    return habits, categories_sample


def test_customer_habit_learning(sample_habits_and_categories):
    print("[1/4] Testing offline customer habit profiling...")
    habits, categories_sample = sample_habits_and_categories
    assert 1 in habits
    assert 2 in habits
    # Retailer 1 only has Category 1 (Buffalo)
    assert habits[1]["frequent_category_ids"] == {1}
    assert 120.0 <= habits[1]["category_stats"][1]["mean"] <= 122.0

    # Retailer 2 only has Category 2 (Cow)
    assert habits[2]["frequent_category_ids"] == {2}
    print("  [PASS] Customer habit profiling: PASS")


def test_anomaly_detection(sample_habits_and_categories):
    print("[2/4] Testing local multi-factor anomaly detection...")
    habits, categories_sample = sample_habits_and_categories
    # Today's draft grid with 2 intentional anomalies:
    # 1. Gupta Dairy (normally only Buffalo) is mistakenly entered with 40L Cow!
    # 2. Laxmi Dairy (normally 20L Cow) has a typo: 200L Cow (10x spike)!
    draft_grid = pd.DataFrame([
        {
            "ID": 1,
            "Retailer": "Gupta Dairy",
            "CID:1 — Buffalo Qty": 120.0,
            "CID:2 — Cow Qty": 40.0,  # <-- ANOMALY: Category mismatch
            "CASH ₹": 5000.0,
        },
        {
            "ID": 2,
            "Retailer": "Laxmi Dairy",
            "CID:1 — Buffalo Qty": 0.0,
            "CID:2 — Cow Qty": 200.0,  # <-- ANOMALY: 10x volume spike
            "CASH ₹": 0.0,
        },
    ])

    anomalies = detect_grid_anomalies(
        draft_df=draft_grid,
        posting_date=date(2026, 10, 12),
        posting_zone="Route 1",
        habit_profiles=habits,
        categories_df=categories_sample,
    )

    types_found = {a["type"] for a in anomalies}
    assert "CATEGORY_MISMATCH" in types_found
    assert "VOLUME_SPIKE" in types_found

    # Verify bilingual explanations are generated
    for a in anomalies:
        assert len(a["msg_en"]) > 0
        assert len(a["msg_mr"]) > 0
        assert len(a["recommendation_en"]) > 0
        assert len(a["recommendation_mr"]) > 0

    print("  [PASS] Category Mismatch & Volume Spike Anomaly Detection: PASS")


def test_driver_cash_shortfall_anomaly():
    print("[3/4] Testing driver cash shortfall reconciliation anomaly...")
    expenses_df = pd.DataFrame([
        {"category": "Fuel", "amount": 2500.0, "payment_mode": "Cash", "note": "Diesel"},
    ])
    # Driver only collected 2000 cash, but spent 2500 cash -> negative expected handover
    pay_mode_totals = {"Cash": 2000.0}
    anomalies = detect_grid_anomalies(
        draft_df=pd.DataFrame([{"ID": 1, "Retailer": "Dummy"}]),
        posting_date=date(2026, 10, 12),
        posting_zone="Route 1",
        habit_profiles={},
        categories_df=pd.DataFrame(),
        expenses_df=expenses_df,
        pay_mode_totals=pay_mode_totals,
    )
    deficit_anomalies = [a for a in anomalies if a["type"] == "DRIVER_CASH_DEFICIT"]
    assert len(deficit_anomalies) == 1
    assert deficit_anomalies[0]["severity"] == "CRITICAL"
    print("  [PASS] Driver cash shortfall anomaly: PASS")


def test_marathi_english_natural_voice_parsing():
    print("[4/4] Testing Marathi & English voice entry NLP parser...")
    retailers = pd.DataFrame([
        {"retailer_id": 1, "name": "Gupta Dairy", "zone": "Route 1"},
        {"retailer_id": 2, "name": "Laxmi Dairy", "zone": "Route 2"},
    ])
    categories = pd.DataFrame([
        {"category_id": 1, "name": "Buffalo"},
        {"category_id": 2, "name": "Cow"},
    ])

    # Case 1: Colloquial Marathlish voice phrase
    phrase1 = "vis mahis gupta dairy payment pach hazaar cash"
    res1 = parse_natural_voice_entry(phrase1, retailers, categories)
    assert res1["retailer_id"] == 1
    assert len(res1["items"]) == 1
    assert res1["items"][0]["qty"] == 20.0
    assert res1["items"][0]["category_name"] == "Buffalo"
    assert res1["payment"]["amount"] == 5000.0
    assert res1["payment"]["mode"] == "Cash"

    # Case 2: English voice phrase
    phrase2 = "20 buffalo gupta dairy payment 5000 cash"
    res2 = parse_natural_voice_entry(phrase2, retailers, categories)
    assert res2["retailer_id"] == 1
    assert res2["items"][0]["qty"] == 20.0
    assert res2["payment"]["amount"] == 5000.0

    # Case 3: Devanagari script voice input
    phrase3 = "पन्नास गाय लक्ष्मी डेअरी रोख तीन हजार"
    res3 = parse_natural_voice_entry(phrase3, retailers, categories)
    assert res3["retailer_id"] == 2
    assert res3["items"][0]["qty"] == 50.0
    assert res3["items"][0]["category_name"] == "Cow"
    assert res3["payment"]["amount"] == 3000.0
    assert res3["payment"]["mode"] == "Cash"

    print("  [PASS] Marathi & English Voice Parser: PASS")


if __name__ == "__main__":
    print("\n=======================================================")
    print("RUNNING AI ENGINE & ANOMALY DETECTOR TESTS")
    print("=======================================================")
    habits, cats = test_customer_habit_learning()
    test_anomaly_detection(habits, cats)
    test_driver_cash_shortfall_anomaly()
    test_marathi_english_natural_voice_parsing()
    print("=======================================================")
    print("ALL AI ENGINE & ANOMALY DETECTOR TESTS PASSED (100%)!")
    print("=======================================================\n")
