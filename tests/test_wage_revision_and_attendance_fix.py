import pandas as pd
from datetime import date
import time
from app import (
    get_worker_wages_df,
    save_worker_wages_df,
    get_worker_rate_for_date,
    get_attendance_records,
    save_attendance_matrix,
    extract_att_val,
    parse_attendance_status_label,
    cached_opening_balances,
)


def test_wage_revision_date_effectiveness():
    """
    Test user scenario:
    Worker 1 has baseline rate of ₹500/day.
    A wage revision takes effect on 2026-10-13 at ₹1000/day.
    Days 1 to 12 must be computed at ₹500/day.
    Days 13 to 31 must be computed at ₹1000/day.
    """
    wages_setup = pd.DataFrame([
        {
            "wage_id": 1,
            "worker_id": 1,
            "effective_date": "2020-01-01",
            "base_rate": 500.0,
            "salary_type": "Daily",
            "notes": "Initial base wage",
            "created_at": "2020-01-01T00:00:00",
        },
        {
            "wage_id": 2,
            "worker_id": 1,
            "effective_date": "2026-10-13",
            "base_rate": 1000.0,
            "salary_type": "Daily",
            "notes": "Revision to 1000 from 13th Oct",
            "created_at": "2026-10-15T18:00:00",
        },
    ])
    save_worker_wages_df(wages_setup)
    wages_df = get_worker_wages_df()
    assert not wages_df.empty

    # Days 1 to 12: rate must be ₹500.0
    for day in range(1, 13):
        d_obj = date(2026, 10, day)
        rate, stype = get_worker_rate_for_date(1, d_obj, wages_df=wages_df)
        assert rate == 500.0, f"Day {day} rate should be 500.0, got {rate}"
        assert stype == "Daily"

    # Days 13 to 31: rate must be ₹1000.0
    for day in range(13, 32):
        d_obj = date(2026, 10, day)
        rate, stype = get_worker_rate_for_date(1, d_obj, wages_df=wages_df)
        assert rate == 1000.0, f"Day {day} rate should be 1000.0, got {rate}"
        assert stype == "Daily"

    # Monthly total: 12 days @ 500 + 19 days @ 1000 = 6,000 + 19,000 = 25,000
    tot_earned = 0.0
    for day in range(1, 32):
        d_obj = date(2026, 10, day)
        rate, _ = get_worker_rate_for_date(1, d_obj, wages_df=wages_df)
        tot_earned += rate * 1.0  # 1.0 full day

    assert tot_earned == 25000.0, f"Expected 25,000, got {tot_earned}"


def test_attendance_matrix_saving_integrity():
    """
    Test saving attendance matrix with Full, Half, and Absent,
    and verify that reload has zero corruption and zero duplicates.
    """
    test_matrix = pd.DataFrame([
        {
            "worker_id": 1,
            "कामगार नाव (Name)": "Ramesh Yadav",
            "पद (Role)": "Driver",
            "1": "Full",
            "2": "Half",
            "3": "Absent",
            **{str(d): "Full" for d in range(4, 32)}
        },
        {
            "worker_id": 2,
            "कामगार नाव (Name)": "Suresh Gawali",
            "पद (Role)": "Helper",
            "1": "Half",
            "2": "Full",
            "3": "Full",
            **{str(d): "Half" for d in range(4, 32)}
        }
    ])

    save_attendance_matrix(2026, 10, test_matrix)

    # Reload records
    records = get_attendance_records(2026, 10)
    assert not records.empty

    # Verify no duplicates
    assert not records.duplicated(subset=["worker_id", "date"]).any()

    # Worker 1 checks
    w1_d1 = records[(records["worker_id"] == 1) & (records["date"] == "2026-10-01")].iloc[0]
    assert w1_d1["status"] == "P"
    assert float(w1_d1["units"]) == 1.0

    w1_d2 = records[(records["worker_id"] == 1) & (records["date"] == "2026-10-02")].iloc[0]
    assert w1_d2["status"] == "HD"
    assert float(w1_d2["units"]) == 0.5

    w1_d3 = records[(records["worker_id"] == 1) & (records["date"] == "2026-10-03")].iloc[0]
    assert w1_d3["status"] == "A"
    assert float(w1_d3["units"]) == 0.0

    # Worker 2 checks
    w2_d1 = records[(records["worker_id"] == 2) & (records["date"] == "2026-10-01")].iloc[0]
    assert w2_d1["status"] == "HD"
    assert float(w2_d1["units"]) == 0.5


