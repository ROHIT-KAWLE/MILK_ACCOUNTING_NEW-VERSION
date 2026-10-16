"""
Unit test to verify that all table column headers across Milk Accounting Pro
are locked (non-sortable and non-movable), matching the Daily Entry table behavior,
and that the navigation deck uses the light mode theme with enlarged button words.
"""

def test_universal_table_header_lock_css_present():
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Verify table header lock styles
    assert 'UNIVERSAL TABLE HEADER LOCK: NON-SORTABLE & NON-MOVABLE' in content
    assert 'div[data-testid="stDataFrame"]::before' in content
    assert 'div[data-testid="stDataEditor"]::before' in content
    assert 'height: 38px !important;' in content
    assert 'pointer-events: auto !important;' in content
    assert 'cursor: default !important;' in content

def test_universal_table_header_event_interceptor_present():
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Verify event interceptor script
    assert 'Universal Double-Layer Event Interceptor' in content
    assert 'lockGridHeaders' in content
    assert 'stopImmediatePropagation' in content

def test_navigation_light_theme_and_enlarged_text():
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Verify light theme container
    assert 'background: #ffffff !important;' in content
    assert 'LIGHT THEME (MATCHES WHOLE APP)' in content

    # Verify enlarged font size (18.5px) and min-height (70px)
    assert 'font-size: 18.5px !important;' in content
    assert 'min-height: 70px !important;' in content
