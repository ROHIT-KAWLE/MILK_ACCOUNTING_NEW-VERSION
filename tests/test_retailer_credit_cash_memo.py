import os
import sys
import pandas as pd
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import build_bill_html

def test_credit_cash_memo_structure():
    retailer_row = {
        'name': 'Gupta Dairy',
        'retailer_id': 12,
        'zone': 'Route 1',
        'contact': '9876543210',
        'address': 'Gulmohar Road, Juhu'
    }
    # Grid with BOTH Buffalo and Cow milk taken
    grid = pd.DataFrame([
        {'Date': '2026-10-01', 'Buffalo Qty': 100.0, 'Cow Qty': 20.0, 'Sales (₹)': 8040.0, 'Payment (₹)': 0.0},
        {'Date': '2026-10-02', 'Buffalo Qty': 120.0, 'Cow Qty': '-', 'Sales (₹)': 8400.0, 'Payment (₹)': 5000.0},
    ])
    pay_modes = pd.DataFrame([{'Mode': 'Cash', 'Total (₹)': 5000.0}])

    html = build_bill_html(
        retailer_row=retailer_row,
        start_day=date(2026, 10, 1),
        end_day=date(2026, 10, 2),
        grid=grid,
        pay_mode_totals=pay_modes,
        cat_names=['Buffalo', 'Cow'],
        opening_due=1500.0
    )

    # 1. Header: Business name, address, updated contact 9987471568, FSSAI 21518020000478, CREDIT / CASH MEMO
    assert "RANJIT BHIMRAO KAWLE MILK SUPPLIER" in html
    assert "Wholesale Milk Supplier" in html
    assert "Kherwadi, Bandra East, Mumbai - 400051" in html
    assert "9987471568" in html
    assert "21518020000478" in html
    assert "CREDIT / CASH MEMO" in html
    assert "INVOICE" not in html
    
    # 2. Customer: starts with Shri
    assert "Shri Gupta Dairy" in html
    
    # 3. Unique deterministic memo number format: CCM/{FY}/{RID}-{Month}{StartDay}{EndDay}
    assert "01/10/2026" in html and "02/10/2026" in html
    assert "CCM/26-27/012-100102" in html
    assert "(Ref: CCM" not in html
    assert "Memo Date:" in html
    assert "Billing Period:" in html
    
    # 4. Both categories taken by retailer appear (Buffalo and Cow), no NaN poison
    assert "Buffalo (L)" in html
    assert "Cow (L)" in html
    
    # 5. Rate column is REMOVED as requested
    assert "<th>Rate (₹)</th>" not in html
    assert "Rate (₹)" not in html
    
    # 6. Optional 2 empty columns (double width) + Dedicated Payment column + Toggle button
    assert 'class="fat-snf-col"' in html
    assert "Toggle FAT &amp; SNF Columns" in html
    assert ">FAT</th>" in html
    assert ">SNF</th>" in html
    assert "Payment (₹)" in html
    assert "Total Cost of Milk (₹)" in html
    
    # Test show_empty_cols=False
    html_no_cols = build_bill_html(
        retailer_row=retailer_row,
        start_day=date(2026, 10, 1),
        end_day=date(2026, 10, 2),
        grid=grid,
        pay_mode_totals=pay_modes,
        cat_names=['Buffalo', 'Cow'],
        opening_due=1500.0,
        show_empty_cols=False
    )
    assert 'display:none;' in html_no_cols
    
    # 7. Bank Details card REMOVED & Outer Outline Border present
    assert "635301010050021" not in html
    assert "UBIN0563536" not in html
    assert "bill-page-wrapper" in html
    
    # 8. Financial breakdown: settlement table on left, net amount in words on right (Gross Total Payable removed)
    assert "Opening Balance:" in html
    assert "Current Period Sales:" in html
    assert "Gross Total Payable:" not in html
    assert "Less: Payments Received:" in html
    assert "Net Amount Payable:" in html
    assert "Net Amount Payable in Words:" in html
    
    # Math: Sales = 8040 + 8400 = 16440. Opening = 1500. Paid = 5000. Closing = 12940.
    assert "16,440.00" in html
    assert "1,500.00" in html
    assert "5,000.00" in html
    assert "12,940.00" in html
    
    # 9. Proper Signature Lines, Terms Removed, Thanking Message & Print
    assert "sign-line" in html
    assert "Customer / Receiver Signature" in html
    assert "For <b>RANJIT BHIMRAO KAWLE MILK SUPPLIER</b>" in html
    assert "Terms & Instructions" not in html
    assert "Thank You for Your Business!" in html
    assert "@page" in html
    assert "A4 portrait" in html

if __name__ == "__main__":
    test_credit_cash_memo_structure()
    print("ALL TESTS PASSED!")