def test_extract_att_val_helper():
    """Test extract_att_val handles both int and str column names, whitespace, and case variants."""
    row_str = pd.Series({"1": "Full", "2": "Half", "3": "Absent", "worker_id": 1})
    assert extract_att_val(row_str, 1) == "Full"
    assert extract_att_val(row_str, 2) == "Half"
    assert extract_att_val(row_str, 3) == "Absent"

    row_int = pd.Series({1: "full", 2: "0.5", 3: "a", "worker_id": 1})
    assert extract_att_val(row_int, 1) == "Full"
    assert extract_att_val(row_int, 2) == "Half"
    assert extract_att_val(row_int, 3) == "Absent"


def test_in_memory_opening_balance_speed():
    """Verify cached_opening_balances completes in < 500ms using in-memory data."""
    t0 = time.time()
    balances = cached_opening_balances((1, 2, 3, 4, 5), date.today(), 1)
    duration_ms = (time.time() - t0) * 1000
    assert isinstance(balances, dict)
    assert len(balances) == 5
    assert duration_ms < 500, f"Calculation took {duration_ms:.1f}ms, expected < 500ms"


def test_parse_attendance_status_label_and_absent_preservation():
    """
    Verify that parse_attendance_status_label ALWAYS strictly preserves Absent
    and never corrupts or converts Absent (status='A', units=0.0) into Full.
    """
    # Standard DB records for Absent
    assert parse_attendance_status_label("A", 0.0) == "Absent"
    assert parse_attendance_status_label("A", None) == "Absent"
    assert parse_attendance_status_label("ABSENT", 0.0) == "Absent"
    assert parse_attendance_status_label("leave", 0.0) == "Absent"
    assert parse_attendance_status_label("सुट्टी", 0.0) == "Absent"
    assert parse_attendance_status_label("गैरहजर", 0.0) == "Absent"
    assert parse_attendance_status_label("0", 0.0) == "Absent"
    assert parse_attendance_status_label("-", 0.0) == "Absent"

    # Even if status is somehow missing or blank, units == 0.0 must be Absent
    assert parse_attendance_status_label("", 0.0) == "Absent"
    assert parse_attendance_status_label(None, 0.0) == "Absent"

    # Half Day checks
    assert parse_attendance_status_label("HD", 0.5) == "Half"
    assert parse_attendance_status_label("HALF", None) == "Half"
    assert parse_attendance_status_label("0.5", 0.5) == "Half"
    assert parse_attendance_status_label("अर्धा", 0.5) == "Half"

    # Full Day checks
    assert parse_attendance_status_label("P", 1.0) == "Full"
    assert parse_attendance_status_label("FULL", None) == "Full"
    assert parse_attendance_status_label("PRESENT", 1.0) == "Full"
    assert parse_attendance_status_label(None, 1.0) == "Full"


def test_ui_matrix_absent_roundtrip():
    """
    Test full UI workflow:
    1. Worker 1 has Absent marked on days 4 and 10.
    2. Save via save_attendance_matrix.
    3. Reload via get_attendance_records.
    4. Build att_lookup exactly as done on the Attendance UI page.
    5. Verify att_lookup contains 'Absent' for days 4 and 10.
    """
    days = {str(d): "Full" for d in range(1, 32)}
    days["4"] = "Absent"
    days["10"] = "Absent"
    days["15"] = "Half"

    matrix = pd.DataFrame([{
        "worker_id": 1,
        "कामगार नाव (Name)": "Ramesh Yadav",
        "पद (Role)": "Driver",
        **days
    }])

    save_attendance_matrix(2026, 10, matrix)

    records = get_attendance_records(2026, 10)
    assert not records.empty

    # Reconstruct att_lookup exactly as done in app.py UI
    att_lookup = {}
    for _, ar in records.iterrows():
        a_date = pd.to_datetime(ar["date"]).date()
        wid = int(ar["worker_id"])
        day = a_date.day
        val_label = parse_attendance_status_label(ar.get("status", "P"), ar.get("units", None))
        att_lookup[(wid, day)] = val_label

    # Days 4 and 10 MUST be strictly 'Absent' in the UI matrix
    assert att_lookup.get((1, 4)) == "Absent", f"Day 4 must be Absent, got {att_lookup.get((1, 4))}"
    assert att_lookup.get((1, 10)) == "Absent", f"Day 10 must be Absent, got {att_lookup.get((1, 10))}"
    assert att_lookup.get((1, 15)) == "Half", f"Day 15 must be Half, got {att_lookup.get((1, 15))}"
    assert att_lookup.get((1, 1)) == "Full", f"Day 1 must be Full, got {att_lookup.get((1, 1))}"

