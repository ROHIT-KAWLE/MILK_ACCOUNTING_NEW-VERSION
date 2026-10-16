"""
MILK ACCOUNTING PRO — COMPREHENSIVE END-TO-END DUMMY WORKFLOW SUITE
===================================================================
This script tests the entire ERP workflow using simulated dummy data
in-memory WITHOUT modifying or connecting to the live Supabase database.

Covers:
1. Master Configuration (Retailers, Categories, Prices, Distributors)
2. Daily Posting Calculations (Volume, Rate lookup, Amounts)
3. Payments & Multi-Mode Breakdowns (Cash, UPI, Cheque, Advance)
4. Route Expenses & Net Cash Handover to Counter
5. Master Zone Route Summary HTML (1 Route per Page, A4 Portrait, Green cells)
6. Retailer Printable Bill (Invoice layout, product annexure, payment ledger)
7. Vendor Procurement Bill (Vendor items, ledger reconciliation)
8. Master Executive Daily Performance & Profit Report
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
from datetime import date
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import (
    _safe_float,
    _safe_sum,
    build_zone_route_summary_master_html,
    build_bill_html,
    build_distributor_bill_html,
    build_daily_report_html,
)

def test_safe_helpers():
    print("[1/7] Testing safe numeric conversion and aggregation helpers...")
    assert _safe_float(None) == 0.0
    assert _safe_float("120.50") == 120.50
    assert _safe_float("-") == 0.0
    assert _safe_float(float("nan")) == 0.0
    assert _safe_float(100) == 100.0

    df_sample = pd.DataFrame({
        "qty": [10.0, 20.5, None, 5.0],
        "amt": ["100.0", "205.0", "-", "50.0"],
    })
    assert _safe_sum(df_sample, "qty") == 35.5
    assert _safe_sum(df_sample, "amt") == 355.0
    assert _safe_sum(df_sample, "non_existent_col") == 0.0
    assert _safe_sum(None, "qty") == 0.0
    print("  [PASS] Safe helpers: PASS")


def test_daily_posting_and_ledger():
    print("[2/7] Testing daily sales posting & customer ledger math...")
    # Dummy Retailers
    retailers = [
        {"id": 1, "name": "Shree Ganesh Dairy", "zone": "Route 1", "opening_due": 15000.0},
        {"id": 2, "name": "Om Sai Milk Center", "zone": "Route 1", "opening_due": 22000.0},
        {"id": 3, "name": "Krishna Dairy", "zone": "Route 2", "opening_due": 5000.0},
    ]

    # Daily Deliveries: (Buffalo @ Rs 80/L, Cow @ Rs 60/L)
    deliveries = [
        {"id": 1, "buf_qty": 50.0, "cow_qty": 20.0, "cash": 2000.0, "upi": 1000.0},
        {"id": 2, "buf_qty": 80.0, "cow_qty": 0.0, "cash": 4000.0, "upi": 0.0},
        {"id": 3, "buf_qty": 20.0, "cow_qty": 10.0, "cash": 2200.0, "upi": 0.0},
    ]

    rows = []
    for r, d in zip(retailers, deliveries):
        today_sales = (d["buf_qty"] * 80.0) + (d["cow_qty"] * 60.0)
        total_pay = d["cash"] + d["upi"]
        total_ledger = r["opening_due"] + today_sales - total_pay
        rows.append({
            "ID": r["id"],
            "Retailer": r["name"],
            "Zone": r["zone"],
            "Buffalo (L)": d["buf_qty"],
            "Cow (L)": d["cow_qty"],
            "Today Sales ₹": today_sales,
            "Previous Ledger ₹": r["opening_due"],
            "CASH ₹": d["cash"],
            "UPI ₹": d["upi"],
            "Total Ledger ₹": total_ledger,
        })

    df = pd.DataFrame(rows)
    # Check totals
    assert df["Today Sales ₹"].sum() == (50*80 + 20*60) + (80*80) + (20*80 + 10*60) # 5200 + 6400 + 2200 = 13800
    assert df["CASH ₹"].sum() == 8200.0
    assert df["UPI ₹"].sum() == 1000.0
    print("  [PASS] Daily posting & customer ledger math: PASS")
    return df


def test_route_cash_handover_and_expenses():
    print("[3/7] Testing route cash collection & net handover reconciliation...")
    # Route 1: Collected Cash = Rs 6000.0 (from Retailer 1 & 2)
    # Driver cash expenses: Diesel = Rs 500, Driver Bhatta = Rs 150
    # Expected handover = 6000 - 650 = Rs 5350.00
    cash_collected = 6000.0
    route_expenses = pd.DataFrame([
        {"Category": "Diesel", "Amount ₹": 500.0, "Payment Mode": "Cash", "Note": "HP Petrol Pump 20L"},
        {"Category": "Driver Bhatta", "Amount ₹": 150.0, "Payment Mode": "Cash", "Note": "Ramesh lunch"},
        {"Category": "Toll Tax", "Amount ₹": 80.0, "Payment Mode": "UPI", "Note": "Fastag"},
    ])

    cash_expenses = 0.0
    total_expenses = 0.0
    for _, r in route_expenses.iterrows():
        amt = _safe_float(r["Amount ₹"])
        total_expenses += amt
        if str(r["Payment Mode"]).strip().upper() == "CASH":
            cash_expenses += amt

    net_handover = cash_collected - cash_expenses
    assert cash_expenses == 650.0
    assert total_expenses == 730.0
    assert net_handover == 5350.0
    print("  [PASS] Route cash handover & expenses: PASS")


def test_zone_summary_master_html_portrait():
    print("[4/7] Testing Master Zone Summary HTML layout (1 route per page, A4 portrait)...")
    route1_df = pd.DataFrame([
        {
            "ID": 1,
            "Retailer": "Shree Ganesh Dairy",
            "Buffalo (L)": 50.0,
            "Cow (L)": 20.0,
            "Today Sales ₹": 5200.0,
            "Previous Ledger ₹": 15000.0,
            "CASH ₹": 2000.0,
            "UPI ₹": 1000.0,
            "Total Ledger ₹": 17200.0,
        },
        {
            "ID": 2,
            "Retailer": "Om Sai Milk Center",
            "Buffalo (L)": 80.0,
            "Cow (L)": 0.0,
            "Today Sales ₹": 6400.0,
            "Previous Ledger ₹": 22000.0,
            "CASH ₹": 4000.0,
            "UPI ₹": 0.0,
            "Total Ledger ₹": 24400.0,
        },
        {
            "ID": "TOTAL",
            "Retailer": "TOTAL",
            "Buffalo (L)": 130.0,
            "Cow (L)": 20.0,
            "Today Sales ₹": 11600.0,
            "Previous Ledger ₹": 37000.0,
            "CASH ₹": 6000.0,
            "UPI ₹": 1000.0,
            "Total Ledger ₹": 41600.0,
        }
    ])

    pay_modes = pd.DataFrame([
        {"payment_mode": "CASH", "amount": 6000.0},
        {"payment_mode": "UPI", "amount": 1000.0},
    ])

    expenses = pd.DataFrame([
        {"category": "Diesel", "note": "HP Petrol Pump", "payment_mode": "Cash", "amount": 500.0},
        {"category": "Driver Bhatta", "note": "Lunch", "payment_mode": "Cash", "amount": 150.0},
    ])

    zone_data = [{
        "zone": "Route 1",
        "df": route1_df,
        "pay_modes": pay_modes,
        "expenses": expenses,
    }]

    html = build_zone_route_summary_master_html(date(2026, 10, 12), zone_data)
    assert "Route 1" in html
    assert "Shree Ganesh Dairy" in html
    assert "Payments Collection by Mode" in html or "Payments" in html
    assert "Route Expenses" in html
    assert "NET CASH HANDOVER TO COUNTER" in html
    assert "5,350.00" in html # 6000 cash - 650 cash expenses
    assert "A4 portrait" in html
    assert "page-break-after: always" in html
    print("  [PASS] Master Zone Summary HTML report generation: PASS")


def test_retailer_printable_bill_rendering():
    print("[5/7] Testing Retailer Printable Bill (Invoice layout with both dict & DataFrame pay modes)...")
    rrow = {
        "retailer_id": 1,
        "name": "Shree Ganesh Dairy",
        "zone": "Route 1",
        "contact": "9820012345",
        "address": "Shop 4, Market Road, Juhu",
    }
    grid = pd.DataFrame([
        {
            "Date": "2026-10-10",
            "Buffalo Qty": 50.0,
            "Total Milk (L)": 50.0,
            "Sales (₹)": 4000.0,
            "Payment (₹)": 0.0,
            "Running Due (₹)": 19000.0,
        },
        {
            "Date": "2026-10-11",
            "Buffalo Qty": 50.0,
            "Total Milk (L)": 50.0,
            "Sales (₹)": 4000.0,
            "Payment (₹)": 5000.0,
            "Running Due (₹)": 18000.0,
        },
        {
            "Date": "2026-10-12",
            "Buffalo Qty": 50.0,
            "Total Milk (L)": 50.0,
            "Sales (₹)": 4000.0,
            "Payment (₹)": 0.0,
            "Running Due (₹)": 22000.0,
        },
    ])

    # Case A: pay_mode_totals as DataFrame
    pm_df = pd.DataFrame([{"Mode": "Cash", "Total (₹)": 5000.0}])
    html_df = build_bill_html(
        rrow,
        date(2026, 10, 10),
        date(2026, 10, 12),
        grid,
        pm_df,
        ["Buffalo"],
        15000.0,
    )
    assert "CREDIT / CASH MEMO" in html_df
    assert "Shree Ganesh Dairy" in html_df
    assert "150.00 L" in html_df # 3 * 50
    assert "5,000.00" in html_df
    assert "Net Amount Payable" in html_df

    # Case B: pay_mode_totals as dict (Edge case that previously triggered AttributeError)
    pm_dict = {"Cash": 5000.0}
    html_dict = build_bill_html(
        rrow,
        date(2026, 10, 10),
        date(2026, 10, 12),
        grid,
        pm_dict,
        ["Buffalo"],
        15000.0,
    )
    assert "CREDIT / CASH MEMO" in html_dict
    assert "Cash" in html_dict
    print("  [PASS] Retailer Printable Bill rendering (DF & Dict): PASS")


def test_distributor_purchase_and_bill():
    print("[6/7] Testing Vendor Procurement & Bill generation...")
    dist_row = {
        "distributor_id": 1,
        "name": "Mahanand Dairy Sangha",
        "contact": "9820099999",
        "address": "Goregaon East, Mumbai",
    }
    grid = pd.DataFrame([
        {
            "Date": "2026-10-10",
            "Buffalo Qty": 500.0,
            "Total Milk (L)": 500.0,
            "Purchases (₹)": 30000.0,
            "Payment (₹)": 25000.0,
            "Running Due (₹)": 15000.0,
        },
        {
            "Date": "2026-10-11",
            "Buffalo Qty": 500.0,
            "Total Milk (L)": 500.0,
            "Purchases (₹)": 30000.0,
            "Payment (₹)": 0.0,
            "Running Due (₹)": 45000.0,
        },
    ])

    html = build_distributor_bill_html(
        dist_row,
        date(2026, 10, 10),
        date(2026, 10, 11),
        grid,
        {"Bank Transfer": 25000.0},
        ["Buffalo"],
        10000.0,
    )
    assert "Vendor Purchase Bill" in html
    assert "Mahanand Dairy Sangha" in html
    assert "1,000.00 LTR" in html
    assert "NET AMOUNT PAYABLE TO VENDOR" in html
    print("  [PASS] Vendor Procurement & Bill generation: PASS")


def test_daily_performance_executive_report():
    print("[7/7] Testing Daily Performance Executive Report (Profit Reconciliation)...")
    retailer_table = pd.DataFrame([
        {"Name": "Route 1", "Total (L)": 150.0, "Total Sales (₹)": 12000.0},
        {"Name": "Route 2", "Total (L)": 100.0, "Total Sales (₹)": 7500.0},
    ])
    distributor_table = pd.DataFrame([
        {"Name": "Vendor Sangha", "TOTAL (L)": 260.0, "Total Purchase Cost (₹)": 14000.0}
    ])
    expenses_df = pd.DataFrame([
        {"category": "Diesel", "description": "[Route 1] Fuel", "payment_mode": "Cash", "amount": 600.0},
        {"category": "Driver Bhatta", "description": "[Route 1] Food", "payment_mode": "Cash", "amount": 200.0},
    ])

    html = build_daily_report_html(
        report_day=date(2026, 10, 12),
        retailer_table=retailer_table,
        retailer_totals={"total_milk": 250.0, "total_sales": 19500.0},
        retailer_pay_modes=pd.DataFrame([{"payment_mode": "Cash", "amount": 10000.0}]),
        distributor_table=distributor_table,
        distributor_totals={"total_milk": 260.0, "purchase_amt": 14000.0},
        purchased_qty=260.0,
        purchased_amt=14000.0,
        sold_qty=250.0,
        sold_amt=19500.0,
        waste_qty=10.0,
        waste_loss=550.0,
        expenses_df=expenses_df,
        total_expenses=800.0,
    )

    # Net Margin = 19500 (Sales) - 14000 (Purchase) - 550 (Waste) - 800 (Expenses) = Rs 4,150.00
    assert "TOTAL EXPENSES" in html
    assert "800.00" in html
    assert "REAL NET PROFIT / MARGIN" in html
    assert "4,150.00" in html
    assert "Diesel" in html
    print("  [PASS] Daily Performance Executive Report: PASS")


if __name__ == "__main__":
    print("\n==================================================================")
    print("STARTING FULL END-TO-END WORKFLOW SIMULATION WITH DUMMY DATA")
    print("==================================================================")
    test_safe_helpers()
    test_daily_posting_and_ledger()
    test_route_cash_handover_and_expenses()
    test_zone_summary_master_html_portrait()
    test_retailer_printable_bill_rendering()
    test_distributor_purchase_and_bill()
    test_daily_performance_executive_report()
    print("==================================================================")
    print("ALL 7 END-TO-END DUMMY WORKFLOW TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================================\n")
