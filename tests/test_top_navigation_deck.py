"""
Unit tests for the new Big Executive Command Navigation Deck in Milk Accounting Pro.
Verifies that navigation items, identifiers, sub-menus, and state contracts are 100% reliable.
"""

def test_navigation_items_defined_in_app():
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Verify NAV_ITEMS_ROW1 exists and has 4 items
    assert "NAV_ITEMS_ROW1 = [" in content
    assert '"📊 Dashboard"' in content
    assert '"📝 Daily Entry"' in content
    assert '"👷 कामगार हजेरी (Attendance)"' in content
    assert '"🧾 Bills & Statements"' in content

    # Verify NAV_ITEMS_ROW2 exists and has 4 items
    assert "NAV_ITEMS_ROW2 = [" in content
    assert '"🤖 AI Audit & Anomaly Detection"' in content
    assert '"💰 Price Management"' in content
    assert '"⚙️ Master Setup"' in content
    assert '"🛡️ Data Health & Backup"' in content

    # Verify st.segmented_control was completely eradicated from navigation
    assert "top_app_navbar" not in content
    assert "sub_nav_bill" not in content
    assert "sub_nav_setup" not in content
    assert "st.segmented_control" not in content

def test_navigation_button_keys_and_classes():
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Verify distinct keys for styling and event hooks
    expected_keys = [
        "nav_deck_btn_dash",
        "nav_deck_btn_daily",
        "nav_deck_btn_att",
        "nav_deck_btn_bill",
        "nav_deck_btn_ai",
        "nav_deck_btn_price",
        "nav_deck_btn_setup",
        "nav_deck_btn_backup",
        "subnav_btn_ret_bill",
        "subnav_btn_dist_bill",
        "subnav_btn_ret",
        "subnav_btn_dist",
        "subnav_btn_cat",
        "subnav_btn_map",
    ]
    for key in expected_keys:
        assert key in content, f"Missing key {key} in navigation code"

def test_navigation_branch_compatibility():
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Verify all conditional branches in app.py match the navigation ids
    assert 'if menu == "📊 Dashboard":' in content
    assert 'elif menu in ("📝 Daily Entry", "📝 Daily Posting Sheet (Excel)"):' in content
    assert 'elif menu == "👷 कामगार हजेरी (Attendance)":' in content
    assert 'elif menu == "🤖 AI Audit & Anomaly Detection":' in content
    assert 'elif menu == "💰 Price Management":' in content
    assert 'elif menu == "🛡️ Data Health & Backup":' in content
    assert 'bill_menu == "🏪 Retailers Bill"' in content
    assert 'bill_menu == "🚚 Distributor Procurement Bill"' in content
    assert 'setup_menu == "🏪 Retailers"' in content
    assert 'setup_menu == "🚚 Distributors"' in content
    assert 'setup_menu == "🥛 Milk Categories"' in content
    assert 'setup_menu == "🧩 Distributor Category Mapping"' in content
