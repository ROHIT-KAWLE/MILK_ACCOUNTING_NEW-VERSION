import os
import sys
import pandas as pd
from datetime import date

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import (
    extract_expense_zone,
    clean_expense_note,
    build_zone_route_summary_master_html,
    build_daily_report_html,
)

def test_helpers():
    print("Testing expense helpers...")
    # 1. extract_expense_zone
    assert extract_expense_zone("[Route 1] Diesel 20L") == "Route 1"
    assert extract_expense_zone("[Route 2]") == "Route 2"
    assert extract_expense_zone("Office Rent", "Route 3 - Diesel") == "Route 3"
    assert extract_expense_zone("Office Electricity") is None
    
    # 2. clean_expense_note
    assert clean_expense_note("[Route 1] HP Petrol Pump 20L") == "HP Petrol Pump 20L"
    assert clean_expense_note("[Route 2]") == ""
    assert clean_expense_note("General note") == "General note"
    print("Expense helpers: PASS")

def test_zone_summary_master_html():
    print("Testing build_zone_route_summary_master_html...")
    # Create sample route data matching Zone_Summary_2026-10-12 (1).html
    sample_df = pd.DataFrame([
        {
            "ID": 1,
            "Retailer": "Gupta dairy (gulmohar road Juhu)",
            "CID:1 — Buffalo": 120.0,
            "CID:2 — Cow": 20.0,
            "CID:3 — Standard": 0.0,
            "Today Sales ₹": 9680.0,
            "Previous Ledger ₹": 968566.0,
            "CASH ₹": 0.0,
            "UPI ₹": 0.0,
            "CHEQUE ₹": 0.0,
            "Total Ledger ₹": 978246.0,
        },
        {
            "ID": 2,
            "Retailer": "Gupta milk center(ful market juhu)",
            "CID:1 — Buffalo": 160.0,
            "CID:2 — Cow": 0.0,
            "CID:3 — Standard": 0.0,
            "Today Sales ₹": 14560.0,
            "Previous Ledger ₹": 4137632.0,
            "CASH ₹": 6840.0,
            "UPI ₹": 0.0,
            "CHEQUE ₹": 0.0,
            "Total Ledger ₹": 4145352.0,
        },
        {
            "ID": "TOTAL",
            "Retailer": "TOTAL",
            "CID:1 — Buffalo": 280.0,
            "CID:2 — Cow": 20.0,
            "CID:3 — Standard": 0.0,
            "Today Sales ₹": 24240.0,
            "Previous Ledger ₹": 5106198.0,
            "CASH ₹": 6840.0,
            "UPI ₹": 0.0,
            "CHEQUE ₹": 0.0,
            "Total Ledger ₹": 5123598.0,
        }
    ])
    
    pay_modes = pd.DataFrame([
        {"payment_mode": "CASH", "amount": 6840.0}
    ])
    
    expenses = pd.DataFrame([
        {"category": "Diesel", "note": "HP pump 20L", "payment_mode": "Cash", "amount": 500.0},
        {"category": "Driver Bhatta", "note": "Ramesh lunch", "payment_mode": "Cash", "amount": 150.0},
        {"category": "Toll", "note": "Fastag", "payment_mode": "UPI", "amount": 80.0},
    ])
    
    zone_data = [{
        "zone": "Route 1",
        "df": sample_df,
        "pay_modes": pay_modes,
        "expenses": expenses,
    }]
    
    html = build_zone_route_summary_master_html(date(2026, 10, 12), zone_data)
    
    # Assertions on HTML content & styling
    assert "RANJIT BHIMRAO KAWLE MILK" in html
    assert "Zone Summary — Route 1" in html
    assert "Gupta dairy (gulmohar road Juhu)" in html
    # Check active data cell (120.00)
    assert "120.00" in html
    # Check Payments by Mode
    assert "Payments Collection by Mode" in html or "Payments by Mode" in html
    assert "6,840.00" in html or "6840.00" in html
    # Check Route Expenses
    assert "Route Expenses" in html
    assert "Diesel" in html
    assert "HP pump 20L" in html
    # Check Cash Handover reconciliation (6840 cash - 650 cash expenses = 6190 handover)
    assert "NET CASH HANDOVER TO COUNTER" in html
    assert "6,190.00" in html
    # Check print stylesheet
    assert "@page" in html
    assert "A4 portrait" in html
    
    print("Zone Summary HTML generation: PASS")

def test_daily_report_html_with_expenses():
    print("Testing build_daily_report_html with expenses...")
    retailer_table = pd.DataFrame([{"Name": "Route 1", "Total (L)": 280.0, "Total Sales (₹)": 24240.0}])
    distributor_table = pd.DataFrame([{"Name": "Vendor 1", "TOTAL (L)": 300.0, "Total Purchase Cost (₹)": 15000.0}])
    expenses_df = pd.DataFrame([
        {"category": "Diesel", "description": "[Route 1] Fuel", "payment_mode": "Cash", "amount": 500.0},
        {"category": "Office Rent", "description": "Godown rent", "payment_mode": "Bank", "amount": 2000.0},
    ])
    
    html = build_daily_report_html(
        report_day=date(2026, 10, 12),
        retailer_table=retailer_table,
        retailer_totals={"total_milk": 280.0, "total_sales": 24240.0},
        retailer_pay_modes=pd.DataFrame([{"payment_mode": "Cash", "amount": 6840.0}]),
        distributor_table=distributor_table,
        distributor_totals={"total_milk": 300.0, "purchase_amt": 15000.0},
        purchased_qty=300.0,
        purchased_amt=15000.0,
        sold_qty=280.0,
        sold_amt=24240.0,
        waste_qty=5.0,
        waste_loss=250.0,
        expenses_df=expenses_df,
        total_expenses=2500.0,
    )
    
    # Check net profit: 24240 - 15000 - 250 - 2500 = 6490.00
    assert "TOTAL EXPENSES" in html
    assert "2,500.00" in html
    assert "REAL NET PROFIT / MARGIN" in html
    assert "6,490.00" in html
    assert "Operating Expenses" in html
    assert "Office Rent" in html
    print("Daily Report HTML generation with expenses: PASS")

def test_save_route_expenses_records_logic():
    print("Testing save_route_expenses_records logic...")
    from unittest.mock import patch
    import app

    test_df = pd.DataFrame([
        {"Category": "Diesel", "Amount ₹": 750.0, "Payment Mode": "Cash", "Note": "HP petrol pump"},
        {"Category": "Driver Bhatta", "Amount ₹": 100.0, "Payment Mode": "Cash", "Note": "Lunch"},
    ])
    
    saved_records = []
    def mock_insert(df, path):
        saved_records.extend(df.to_dict(orient="records"))
        
    with patch.object(app, "sb_fetch_df", return_value=pd.DataFrame()):
        with patch.object(app, "sb_delete_by_pk", return_value=None):
            with patch.object(app, "sb_insert_df", side_effect=mock_insert):
                with patch.object(app, "invalidate_data_cache", return_value=None):
                    app.save_route_expenses_records(date(2026, 10, 12), "Route 1", test_df)

    assert len(saved_records) == 2
    assert saved_records[0]["category"] == "Diesel"
    assert saved_records[0]["amount"] == 750.0
    assert saved_records[0]["description"] == "[Route 1] HP petrol pump"
    assert saved_records[1]["category"] == "Driver Bhatta"
    assert saved_records[1]["amount"] == 100.0
    print("save_route_expenses_records: PASS")

if __name__ == "__main__":
    test_helpers()
    test_zone_summary_master_html()
    test_daily_report_html_with_expenses()
    test_save_route_expenses_records_logic()
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

