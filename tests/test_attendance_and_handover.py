import pandas as pd
from datetime import date
from app import (
    get_workers_df,
    get_attendance_records,
    save_attendance_matrix,
    get_attendance_date_locks,
    save_attendance_date_locks,
    build_bill_html,
)

def test_attendance_helpers_and_matrix_flow():
    # 1. Fetch default workers
    workers = get_workers_df()
    assert not workers.empty
    assert "name" in workers.columns
    assert "worker_id" in workers.columns
    
    # 2. Test saving and retrieving attendance date locks
    # Day 5 locked (False = locked/not editable), Day 10 editable (True)
    test_locks = {d: True for d in range(1, 32)}
    test_locks[5] = False
    save_attendance_date_locks(2026, 10, test_locks)
    
    loaded_locks = get_attendance_date_locks(2026, 10)
    assert loaded_locks[5] is False
    assert loaded_locks[10] is True
    
    # 3. Test saving attendance matrix with Full Day (P) and Half Day (HD)
    matrix_df = pd.DataFrame([
        {
            "worker_id": 1,
            "कामगार नाव (Name)": "Ramesh Yadav",
            "पद (Role)": "Driver",
            "1": "P",
            "2": "P",
            "3": "HD", # Half day
            "4": "-",  # Absent
            **{str(d): "P" for d in range(5, 32)}
        }
    ])
    save_attendance_matrix(2026, 10, matrix_df)
    
    records = get_attendance_records(2026, 10)
    assert not records.empty
    
    # Worker 1 Day 1: P, 1.0 unit
    w1_d1 = records[(records["worker_id"] == 1) & (records["date"] == "2026-10-01")]
    assert not w1_d1.empty
    assert w1_d1.iloc[0]["status"] == "P"
    assert float(w1_d1.iloc[0]["units"]) == 1.0
    
    # Worker 1 Day 3: HD, 0.5 unit
    w1_d3 = records[(records["worker_id"] == 1) & (records["date"] == "2026-10-03")]
    assert not w1_d3.empty
    assert w1_d3.iloc[0]["status"] == "HD"
    assert float(w1_d3.iloc[0]["units"]) == 0.5
    
    # Worker 1 Day 4: A, 0.0 unit
    w1_d4 = records[(records["worker_id"] == 1) & (records["date"] == "2026-10-04")]
    assert not w1_d4.empty
    assert w1_d4.iloc[0]["status"] == "A"
    assert float(w1_d4.iloc[0]["units"]) == 0.0

def test_route_cash_handover_deficit_calculation():
    # User's case:
    # Retailer cash collection = 5000.00
    # Driver cash expenses = 450.00
    # Advance given = 0.00
    # Expected handover = 5000 - 450 = 4550.00
    # Actual handover = 4500.00
    # Shortfall = 4500 - 4550 = -50.00 (Shortage / तूट of ₹50.00)
    r_cash_collected = 5000.00
    r_cash_expenses = 450.00
    driver_adv_cash = 0.00
    
    expected_handover = (driver_adv_cash + r_cash_collected) - r_cash_expenses
    assert expected_handover == 4550.00
    
    actual_handover = 4500.00
    discrepancy = actual_handover - expected_handover
    assert discrepancy == -50.00
    assert abs(discrepancy) == 50.00

