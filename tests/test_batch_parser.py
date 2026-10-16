"""Unit tests for Multi-Transaction Continuous Batch Parser."""

import os
import sys
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ai.parser.batch_parser import (
    split_continuous_stream,
    parse_continuous_batch,
    apply_batch_to_daily_grid,
)


def test_continuous_splitting():
    print("[1/4] Testing stream splitting...")
    text = "गुप्ता डेअरी २० म्हैस रोख ५०००, साई डेअरी १० गाय आणि लक्ष्मी डेअरी ३० म्हैस १०००० जमा. डिझेल १५०० रोख"
    parts = split_continuous_stream(text)
    assert len(parts) >= 4
    print("  [PASS] Stream splitting: PASS")


def test_batch_multi_customer_parsing():
    print("[2/4] Testing batch multi-customer resolution...")
    retailers_df = pd.DataFrame([
        {"id": 101, "name": "Gulmohar Dairy", "marathi_name": "गुलमोहर डेअरी", "route_code": "R1"},
        {"id": 102, "name": "Laxmi Dairy", "marathi_name": "लक्ष्मी डेअरी", "route_code": "R1"},
        {"id": 103, "name": "Sai Dairy", "marathi_name": "साई डेअरी", "route_code": "R1"},
    ])
    categories_df = pd.DataFrame([
        {"id": 1, "name": "Buffalo", "marathi_name": "म्हैस", "display_order": 1},
        {"id": 2, "name": "Cow", "marathi_name": "गाय", "display_order": 2},
    ])

    continuous_text = (
        "गुलमोहर डेअरी २० म्हैस रोख ५०००, "
        "लक्ष्मी डेअरी १० गाय, "
        "साई डेअरी ३० म्हैस रोख १००००, "
        "डिझेल १५०० रोख"
    )

    batch_res = parse_continuous_batch(
        continuous_text,
        retailers_df=retailers_df,
        categories_df=categories_df,
        active_zone="R1",
    )

    assert len(batch_res.sales) == 3
    assert len(batch_res.expenses) == 1

    # Check first sale (Gulmohar Dairy)
    s1 = next(s for s in batch_res.sales if s.retailer_id == 101)
    assert s1.items[0].qty == 20.0
    assert s1.items[0].category_id == 1
    assert s1.cash_payment == 5000.0

    # Check second sale (Laxmi Dairy)
    s2 = next(s for s in batch_res.sales if s.retailer_id == 102)
    assert s2.items[0].qty == 10.0
    assert s2.items[0].category_id == 2
    assert s2.cash_payment == 0.0

    # Check third sale (Sai Dairy)
    s3 = next(s for s in batch_res.sales if s.retailer_id == 103)
    assert s3.items[0].qty == 30.0
    assert s3.cash_payment == 10000.0

    # Check expense (Fuel)
    e = batch_res.expenses[0]
    assert e.category == "Fuel"
    assert e.amount == 1500.0
    print("  [PASS] Batch multi-customer resolution: PASS")