def test_enhanced_bill_html_features():
    retailer_row = {
        'name': 'Gupta Dairy (gulmohar road Juhu)',
        'retailer_id': 1,
        'zone': 'Route 1',
        'contact': '9876543210',
        'address': 'Kherwadi, Bandra East, Mumbai'
    }
    grid = pd.DataFrame([
        {'Date': '2026-10-01', 'Buffalo Qty': 160.0, 'Cow Qty': 22.0, 'Payment (₹)': 0.0, 'Sales (₹)': 12664.0},
        {'Date': '2026-10-02', 'Buffalo Qty': 160.0, 'Cow Qty': 25.0, 'Payment (₹)': 5000.0, 'Sales (₹)': 12820.0},
    ])
    pay_modes = pd.DataFrame([{'Mode': 'Cash', 'Total (₹)': 5000.0}])
    
    html = build_bill_html(
        retailer_row=retailer_row,
        start_day=date(2026, 10, 1),
        end_day=date(2026, 10, 2),
        grid=grid,
        pay_mode_totals=pay_modes,
        cat_names=['Buffalo', 'Cow'],
        opening_due=275032.00
    )
    
    # 1. Outer Box Outline
    assert "bill-page-wrapper" in html
    assert "border: 2px solid #0f172a" in html
    
    # 2. Toggleable FAT/SNF columns
    assert "fat-snf-col" in html
    
    # 3. Dedicated Payment column
    assert "Payment (₹)" in html
    assert "₹5,000.00" in html
    
    # 4. Remove "Less:"
    assert "Less: Payment Made (in this Period):" not in html
    
    # 5. Thanking message at bottom
    assert "Thank You for Your Business!" in html
    assert "9987471568" in html


def test_worker_wage_revisions_and_attendance_calculation():
    from app import (
        get_worker_wages_df,
        save_worker_wages_df,
        get_worker_rate_for_date,
    )

    # 1. Setup sample worker wage history:
    # Worker 99 initially joined at ₹400/day on 2026-09-01
    # Revised to ₹500/day from 2026-10-16
    sample_wages = pd.DataFrame([
        {
            "wage_id": 901,
            "worker_id": 99,
            "effective_date": "2026-09-01",
            "base_rate": 400.0,
            "salary_type": "Daily",
            "notes": "Joining rate",
            "created_at": "2026-09-01T10:00:00",
        },
        {
            "wage_id": 902,
            "worker_id": 99,
            "effective_date": "2026-10-16",
            "base_rate": 500.0,
            "salary_type": "Daily",
            "notes": "Mid-month increment",
            "created_at": "2026-10-15T18:00:00",
        },
    ])
    existing = get_worker_wages_df()
    combined = pd.concat([existing[existing["worker_id"].astype(int) != 99], sample_wages], ignore_index=True)
    save_worker_wages_df(combined)

    # 2. Verify rate lookup on different dates
    rate_oct10, stype_oct10 = get_worker_rate_for_date(99, date(2026, 10, 10))
    assert rate_oct10 == 400.0
    assert stype_oct10 == "Daily"

    rate_oct15, _ = get_worker_rate_for_date(99, date(2026, 10, 15))
    assert rate_oct15 == 400.0

    rate_oct16, _ = get_worker_rate_for_date(99, date(2026, 10, 16))
    assert rate_oct16 == 500.0

    rate_oct25, _ = get_worker_rate_for_date(99, date(2026, 10, 25))
    assert rate_oct25 == 500.0

    # 3. Calculate October (31 days) earnings:
    # Days 1-15: 15 full days @ ₹400 = ₹6,000
    # Days 16-30: 15 full days @ ₹500 = ₹7,500
    # Day 31: 1 half day (0.5) @ ₹500 = ₹250
    tot_pay = 0.0
    for d in range(1, 32):
        d_obj = date(2026, 10, d)
        rate, _ = get_worker_rate_for_date(99, d_obj)
        units = 0.5 if d == 31 else 1.0
        tot_pay += rate * units

    assert tot_pay == 6000.0 + 7500.0 + 250.0
    assert tot_pay == 13750.0


def test_driver_actual_handover_persistence():
    from app import get_driver_actual_handover, save_driver_actual_handover

    test_d = "2026-10-14"
    test_z = "Route 1"
    
    # Save handover
    save_driver_actual_handover(test_d, test_z, 4500.0, 4550.0)
    
    # Retrieve handover
    val = get_driver_actual_handover(test_d, test_z)
    assert val == 4500.0

    # Expected handover formula without advance:
    cash_collected = 5000.0
    cash_expenses = 450.0
    expected = cash_collected - cash_expenses
    assert expected == 4550.0
    diff = val - expected
    assert diff == -50.0  # ₹50 shortfall