def test_grid_auto_fill():
    print("[3/4] Testing in-memory grid population...")
    retailers_df = pd.DataFrame([
        {"id": 101, "name": "Gulmohar Dairy", "marathi_name": "गुलमोहर डेअरी", "route_code": "R1"},
        {"id": 102, "name": "Laxmi Dairy", "marathi_name": "लक्ष्मी डेअरी", "route_code": "R1"},
    ])
    categories_df = pd.DataFrame([
        {"id": 1, "name": "Buffalo", "marathi_name": "म्हैस", "display_order": 1},
        {"id": 2, "name": "Cow", "marathi_name": "गाय", "display_order": 2},
    ])

    # Initial daily draft table with zeros
    draft_df = pd.DataFrame([
        {"ID": 101, "Retailer": "Gulmohar Dairy", "CID:1 — Buffalo": 0.0, "CID:2 — Cow": 0.0, "CASH ₹": 0.0},
        {"ID": 102, "Retailer": "Laxmi Dairy", "CID:1 — Buffalo": 0.0, "CID:2 — Cow": 0.0, "CASH ₹": 0.0},
        {"ID": 103, "Retailer": "Other Dairy", "CID:1 — Buffalo": 0.0, "CID:2 — Cow": 0.0, "CASH ₹": 0.0},
    ])
    cat_cols = [
        {"id": 1, "col": "CID:1 — Buffalo"},
        {"id": 2, "col": "CID:2 — Cow"},
    ]

    continuous_text = "गुलमोहर डेअरी २५ म्हैस रोख ४०००, लक्ष्मी डेअरी १५ गाय"
    batch_res = parse_continuous_batch(continuous_text, retailers_df, categories_df)

    updated_df, modified_ids = apply_batch_to_daily_grid(batch_res, draft_df, cat_cols)

    assert 101 in modified_ids
    assert 102 in modified_ids
    assert 103 not in modified_ids

    # Check Gulmohar row
    r1 = updated_df[updated_df["ID"] == 101].iloc[0]
    assert r1["CID:1 — Buffalo"] == 25.0
    assert r1["CASH ₹"] == 4000.0

    # Check Laxmi row
    r2 = updated_df[updated_df["ID"] == 102].iloc[0]
    assert r2["CID:2 — Cow"] == 15.0

    # Check untouched row
    r3 = updated_df[updated_df["ID"] == 103].iloc[0]
    assert r3["CID:1 — Buffalo"] == 0.0
    print("  [PASS] In-memory grid population: PASS")


def test_fault_tolerant_unmatched():
    print("[4/4] Testing fault tolerance on noisy phrases...")
    retailers_df = pd.DataFrame([{"id": 101, "name": "Gulmohar Dairy", "marathi_name": "गुलमोहर डेअरी"}])
    categories_df = pd.DataFrame([{"id": 1, "name": "Buffalo", "marathi_name": "म्हैस"}])

    mixed_text = "गुलमोहर डेअरी २० म्हैस, अरे काहीतरी विचित्र शब्द, डिझेल ५००"
    batch_res = parse_continuous_batch(mixed_text, retailers_df, categories_df)
    assert len(batch_res.sales) == 1
    assert len(batch_res.expenses) == 1
    assert len(batch_res.unmatched_segments) >= 1
    print("  [PASS] Fault tolerance on noisy phrases: PASS")


def test_driver_cash_reconciliation_math():
    print("[5/5] Testing driver advance cash reconciliation equation...")
    retailers_df = pd.DataFrame([
        {"id": 101, "name": "Gulmohar Dairy", "marathi_name": "गुलमोहर डेअरी"},
        {"id": 102, "name": "Sai Dairy", "marathi_name": "साई डेअरी"}
    ])
    categories_df = pd.DataFrame([{"id": 1, "name": "Buffalo", "marathi_name": "म्हैस"}])

    route_stream = "गुलमोहर डेअरी २० म्हैस रोख ५०००, साई डेअरी १० म्हैस रोख ३०००, डिझेल १५०० रोख, नाश्ता २०० रोख"
    batch_res = parse_continuous_batch(route_stream, retailers_df, categories_df)

    cash_collected = sum(s.cash_payment for s in batch_res.sales)
    assert cash_collected == 8000.0

    cash_expenses = sum(e.amount for e in batch_res.expenses if e.payment_mode == "Cash")
    assert cash_expenses == 1700.0

    # Advance cash given to driver before leaving depot
    driver_adv_cash = 2000.0

    # Equation: (Advance + Collected) - Expenses = Net Cash Handover
    tot_cash_with_driver = driver_adv_cash + cash_collected
    assert tot_cash_with_driver == 10000.0

    final_cash_to_return = tot_cash_with_driver - cash_expenses
    assert final_cash_to_return == 8300.0

    print("  [PASS] Driver advance cash reconciliation equation: PASS")


if __name__ == "__main__":
    print("\n=======================================================")
    print("RUNNING BATCH PARSER TESTS")
    print("=======================================================")
    test_continuous_splitting()
    test_batch_multi_customer_parsing()
    test_grid_auto_fill()
    test_fault_tolerant_unmatched()
    test_driver_cash_reconciliation_math()
    print("=======================================================")
    print("ALL BATCH PARSER TESTS PASSED 100%!")
    print("=======================================================\n")
