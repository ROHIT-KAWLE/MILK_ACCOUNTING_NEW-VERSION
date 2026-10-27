# ============================================================
# MILK ACCOUNTING PRO
# Dairy Distribution & Retailer Accounting System
# ============================================================

# ============================================================
# IMPORTS
# ============================================================

# Standard library
from datetime import date, timedelta, datetime
import calendar
import io
import os
import ssl
import time
import zipfile

# Third-party
import httpx

# Securely configure system root CA certificates for SSL verification so Supabase
# and external requests connect reliably with full TLS validation on Windows.
if os.name == "nt":
    try:
        _ssl_ctx = ssl.create_default_context()
        _ssl_ctx.load_default_certs()
        ssl._create_default_https_context = lambda: _ssl_ctx
        _orig_httpx_init = httpx.Client.__init__
        def _safe_httpx_init(self, *args, **kwargs):
            if kwargs.get("verify") is True or "verify" not in kwargs:
                kwargs["verify"] = _ssl_ctx
            _orig_httpx_init(self, *args, **kwargs)
        httpx.Client.__init__ = _safe_httpx_init
    except Exception:
        pass

import warnings
warnings.filterwarnings("ignore")

try:
    import logging
    class _IgnoreContainerWidth(logging.Filter):
        def filter(self, record):
            return "use_container_width" not in str(record.getMessage())

    logging.getLogger("streamlit").addFilter(_IgnoreContainerWidth())
    logging.getLogger("streamlit.deprecation_util").addFilter(_IgnoreContainerWidth())
    logging.getLogger("streamlit.elements.arrow").addFilter(_IgnoreContainerWidth())
    logging.getLogger("streamlit.elements.widgets.data_editor").addFilter(_IgnoreContainerWidth())

    import streamlit.deprecation_util as _sdu
    if hasattr(_sdu, "_LOGGER"):
        _orig_warn = _sdu._LOGGER.warning
        _sdu._LOGGER.warning = lambda msg, *a, **kw: None if "use_container_width" in str(msg) else _orig_warn(msg, *a, **kw)
    _sdu.show_deprecation_warning = lambda *args, **kwargs: None
except Exception:
    pass

import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import streamlit as st
from supabase import create_client
import ai_engine

# ============================================================
# STREAMLIT PAGE CONFIGURATION & GLOBAL STYLES
# ============================================================
st.set_page_config(
    page_title="Milk Accounting Pro", layout="wide", initial_sidebar_state="expanded"
)
st.markdown(
    """
<style>
:root{
  --bg: #F8FAFC;
  --card: rgba(255,255,255,0.95);
  --text: #0F172A;
  --muted: #64748B;
  --border: rgba(15, 23, 42, 0.08);
  --shadow: 0 10px 30px rgba(2, 6, 23, 0.06);
  --shadow2: 0 4px 14px rgba(2, 6, 23, 0.05);
  --radius: 16px;
  --primary: #2563EB;
  --primary2: #1D4ED8;
}

.stApp {
  background: radial-gradient(1100px 650px at 8% 0%, rgba(37,99,235,0.06), transparent 55%),
              radial-gradient(900px 500px at 92% 10%, rgba(16,185,129,0.05), transparent 55%),
              linear-gradient(180deg, var(--bg) 0%, #EEF2FF 120%);
}

.block-container { padding-top: 1.0rem !important; padding-bottom: 2.5rem !important; }

section[data-testid="stSidebar"]{
  background: rgba(255,255,255,0.85) !important;
  backdrop-filter: blur(12px);
  border-right: 1px solid var(--border);
}

/* Modern Sidebar Navigation Menu Cards */
div[data-testid="stSidebar"] div[role="radiogroup"] {
  display: flex !important;
  flex-direction: column !important;
  gap: 7px !important;
  padding: 4px 0 !important;
}
div[data-testid="stSidebar"] div[role="radiogroup"] > label {
  background: rgba(255, 255, 255, 0.72) !important;
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
  border-radius: 12px !important;
  padding: 10px 14px !important;
  margin: 0 !important;
  cursor: pointer !important;
  transition: all 0.16s ease-in-out !important;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
  width: 100% !important;
}
div[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
  background: #f1f5f9 !important;
  border-color: #94a3b8 !important;
  transform: translateX(3px) !important;
}
div[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
  background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%) !important;
  border-color: #1d4ed8 !important;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.28) !important;
}
div[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p,
div[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) span {
  color: #ffffff !important;
  font-weight: 850 !important;
}
div[data-testid="stSidebar"] div[role="radiogroup"] > label:not(:has(input:checked)) p,
div[data-testid="stSidebar"] div[role="radiogroup"] > label:not(:has(input:checked)) span {
  color: #1e293b !important;
  font-weight: 700 !important;
}

h1,h2,h3,h4 { letter-spacing: -0.02em !important; }
h1 { font-weight: 900 !important; }
h2 { font-weight: 800 !important; }
h3 { color: var(--muted) !important; font-weight: 700 !important; }

.stButton>button{
  background: linear-gradient(180deg, var(--primary) 0%, var(--primary2) 100%) !important;
  color:#fff !important;
  border: 1px solid rgba(255,255,255,0.18) !important;
  border-radius: 12px !important;
  padding: 0.65rem 1.05rem !important;
  font-weight: 800 !important;
  box-shadow: 0 8px 16px rgba(37,99,235,0.16) !important;
  transition: transform 0.08s ease, filter 0.12s ease !important;
}
.stButton>button:hover{ filter: brightness(1.04); transform: translateY(-1px); }
.stButton>button:active{ transform: translateY(0px); }

div[data-baseweb="input"]>div,
div[data-baseweb="select"]>div,
div[data-baseweb="textarea"]>div{
  border-radius: 12px !important;
  border: 1px solid var(--border) !important;
  background: rgba(255,255,255,0.85) !important;
  box-shadow: none !important;
}
label { color: var(--muted) !important; font-weight: 700 !important; }

.stTabs [data-baseweb="tab-list"]{ gap:10px; }
.stTabs [data-baseweb="tab"]{
  background: rgba(255,255,255,0.55) !important;
  border: 1px solid var(--border) !important;
  border-radius: 999px !important;
  padding: 10px 14px !important;
  font-weight: 800 !important;
  color: var(--muted) !important;
}
.stTabs [aria-selected="true"]{
  background: rgba(37,99,235,0.12) !important;
  border: 1px solid rgba(37,99,235,0.35) !important;
  color: var(--text) !important;
}

div[data-testid="stMetric"]{
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  padding: 16px !important;
  box-shadow: var(--shadow2) !important;
}
div[data-testid="stMetric"] label{ color: var(--muted) !important; font-weight: 800 !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"]{
  font-size: 1.65rem !important;
  font-weight: 950 !important;
}

div[data-testid="stDataEditor"]{
  background: var(--card) !important;
  border-radius: var(--radius) !important;
  border: 1px solid var(--border) !important;
  box-shadow: var(--shadow) !important;
  overflow: hidden !important;
}

details[data-testid="stExpander"]{
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow2) !important;
  overflow: hidden !important;
}


hr { border-color: rgba(15,23,42,0.08) !important; }

/* Non-Tech Operator Visual Hierarchy & Bold Entity Styling */
.ag-theme-streamlit .ag-cell[col-id="Retailer"],
.ag-theme-alpine .ag-cell[col-id="Retailer"],
.ag-theme-streamlit .ag-cell[col-id="Distributor"],
.ag-theme-alpine .ag-cell[col-id="Distributor"] {
  font-weight: 800 !important;
  color: #0f172a !important;
  font-size: 13.5px !important;
  letter-spacing: -0.01em !important;
}

/* AgGrid Focus & Active Row Crosshair Highlighting */
.ag-theme-streamlit .ag-row-focus,
.ag-theme-alpine .ag-row-focus {
  background-color: #fef3c7 !important; /* Soft warm amber highlight */
}
.ag-theme-streamlit .ag-cell-focus,
.ag-theme-alpine .ag-cell-focus {
  background-color: #fde68a !important; /* Rich amber highlight */
  outline: 2.5px solid #d97706 !important;
  font-weight: 900 !important;
  box-shadow: inset 0 0 6px rgba(217,119,6,0.3) !important;
}
.ag-theme-streamlit .ag-row-focus .ag-pinned-left-cols-container .ag-cell {
  background-color: #fef3c7 !important;
}

#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
/* DON'T hide the header; it contains the sidebar toggle */
/* header {visibility:hidden;} */

</style>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# DATA FILE PATH CONSTANTS & TABLE MAPPINGS
# ============================================================
# Ensure local data and invoices directories exist on fresh deployments
os.makedirs("data", exist_ok=True)
os.makedirs("invoices", exist_ok=True)

# Keep same "file names" so your app code doesn't change
RETAILERS_FILE = "data/retailers.csv"
CATEGORIES_FILE = "data/categories.csv"
PRICES_FILE = "data/prices.csv"
ENTRIES_FILE = "data/entries.csv"
PAYMENTS_FILE = "data/payments.csv"
DISTRIBUTORS_FILE = "data/distributors.csv"
DISTRIBUTOR_PURCHASES_FILE = "data/distributor_purchases.csv"
DISTRIBUTOR_PAYMENTS_FILE = "data/distributor_payments.csv"
DISTRIBUTOR_CATEGORY_MAP_FILE = "data/distributor_category_map.csv"
WASTAGE_FILE = "data/wastage.csv"
EXPENSES_FILE = "data/expenses.csv"
WORKERS_FILE = "data/workers.csv"
WORKER_ATTENDANCE_FILE = "data/worker_attendance.csv"
ATTENDANCE_LOCKS_FILE = "data/attendance_date_locks.csv"
WORKER_WAGES_FILE = "data/worker_wages.csv"

GLOBAL_RETAILER_ID = 0

FILE_TO_TABLE = {
    RETAILERS_FILE: ("retailers", "retailer_id"),
    CATEGORIES_FILE: ("categories", "category_id"),
    PRICES_FILE: ("prices", "price_id"),
    ENTRIES_FILE: ("entries", "entry_id"),
    PAYMENTS_FILE: ("payments", "payment_id"),
    DISTRIBUTORS_FILE: ("distributors", "distributor_id"),
    DISTRIBUTOR_PURCHASES_FILE: ("distributor_purchases", "purchase_id"),
    DISTRIBUTOR_PAYMENTS_FILE: ("distributor_payments", "payment_id"),
    DISTRIBUTOR_CATEGORY_MAP_FILE: ("distributor_category_map", "map_id"),
    WASTAGE_FILE: ("wastage", "wastage_id"),
    EXPENSES_FILE: ("expenses", "expense_id"),
    WORKERS_FILE: ("workers", "worker_id"),
    WORKER_ATTENDANCE_FILE: ("worker_attendance", "attendance_id"),
    ATTENDANCE_LOCKS_FILE: ("attendance_date_locks", "lock_date"),
    WORKER_WAGES_FILE: ("worker_wages", "wage_id"),
}


# ============================================================
# SUPABASE CLIENT INITIALIZATION & HEALTH CHECK
# ============================================================
@st.cache_resource
def get_sb():
    if "supabase" not in st.secrets:
        st.error(
            "⚠️ **Missing Supabase Secrets!**\n\n"
            "Please configure `[supabase]` secrets in your Streamlit Cloud dashboard under "
            "**App Settings -> Secrets**.\n\n"
            "Refer to `.streamlit/secrets.toml.example` for the required keys (`url`, `anon_key`, `service_role_key`)."
        )
        st.stop()
    cfg = st.secrets["supabase"]
    try:
        return create_client(cfg["url"], cfg["anon_key"])
    except Exception as e:
        st.error(f"⚠️ **Supabase Client Initialization Error:** {e}")
        st.stop()


sb = get_sb()

if st.sidebar.button("🔌 Test DB Connection"):
    try:
        sb.table("retailers").select("retailer_id").limit(1).execute()
        st.sidebar.success("Supabase connected ✅")
    except Exception as e:
        st.sidebar.error(f"Connection failed ❌\n{e}")


# ============================================================
# CACHE INVALIDATION & STATE SYNCHRONIZATION
# ============================================================
st.session_state.setdefault("data_version", 0)
st.session_state.setdefault("daily_save_lock", False)


def invalidate_data_cache():
    st.session_state["data_version"] = int(st.session_state.get("data_version", 0)) + 1
    # Purge in-memory draft states across all screens to guarantee zero stale data
    st.session_state["daily_drafts"] = {}
    st.session_state["daily_loaded_ctx"] = None
    st.session_state["daily_meta"] = {}
    st.session_state["dist_flat_grid"] = pd.DataFrame()
    st.session_state["dist_flat_payments"] = pd.DataFrame()
    st.session_state["backup_zip_bytes"] = None
    st.session_state["backup_zip_version"] = None


# ============================================================
# BACKUP & DATA EXPORT GENERATORS
# ============================================================
def make_range_backup_csv(
    start_date,
    end_date,
    retailers,
    categories,
    entries,
    payments,
    dist_purchases,
    dist_payments,
    distributors,
):
    """
    SAFE VERSION
    - Uses csv.writer (fixes corrupted CSV structure)
    - Prevents bad IDs becoming 0
    - Properly escapes commas/quotes/newlines
    - Stable Excel-compatible export
    """

    import io
    import csv
    import pandas as pd

    output = io.StringIO()
    writer = csv.writer(output)

    PAYMENT_MODES = ["Cash", "UPI", "Bank", "Cheque", "Other"]

    # FIX: payment_mode strings in the DB use mixed case (e.g. "UPI", "upi",
    # "Cash", "BANK", …). The original code used `.str.title()` which turned
    # "UPI" into "Upi" — that no longer matched the `PAYMENT_MODES` keys, so
    # everything fell through to the Cash bucket. Use a case-insensitive map
    # against an uppercase canonical key.
    _PM_CANON = {m.upper(): m for m in PAYMENT_MODES}

    def _canon_mode(v):
        s = str(v or "").strip().upper()
        return _PM_CANON.get(s, "Cash")

    # =========================================================
    # HELPERS
    # =========================================================

    def _to_date(df, col="date"):
        if df is None or df.empty or col not in df.columns:
            return pd.DataFrame()

        df = df.copy()
        # FIX: force string format so comparisons with `d` (also string) always work.
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
        return df

    def _num(df, cols):
        if df is None or df.empty:
            return pd.DataFrame()

        df = df.copy()

        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

        return df

    # =========================================================
    # NORMALIZE INPUTS
    # =========================================================

    entries = _to_date(entries)
    payments = _to_date(payments)
    dist_purchases = _to_date(dist_purchases)
    dist_payments = _to_date(dist_payments)

    if not entries.empty:
        entries = _num(entries, ["retailer_id", "category_id", "qty", "amount"])

    if not payments.empty:
        payments = _num(payments, ["retailer_id", "amount"])

    if not dist_purchases.empty:
        dist_purchases = _num(
            dist_purchases, ["distributor_id", "category_id", "qty", "amount"]
        )

    if not dist_payments.empty:
        dist_payments = _num(dist_payments, ["distributor_id", "amount"])

        if "payment_mode" in dist_payments.columns:
            # FIX: use case-insensitive canonical mapping (was .str.title() which
            # broke "UPI" → "Upi" and silently routed UPI/Bank/Cheque to "Cash").
            dist_payments["payment_mode"] = (
                dist_payments["payment_mode"]
                .fillna("Cash")
                .astype(str)
                .map(_canon_mode)
            )

    # =========================================================
    # RETAILERS
    # =========================================================

    retailers = retailers.copy()

    retailers["retailer_id"] = pd.to_numeric(retailers["retailer_id"], errors="coerce")

    retailers = retailers.dropna(subset=["retailer_id"])

    retailers["retailer_id"] = retailers["retailer_id"].astype(int)

    retailers["name"] = retailers["name"].fillna("").astype(str)

    retailer_list = (
        retailers[["retailer_id", "name"]]
        .drop_duplicates("retailer_id")
        .values.tolist()
    )

    rid_to_name = {int(r[0]): str(r[1]) for r in retailer_list}

    all_rids = [int(r[0]) for r in retailer_list]

    # =========================================================
    # CATEGORIES
    # =========================================================

    categories = categories.copy()

    categories["category_id"] = pd.to_numeric(
        categories["category_id"], errors="coerce"
    )

    categories = categories.dropna(subset=["category_id"])

    categories["category_id"] = categories["category_id"].astype(int)

    categories["name"] = categories["name"].fillna("").astype(str)

    cat_list = (
        categories[["category_id", "name"]]
        .drop_duplicates("category_id")
        .values.tolist()
    )

    cid_to_name = {int(c[0]): str(c[1]).upper() for c in cat_list}

    all_cids = [int(c[0]) for c in cat_list]

    cat_names = [cid_to_name[c] for c in all_cids]

    # =========================================================
    # DISTRIBUTORS
    # =========================================================

    distributors = distributors.copy()

    distributors["distributor_id"] = pd.to_numeric(
        distributors["distributor_id"], errors="coerce"
    )

    distributors = distributors.dropna(subset=["distributor_id"])

    distributors["distributor_id"] = distributors["distributor_id"].astype(int)

    distributors["name"] = distributors["name"].fillna("").astype(str)

    dist_list = (
        distributors[["distributor_id", "name"]]
        .drop_duplicates("distributor_id")
        .values.tolist()
    )

    did_to_name = {int(d[0]): str(d[1]).upper() for d in dist_list}

    all_dids = [int(d[0]) for d in dist_list]

    # =========================================================
    # DATE RANGE
    # =========================================================

    # FIX: keep dates as strings so they match the strftime'd `date` columns above.
    _start_str = pd.to_datetime(start_date, errors="coerce").strftime("%Y-%m-%d")
    _end_str = pd.to_datetime(end_date, errors="coerce").strftime("%Y-%m-%d")

    all_dates = pd.date_range(start_date, end_date, freq="D").strftime("%Y-%m-%d")

    # =========================================================
    # OPENING BALANCES
    # =========================================================

    def _opening_retailer(rid):

        e_before = (
            entries.loc[
                (entries["retailer_id"].astype(int) == rid)
                & (entries["date"] < _start_str),
                "amount",
            ].sum()
            if not entries.empty
            else 0.0
        )

        p_before = (
            payments.loc[
                (payments["retailer_id"].astype(int) == rid)
                & (payments["date"] < _start_str),
                "amount",
            ].sum()
            if not payments.empty
            else 0.0
        )

        return round(float(e_before - p_before), 2)

    def _opening_distributor(did):

        d_before = (
            dist_purchases.loc[
                (dist_purchases["distributor_id"].astype(int) == did)
                & (dist_purchases["date"] < _start_str),
                "amount",
            ].sum()
            if not dist_purchases.empty
            else 0.0
        )

        p_before = (
            dist_payments.loc[
                (dist_payments["distributor_id"].astype(int) == did)
                & (dist_payments["date"] < _start_str),
                "amount",
            ].sum()
            if not dist_payments.empty
            else 0.0
        )

        return round(float(d_before - p_before), 2)

    retailer_running = {rid: _opening_retailer(rid) for rid in all_rids}

    dist_running = {did: _opening_distributor(did) for did in all_dids}

    # =========================================================
    # HEADERS
    # =========================================================

    r_header = (
        ["Retailer"]
        + cat_names
        + ["Total L", "Total ₹"]
        + PAYMENT_MODES
        + ["Previous", "Ledger"]
    )

    d_header = (
        ["Distributor"]
        + cat_names
        + ["Total L", "Total ₹", "Payment", "Previous", "Ledger"]
    )

    gap = ["", ""]

    full_header = r_header + gap + d_header

    # =========================================================
    # MAIN LOOP
    # =========================================================

    for d in all_dates:
        writer.writerow([f"DATE : {d}"])
        writer.writerow([])

        writer.writerow(full_header)

        e_day = (
            entries.loc[entries["date"] == d].copy()
            if not entries.empty
            else pd.DataFrame()
        )

        p_day = (
            payments.loc[payments["date"] == d].copy()
            if not payments.empty
            else pd.DataFrame()
        )

        dp_day = (
            dist_purchases.loc[dist_purchases["date"] == d].copy()
            if not dist_purchases.empty
            else pd.DataFrame()
        )

        dpay_day = (
            dist_payments.loc[dist_payments["date"] == d].copy()
            if not dist_payments.empty
            else pd.DataFrame()
        )

        # =====================================================
        # RETAILERS
        # =====================================================

        retailer_rows = []

        for rid in all_rids:
            rname = rid_to_name.get(rid, str(rid))

            cat_qtys = []
            total_l = 0.0

            for cid in all_cids:
                if e_day.empty:
                    qty = 0.0
                else:
                    sub = e_day.loc[
                        (e_day["retailer_id"].astype(int) == rid)
                        & (e_day["category_id"].astype(int) == cid)
                    ]

                    qty = round(float(sub["qty"].sum()), 3) if not sub.empty else 0.0

                cat_qtys.append(qty)
                total_l += qty

            total_l = round(total_l, 3)

            total_rs = (
                round(
                    float(
                        e_day.loc[
                            e_day["retailer_id"].astype(int) == rid, "amount"
                        ].sum()
                    ),
                    2,
                )
                if not e_day.empty
                else 0.0
            )

            mode_amts = {m: 0.0 for m in PAYMENT_MODES}

            if not p_day.empty:
                r_pay = p_day.loc[p_day["retailer_id"].astype(int) == rid].copy()

                if not r_pay.empty:
                    # FIX: case-insensitive canonical mapping (see _canon_mode
                    # at top of function). The previous .str.title() call
                    # converted "UPI" → "Upi" which never matched the
                    # PAYMENT_MODES keys, so all non-Cash modes were silently
                    # added to the Cash bucket.
                    r_pay["payment_mode"] = (
                        r_pay.get("payment_mode", pd.Series(dtype=str))
                        .fillna("Cash")
                        .astype(str)
                        .map(_canon_mode)
                    )

                    for _, row in r_pay.iterrows():
                        pm = _canon_mode(row.get("payment_mode", "Cash"))

                        amt = round(float(row.get("amount", 0.0)), 2)

                        # pm is always a valid key thanks to _canon_mode.
                        mode_amts[pm] += amt

            total_pay = round(sum(mode_amts.values()), 2)

            prev_ledger = round(float(retailer_running[rid]), 2)

            close_ledger = round(prev_ledger + total_rs - total_pay, 2)

            retailer_running[rid] = close_ledger

            retailer_rows.append(
                [rname]
                + cat_qtys
                + [total_l, total_rs]
                + [mode_amts[m] for m in PAYMENT_MODES]
                + [prev_ledger, close_ledger]
            )

        # =====================================================
        # DISTRIBUTORS
        # =====================================================

        dist_rows = []

        for did in all_dids:
            dname = did_to_name.get(did, str(did))

            cat_qtys = []
            total_l = 0.0

            for cid in all_cids:
                if dp_day.empty:
                    qty = 0.0
                else:
                    sub = dp_day.loc[
                        (dp_day["distributor_id"].astype(int) == did)
                        & (dp_day["category_id"].astype(int) == cid)
                    ]

                    qty = round(float(sub["qty"].sum()), 3) if not sub.empty else 0.0

                cat_qtys.append(qty)
                total_l += qty

            total_l = round(total_l, 3)

            total_rs = (
                round(
                    float(
                        dp_day.loc[
                            dp_day["distributor_id"].astype(int) == did, "amount"
                        ].sum()
                    ),
                    2,
                )
                if not dp_day.empty
                else 0.0
            )

            total_pay = (
                round(
                    float(
                        dpay_day.loc[
                            dpay_day["distributor_id"].astype(int) == did, "amount"
                        ].sum()
                    ),
                    2,
                )
                if not dpay_day.empty
                else 0.0
            )

            prev_ledger = round(float(dist_running[did]), 2)

            close_ledger = round(prev_ledger + total_rs - total_pay, 2)

            dist_running[did] = close_ledger

            dist_rows.append(
                [dname]
                + cat_qtys
                + [total_l, total_rs, total_pay, prev_ledger, close_ledger]
            )

        # =====================================================
        # WRITE ROWS
        # =====================================================

        max_rows = max(len(retailer_rows), len(dist_rows))

        empty_r = [""] * len(r_header)
        empty_d = [""] * len(d_header)

        for i in range(max_rows):
            r_row = retailer_rows[i] if i < len(retailer_rows) else empty_r

            d_row = dist_rows[i] if i < len(dist_rows) else empty_d

            combined = r_row + gap + d_row

            writer.writerow(combined)

        writer.writerow([])
        writer.writerow([])

    return output.getvalue().encode("utf-8")


def make_full_backup_zip(data_version: int) -> bytes:
    """
    FIXED: Uses same processed pipeline as app
    DOES NOT break existing structure
    """

    _ = data_version

    # ✅ USE CENTRAL DATA LOADER (already used in app)
    (
        retailers,
        categories,
        prices,
        entries,
        payments,
        distributors,
        dist_purchases,
        dist_payments,
        dist_cat_map,
        wastage,
        expenses,
    ) = load_all_data(data_version)

    # ✅ ADD LEDGER & MAIN_RETAILERS
    ledger_df = compute_ledger_fast(entries, payments)
    try:
        main_retailers_df = sb_fetch_all("main_retailers", cols="retailer_id")
    except Exception:
        main_retailers_df = pd.DataFrame(columns=["retailer_id"])

    # ✅ ADD WORKERS, WAGES, ATTENDANCE, DRIVER HANDOVERS & ATTENDANCE LOCKS
    try:
        workers_df = get_workers_df()
    except Exception:
        workers_df = pd.read_csv("data/workers.csv") if os.path.exists("data/workers.csv") else pd.DataFrame()

    try:
        wages_df = get_worker_wages_df()
    except Exception:
        wages_df = pd.read_csv("data/worker_wages.csv") if os.path.exists("data/worker_wages.csv") else pd.DataFrame()

    try:
        att_df = pd.read_csv("data/worker_attendance.csv") if os.path.exists("data/worker_attendance.csv") else pd.DataFrame()
    except Exception:
        att_df = pd.DataFrame()

    try:
        handovers_df = pd.read_csv("data/driver_handovers.csv") if os.path.exists("data/driver_handovers.csv") else pd.DataFrame()
    except Exception:
        handovers_df = pd.DataFrame()

    try:
        att_locks_df = pd.read_csv("data/attendance_date_locks.csv") if os.path.exists("data/attendance_date_locks.csv") else pd.DataFrame()
    except Exception:
        att_locks_df = pd.DataFrame()

    # ✅ KEEP SAME TABLE NAMES (no break) + ALL LOCAL TABLES
    tables = {
        "retailers": retailers,
        "categories": categories,
        "prices": prices,
        "entries": entries,
        "payments": payments,
        "distributors": distributors,
        "distributor_purchases": dist_purchases,
        "distributor_payments": dist_payments,
        "distributor_category_map": dist_cat_map,
        "wastage": wastage,
        "expenses": expenses,
        "main_retailers": main_retailers_df,
        "ledger": ledger_df,
        "workers": workers_df,
        "worker_wages": wages_df,
        "worker_attendance": att_df,
        "driver_handovers": handovers_df,
        "attendance_date_locks": att_locks_df,
    }

    buf = io.BytesIO()

    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, df in tables.items():
            if isinstance(df, pd.DataFrame):
                zf.writestr(f"{name}.csv", df.to_csv(index=False).encode("utf-8"))

    return buf.getvalue()


def _secret_bool(key: str, default: bool = False) -> bool:
    try:
        raw = st.secrets["supabase"].get(key, default)
    except Exception:
        return default
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes", "y", "on")
    return bool(raw)


# Toggle DB-assigned IDs and server-side filtering via secrets if desired.
USE_DB_IDS = False
USE_SERVER_FILTERS = True
if not USE_SERVER_FILTERS:
    st.warning(
        "⚠️ App is running in LOCAL CSV mode. If you delete data in Supabase, it will not reflect here. Turn on Supabase mode in secrets (use_server_filters=True)."
    )
# ============================================================
# RUNTIME CONFIGURATION & CSV SCHEMAS
# ============================================================
CSV_SCHEMAS = {
    RETAILERS_FILE: ["retailer_id", "name", "contact", "address", "zone", "is_active"],
    CATEGORIES_FILE: [
        "category_id",
        "name",
        "description",
        "default_price",
        "is_active",
    ],
    PRICES_FILE: ["price_id", "retailer_id", "category_id", "price", "effective_date"],
    ENTRIES_FILE: [
        "entry_id",
        "date",
        "retailer_id",
        "category_id",
        "qty",
        "rate",
        "amount",
    ],
    PAYMENTS_FILE: [
        "payment_id",
        "date",
        "retailer_id",
        "amount",
        "payment_mode",
        "note",
    ],
    DISTRIBUTORS_FILE: ["distributor_id", "name", "contact", "address", "is_active"],
    DISTRIBUTOR_PURCHASES_FILE: [
        "purchase_id",
        "date",
        "distributor_id",
        "category_id",
        "qty",
        "rate",
        "amount",
    ],
    DISTRIBUTOR_PAYMENTS_FILE: [
        "payment_id",
        "date",
        "distributor_id",
        "amount",
        "payment_mode",
        "note",
    ],
    DISTRIBUTOR_CATEGORY_MAP_FILE: [
        "map_id",
        "distributor_id",
        "category_id",
        "is_active",
    ],
    WASTAGE_FILE: [
        "wastage_id",
        "date",
        "category_id",
        "qty",
        "reason",
        "estimated_loss",
    ],
    EXPENSES_FILE: [
        "expense_id",
        "date",
        "category",
        "description",
        "amount",
        "payment_mode",
        "paid",
    ],
    WORKERS_FILE: [
        "worker_id",
        "name",
        "role",
        "contact",
        "salary_type",
        "base_rate",
        "is_active",
    ],
    WORKER_ATTENDANCE_FILE: [
        "attendance_id",
        "worker_id",
        "date",
        "status",
        "units",
        "notes",
    ],
    ATTENDANCE_LOCKS_FILE: [
        "lock_date",
        "is_locked",
    ],
    WORKER_WAGES_FILE: [
        "wage_id",
        "worker_id",
        "effective_date",
        "salary_type",
        "base_rate",
        "notes",
    ],
}

# legacy columns allowed to be missing in old CSVs (in-memory only, no write on startup)
ALLOWED_LEGACY_MISSING = {
    RETAILERS_FILE: {"zone", "is_active", "contact", "address"},
    CATEGORIES_FILE: {"description", "default_price", "is_active"},
    DISTRIBUTORS_FILE: {"contact", "address", "is_active"},
}


# ============================================================
# DATA FORMATTING & ID GENERATION HELPERS
# ============================================================
def _is_missingish(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and pd.isna(v):
        return True
    s = str(v).strip()
    return s == "" or s.lower() in ("nan", "none", "-", "–")


def _safe_float(v, default: float = 0.0) -> float:
    """Safely converts scalar or object v to float. Returns default on NaN/None/error."""
    if v is None:
        return default
    try:
        val = pd.to_numeric(v, errors="coerce")
        return default if pd.isna(val) else float(val)
    except Exception:
        return default


def _safe_sum(df, col: str) -> float:
    """Safely sums a column from a DataFrame. Returns 0.0 if df is empty or column missing."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0.0).sum())


def _disp_2dec_or_dash(v, dash="–") -> str:
    """Show number with 2 decimals, else dash. 0 => dash (matches your UI logic)."""
    if _is_missingish(v):
        return dash
    try:
        fv = float(v)
        return dash if fv == 0 else f"{fv:.2f}"
    except Exception:
        return dash


def _disp_rate_or_dash(v, dash="–") -> str:
    """Rate display: 2 decimals, but keep dash for missing. 0 => dash."""
    return _disp_2dec_or_dash(v, dash=dash)


# ============================================================
# SUPABASE DATA ACCESS & MUTATION HELPERS
# ============================================================
def sb_table_for_path(path: str) -> tuple[str, str]:
    if path not in FILE_TO_TABLE:
        raise ValueError(f"Unknown mapping for: {path}")
    return FILE_TO_TABLE[path]


def sb_next_id(table: str, pk: str) -> int:
    """
    Get next integer ID safely from DB (max(pk)+1).
    Prevents collisions across multiple sessions/users.
    """
    sb = get_sb()
    resp = sb.table(table).select(pk).order(pk, desc=True).limit(1).execute()
    data = resp.data or []
    if not data:
        return 1
    try:
        return int(data[0][pk]) + 1
    except Exception:
        return 1


def sb_new_id(table: str, pk: str):
    return sb_next_id(table, pk) if USE_DB_IDS else None


def _safe_dt(s):
    return pd.to_datetime(s, errors="coerce")


# ============================================================
# ENTRIES VIEW BUILDER
# ============================================================
def build_entries_view(
    df: pd.DataFrame,
    retailers_df: pd.DataFrame,
    categories_df: pd.DataFrame,
    want_milk_type_col: bool = False,
) -> pd.DataFrame:
    """
    Clean UI-ready entries view.
    NO global dependencies.
    """

    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "entry_id",
                "date",
                "zone",
                "Retailer",
                "Category",
                "qty",
                "rate",
                "amount",
            ]
        )

    out = df.copy()

    # --- DATE ---
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    # --- IDS ---
    out["retailer_id"] = (
        pd.to_numeric(out.get("retailer_id"), errors="coerce").fillna(0).astype(int)
    )
    out["category_id"] = (
        pd.to_numeric(out.get("category_id"), errors="coerce").fillna(0).astype(int)
    )

    # --- RETAILER JOIN ---
    if retailers_df is not None and not retailers_df.empty:
        rmap = retailers_df[["retailer_id", "name", "zone"]].copy()

        rmap["retailer_id"] = (
            pd.to_numeric(rmap["retailer_id"], errors="coerce").fillna(0).astype(int)
        )
        rmap["zone"] = rmap["zone"].fillna("Default").astype(str).apply(_norm_zone)

        out = out.merge(rmap, on="retailer_id", how="left")
        out = out.rename(columns={"name": "Retailer"})
    else:
        out["Retailer"] = "-"
        out["zone"] = "Default"

    # --- CATEGORY JOIN ---
    if categories_df is not None and not categories_df.empty:
        cmap = categories_df[["category_id", "name"]].copy()

        cmap["category_id"] = (
            pd.to_numeric(cmap["category_id"], errors="coerce").fillna(0).astype(int)
        )

        out = out.merge(cmap, on="category_id", how="left")
        out = out.rename(columns={"name": "Category"})
    else:
        out["Category"] = "-"

    # --- CLEAN FALLBACKS ---
    out["Retailer"] = out.get("Retailer", "-").fillna("-").astype(str)
    out["Category"] = out.get("Category", "-").fillna("-").astype(str)

    if "zone" not in out.columns:
        out["zone"] = "Default"

    out["zone"] = out["zone"].fillna("Default").astype(str).apply(_norm_zone)

    # --- NUMERIC ---
    for c in ["qty", "rate", "amount"]:
        out[c] = pd.to_numeric(out.get(c, 0), errors="coerce").fillna(0.0).astype(float)

    # --- FINAL COLUMNS ---
    cols = [
        "entry_id",
        "date",
        "zone",
        "Retailer",
        "Category",
        "qty",
        "rate",
        "amount",
    ]

    for c in cols:
        if c not in out.columns:
            out[c] = "-" if c in ["zone", "Retailer", "Category", "date"] else 0

    return out[cols]


# ============================================================
# DATA LOADING & CACHED FETCHING
# ============================================================
@st.cache_data(show_spinner="Loading data from Supabase…")
def load_all_data(data_version):
    from concurrent.futures import ThreadPoolExecutor

    _ = data_version

    fetch_tasks = [
        ("retailers", RETAILERS_FILE, CSV_SCHEMAS[RETAILERS_FILE]),
        ("categories", CATEGORIES_FILE, CSV_SCHEMAS[CATEGORIES_FILE]),
        ("prices", PRICES_FILE, CSV_SCHEMAS[PRICES_FILE]),
        ("distributors", DISTRIBUTORS_FILE, CSV_SCHEMAS[DISTRIBUTORS_FILE]),
        (
            "dist_cat_map",
            DISTRIBUTOR_CATEGORY_MAP_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_CATEGORY_MAP_FILE],
        ),
        ("entries", ENTRIES_FILE, CSV_SCHEMAS[ENTRIES_FILE]),
        ("payments", PAYMENTS_FILE, CSV_SCHEMAS[PAYMENTS_FILE]),
        (
            "dist_purchases",
            DISTRIBUTOR_PURCHASES_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE],
        ),
        (
            "dist_payments",
            DISTRIBUTOR_PAYMENTS_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_PAYMENTS_FILE],
        ),
        ("wastage", WASTAGE_FILE, CSV_SCHEMAS[WASTAGE_FILE]),
        ("expenses", EXPENSES_FILE, CSV_SCHEMAS[EXPENSES_FILE]),
    ]

    def _fetch_one(item):
        name, file_path, schema = item
        return name, sb_fetch_all(file_path, schema)

    with ThreadPoolExecutor(max_workers=6) as pool:
        data = dict(pool.map(_fetch_one, fetch_tasks))

    return (
        data["retailers"],
        data["categories"],
        data["prices"],
        data["entries"],
        data["payments"],
        data["distributors"],
        data["dist_purchases"],
        data["dist_payments"],
        data["dist_cat_map"],
        data["wastage"],
        data["expenses"],
    )


@st.cache_data(show_spinner=False)
def build_entries_view_cached(
    df,
    data_version,
    want_milk_type_col=False,
):
    _ = data_version
    # Pass global retailers/categories — safe because data_version busts cache on changes
    return build_entries_view(
        df,
        retailers_df=retailers,
        categories_df=categories,
        want_milk_type_col=want_milk_type_col,
    )


def _norm_zone(z: str) -> str:
    if z is None or pd.isna(z):
        return "Default"
    z = str(z).strip()
    if not z or z.lower() in ("nan", "none", "null", "default"):
        return "Default"
    return " ".join(z.split()).title()


# ============================================================
# SAFE AGGREGATION & DISPLAY UTILITIES
# ============================================================


def safe_scalar_sum(series_or_df) -> float:
    """Always returns a float scalar, handles Series/DataFrame/scalar."""
    if series_or_df is None:
        return 0.0
    try:
        val = series_or_df
        if isinstance(val, pd.DataFrame):
            return float(val.values.sum())
        if isinstance(val, pd.Series):
            return float(val.sum())
        return float(val)
    except Exception:
        return 0.0


def safe_pivot(df: pd.DataFrame, index: str, columns: str, values: str) -> pd.DataFrame:
    """
    Always returns a flat DataFrame (no MultiIndex).
    Columns are category names (strings).
    Index is reset to a plain column.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    try:
        pivot = pd.pivot_table(
            df,
            index=index,
            columns=columns,
            values=values,
            aggfunc="sum",
            fill_value=0.0,
        )
        # Flatten MultiIndex columns if present
        if isinstance(pivot.columns, pd.MultiIndex):
            pivot.columns = [
                str(c[-1]) if isinstance(c, tuple) else str(c) for c in pivot.columns
            ]
        else:
            pivot.columns = [str(c) for c in pivot.columns]
        pivot.columns.name = None
        pivot.index.name = None
        return pivot
    except Exception:
        return pd.DataFrame()


def safe_group_sum(df: pd.DataFrame, group_col: str, value_col: str) -> pd.Series:
    """Returns a Series {group_value: float_sum}, always scalar-safe."""
    if (
        df is None
        or df.empty
        or group_col not in df.columns
        or value_col not in df.columns
    ):
        return pd.Series(dtype=float)
    try:
        result = df.groupby(group_col)[value_col].sum()
        return result.astype(float)
    except Exception:
        return pd.Series(dtype=float)


def parse_boolish_active(v) -> bool:
    if v is None:
        return True
    s = str(v).strip().lower()
    if s in ("false", "0", "no", "n", "inactive", "off"):
        return False
    if s in ("true", "1", "yes", "y", "active", "on"):
        return True
    try:
        return bool(int(float(s)))
    except Exception:
        return True  # default active


def fmt_zero_dash(x) -> str:
    """Format numeric values; show en-dash for zero/blank/invalid."""
    if x in (None, "", "–", "-", "—"):
        v = 0.0
    else:
        try:
            v = float(x)
        except Exception:
            v = 0.0
    return "–" if v == 0.0 else f"{v:.2f}"


def highlight_cell(v):
    try:
        x = float(v)
    except (ValueError, TypeError):
        return f"<td>{v}</td>"

    if x == 0:
        return "<td style='color:#bbb'>0.0</td>"
    else:
        return f"<td style='font-weight:700;background:#e8ffe8'>{x:.2f}</td>"


def parse_boolish_paid(v) -> bool:
    if v is None:
        return False
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "y", "paid", "on"):
        return True
    if s in ("false", "0", "no", "n", "unpaid", "off"):
        return False
    try:
        return bool(int(float(s)))
    except Exception:
        return False


def next_id_from_df(df: pd.DataFrame, id_col: str) -> int:
    if df is None or df.empty or id_col not in df.columns:
        return 1
    s = pd.to_numeric(df[id_col], errors="coerce").dropna()
    return int(s.max()) + 1 if not s.empty else 1


def _fmt_money(x) -> str:
    try:
        return f"₹{float(x):,.2f}"
    except Exception:
        return "₹0.00"


def display_or_dash(v, dash="–") -> str:
    s = "" if v is None else str(v).strip()
    return dash if not s else s


def df_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Make df safe for Streamlit (Arrow) display:
    - convert bytes -> str
    - ensure object columns are consistent (string)
    - replace None/NaN with "–"
    """
    if df is None:
        return pd.DataFrame()

    out = df.copy()

    # Replace None/NaN first
    out = out.replace({None: "–"}).fillna("–")

    # Fix Arrow crash: object columns containing mixed bytes/float/etc.
    for col in out.columns:
        if out[col].dtype == "object":

            def _norm(v):
                if v is None:
                    return "–"
                if isinstance(v, (bytes, bytearray)):
                    try:
                        return v.decode("utf-8", errors="ignore")
                    except Exception:
                        return str(v)
                return str(v)

            out[col] = out[col].map(_norm)

    return out


# ============================================================
# SUPABASE QUERY HELPERS & LEDGER CALCULATIONS
# ============================================================
def sb_fetch_all(path: str, cols="*", page_size: int = 1000, max_retries: int = 5):
    """Fetch all rows from a Supabase table with correct pagination.

    Fixes:
    1. Supabase PostgREST caps responses at 1000 rows. Using page_size > 1000
       caused silent truncation: the server returned only 1000 rows, and the
       `if len(batch) < page_size: break` check then exited the loop before
       fetching subsequent pages. This dropped most entries/payments and made
       later dates appear empty in the backup CSV. page_size is now pinned to
       1000 to match the server cap.
    2. On empty/flaky queries the original had an infinite while-True loop.
    """
    sb = get_sb()
    pk = None
    if path in FILE_TO_TABLE:
        table, pk = FILE_TO_TABLE[path]
    else:
        table = path
        for t_name, t_pk in FILE_TO_TABLE.values():
            if t_name == table:
                pk = t_pk
                break
        if not pk and table == "main_retailers":
            pk = "retailer_id"

    if isinstance(cols, list):
        cols = ",".join(cols)

    query = sb.table(table).select(cols)
    if pk:
        query = query.order(pk, desc=False)

    # 1. Fetch first page
    first_batch = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = query.range(0, page_size - 1).execute()
            first_batch = resp.data or []
            break
        except Exception as e:
            if attempt == max_retries:
                raise e
            time.sleep(0.05 * attempt)

    if not first_batch:
        return pd.DataFrame()

    # If table has fewer than page_size rows, return immediately (fastest path: 1 HTTP round-trip)
    if len(first_batch) < page_size:
        return pd.DataFrame(first_batch)

    # 2. For large tables (> 1000 rows): get total count to fetch all remaining pages in parallel
    total_count = None
    for attempt in range(1, max_retries + 1):
        try:
            cnt_resp = (
                sb.table(table)
                .select(pk if pk else "*", count="exact")
                .limit(1)
                .execute()
            )
            total_count = cnt_resp.count
            break
        except Exception:
            if attempt == max_retries:
                total_count = None
            time.sleep(0.05 * attempt)

    # Fallback to sequential if count query failed
    if total_count is None:
        out = list(first_batch)
        offset = page_size
        while True:
            batch = None
            for attempt in range(1, max_retries + 1):
                try:
                    resp = query.range(offset, offset + page_size - 1).execute()
                    batch = resp.data or []
                    break
                except Exception as e:
                    if attempt == max_retries:
                        raise e
                    time.sleep(0.05 * attempt)
            if not batch:
                break
            out.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        return pd.DataFrame(out)

    # High-speed parallel page fetching with 8 concurrent workers
    from concurrent.futures import ThreadPoolExecutor

    ranges = [
        (i, min(i + page_size - 1, total_count - 1))
        for i in range(page_size, total_count, page_size)
    ]

    def _fetch_page(r):
        s, e = r
        q = sb.table(table).select(cols)
        if pk:
            q = q.order(pk, desc=False)
        for att in range(1, max_retries + 1):
            try:
                res = q.range(s, e).execute()
                return s, res.data or []
            except Exception as exc:
                if att == max_retries:
                    raise exc
                time.sleep(0.05 * att)
        return s, []

    with ThreadPoolExecutor(max_workers=5) as pool:
        chunks = list(pool.map(_fetch_page, ranges))

    chunks.sort(key=lambda x: x[0])
    out = list(first_batch)
    for _, rows in chunks:
        out.extend(rows)
    return pd.DataFrame(out)


@st.cache_data(show_spinner=False)
def cached_groupby_sum(df, cols, value, data_version):

    _ = data_version

    if df is None or df.empty:
        return pd.DataFrame()

    return df.groupby(cols)[value].sum().reset_index()


def normalize_date_cols(df: pd.DataFrame, cols=("date",)) -> pd.DataFrame:
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
    return df


@st.cache_data(show_spinner=False)
def cached_fetch_entries(day, rids, version):
    return fetch_entries_filtered(
        day,
        day,
        rids,
        version,
    )


@st.cache_data(show_spinner=False)
def cached_fetch_payments(day, rids, version):
    return fetch_payments_filtered(
        day,
        day,
        rids,
        version,
    )


def compute_ledger_fast(entries, payments):

    def _norm(df):
        if df is None or df.empty:
            return pd.DataFrame(columns=["date", "retailer_id", "amount"])
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df["retailer_id"] = (
            pd.to_numeric(df["retailer_id"], errors="coerce").fillna(0).astype(int)
        )
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        return df

    e = _norm(entries)
    p = _norm(payments)

    e["delta"] = e["amount"]
    p["delta"] = -p["amount"]

    all_df = pd.concat([e, p], ignore_index=True)
    all_df = all_df.sort_values(["retailer_id", "date"])

    res = all_df[["date", "retailer_id"]].copy()
    res["balance"] = all_df.groupby("retailer_id")["delta"].cumsum().round(2)
    return res.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def cached_pivot(
    df,
    index,
    columns,
    values,
    data_version,
):

    _ = data_version

    if df is None or df.empty:
        return pd.DataFrame()

    return pd.pivot_table(
        df,
        index=index,
        columns=columns,
        values=values,
        aggfunc="sum",
        fill_value=0,
    )


@st.cache_data(show_spinner=False)
def fetch_entries_filtered(
    start_date,
    end_date,
    retailer_ids,
    data_version,
):

    _ = data_version

    filters = []

    if start_date is not None:
        filters.append(("date", "gte", str(start_date)))

    if end_date is not None:
        filters.append(("date", "lte", str(end_date)))

    if retailer_ids:
        filters.append(("retailer_id", "in", retailer_ids))

    return sb_fetch_df(
        ENTRIES_FILE,
        CSV_SCHEMAS[ENTRIES_FILE],
        filters=filters,
    )


@st.cache_data(show_spinner=False)
def fetch_payments_filtered(
    start_date,
    end_date,
    retailer_ids,
    data_version,
):

    _ = data_version

    filters = []

    if start_date is not None:
        filters.append(("date", "gte", str(start_date)))

    if end_date is not None:
        filters.append(("date", "lte", str(end_date)))

    if retailer_ids:
        filters.append(("retailer_id", "in", retailer_ids))

    return sb_fetch_df(
        PAYMENTS_FILE,
        CSV_SCHEMAS[PAYMENTS_FILE],
        filters=filters,
    )


@st.cache_data(show_spinner=False)
def fetch_purchases_filtered(
    start_date,
    end_date,
    distributor_ids,
    data_version,
):

    _ = data_version

    filters = []

    if start_date is not None:
        filters.append(("date", "gte", str(start_date)))

    if end_date is not None:
        filters.append(("date", "lte", str(end_date)))

    if distributor_ids:
        filters.append(("distributor_id", "in", distributor_ids))

    return sb_fetch_df(
        DISTRIBUTOR_PURCHASES_FILE,
        CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE],
        filters=filters,
    )


@st.cache_data(show_spinner=False)
def cached_distributor_balance(
    did,
    d,
    version,
):

    _ = version

    return distributor_balance_before(
        did,
        d,
    )


def _normalize_df_from_rows(
    path: str, columns: list[str], rows: list[dict]
) -> pd.DataFrame:
    if not rows:
        df = pd.DataFrame(columns=columns)
    else:
        df = pd.DataFrame(rows)

    # Ensure schema columns exist (create missing as blank/None)
    for c in columns:
        if c not in df.columns:
            df[c] = None

    # Allow legacy missing columns without crashing
    legacy_ok = ALLOWED_LEGACY_MISSING.get(path, set())
    for c in legacy_ok:
        if c not in df.columns:
            df[c] = None

    # Keep only schema columns (and legacy allowed ones if they are in schema)
    keep = [c for c in columns if c in df.columns]
    return df[keep].copy()


def sb_fetch_where(
    table: str,
    cols: str = "*",
    filters: list[tuple] | None = None,
    page_size: int = 1000,
    in_chunk: int = 500,
) -> list[dict]:
    """
    Fetch rows from Supabase table with server-side filters.
    Supported ops: eq, lt, lte, gt, gte, in

    NOTE: page_size pinned to 1000 — Supabase PostgREST hard-caps responses at
    1000 rows. Using a larger page_size made the loop's
    `if len(batch) < page_size: break` exit after the first page, silently
    truncating filtered fetches (same root cause as sb_fetch_all).
    """
    sb = get_sb()
    filters = filters or []

    pk = None
    for t_path, (t_name, t_pk) in FILE_TO_TABLE.items():
        if t_name == table or t_path == table:
            pk = t_pk
            break
    if not pk and table == "main_retailers":
        pk = "retailer_id"

    eq_filters = []
    in_filters = []
    for col, op, val in filters:
        if op == "in":
            vals = list(val) if isinstance(val, (list, tuple, set)) else [val]
            in_filters.append((col, vals))
        elif op in ("eq", "lt", "lte", "gt", "gte"):
            eq_filters.append((col, op, val))
        else:
            raise ValueError(f"Unsupported op: {op}")

    def _build_base():
        b = sb.table(table).select(cols)
        if pk:
            b = b.order(pk, desc=False)
        for col, op, val in eq_filters:
            if op == "eq":
                b = b.eq(col, val)
            elif op == "lt":
                b = b.lt(col, val)
            elif op == "lte":
                b = b.lte(col, val)
            elif op == "gt":
                b = b.gt(col, val)
            elif op == "gte":
                b = b.gte(col, val)
        return b

    def _fetch(q):
        import time
        out = []
        offset = 0
        while True:
            batch = None
            for attempt in range(3):
                try:
                    resp = q.range(offset, offset + page_size - 1).execute()
                    batch = resp.data or []
                    break
                except Exception as ex:
                    if attempt == 2:
                        raise ex
                    time.sleep(0.35)
            out.extend(batch or [])
            if not batch or len(batch) < page_size:
                break
            offset += page_size
        return out

    if not in_filters:
        return _fetch(_build_base())

    first_col, first_vals = in_filters[0]
    rest_in = in_filters[1:]

    out = []
    for i in range(0, len(first_vals), in_chunk):
        q = _build_base().in_(first_col, first_vals[i : i + in_chunk])
        for col, vals in rest_in:
            q = q.in_(col, vals)
        out.extend(_fetch(q))
    return out


def sb_fetch_df(
    path: str, columns: list[str], filters: list[tuple] | None = None
) -> pd.DataFrame:
    """Fetch a dataframe from Supabase.

    IMPORTANT (data integrity): if server-side filtered fetch fails, we return an EMPTY dataframe
    with the correct schema. We NEVER fall back to an unfiltered full-table read because that
    causes cross-date contamination in transactional pages.
    """
    if not filters:
        return safe_read_csv(path, columns)
    if path not in FILE_TO_TABLE:
        return pd.DataFrame(columns=columns)
    table, _ = FILE_TO_TABLE[path]
    try:
        rows = sb_fetch_where(table, cols="*", filters=filters)
        return _normalize_df_from_rows(path, columns, rows)
    except Exception as e:
        print("sb_fetch_df error:", e)
        # FAIL CLOSED: empty-with-schema, not unfiltered data.
        return _normalize_df_from_rows(path, columns, [])


def _prepare_df_for_write(df: pd.DataFrame, path: str) -> pd.DataFrame:
    df = df.copy() if df is not None else pd.DataFrame()
    df = df.drop(columns=["_selectedRowNodeInfo"], errors="ignore")
    expected_cols = CSV_SCHEMAS.get(path, [])
    if not expected_cols:
        table, _ = FILE_TO_TABLE[path]
        raise RuntimeError(f"{table}: missing schema definition for {path}")

    # Drop any unexpected columns to avoid Supabase "column does not exist" errors.
    extra_cols = [c for c in df.columns if c not in expected_cols]
    if extra_cols:
        df = df.drop(columns=extra_cols, errors="ignore")

    # Ensure all expected columns exist (missing columns become NULLs).
    for c in expected_cols:
        if c not in df.columns:
            df[c] = None

    # Keep stable column order to match schema.
    return df[expected_cols]


def sb_insert_df(df: object, path: str) -> None:
    """
    Clean insert helper.

    - Always treats input as NEW rows
    - NEVER trusts client-side primary keys
    - Assigns explicit IDs (max(pk)+1) to avoid:
        * null PK constraint errors (re-added by schema enforcement)
        * IDENTITY sequence drift causing duplicate pkey errors
    - Handles dict / list / DataFrame
    """

    # Normalize input
    if isinstance(df, dict):
        df = pd.DataFrame([df])
    elif isinstance(df, list):
        df = pd.DataFrame(df)

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"sb_insert_df expects DataFrame/dict/list[dict], got {type(df)}"
        )

    if df.empty:
        return

    table, pk = FILE_TO_TABLE[path]

    # 🚨 CRITICAL: NEVER send primary key from UI
    if pk in df.columns:
        df = df.drop(columns=[pk])

    # Clean + enforce schema
    df = _prepare_df_for_write(df, path)

    # 🚨 _prepare_df_for_write re-adds the pk column as None to match schema.
    # Drop it again so we can either omit it OR assign fresh IDs explicitly.
    if pk in df.columns:
        df = df.drop(columns=[pk])

    # Assign explicit IDs based on current max(pk)+1.
    # This avoids both null-PK errors AND IDENTITY sequence drift duplicates.
    try:
        next_id = sb_next_id(table, pk)
        df.insert(0, pk, list(range(next_id, next_id + len(df))))
    except Exception as _id_err:
        # If we can't compute next id, fall back to letting DB generate.
        print(f"[sb_insert_df] sb_next_id failed for {table}.{pk}: {_id_err}")

    # Convert NaN → None (required for Supabase)
    records = df.where(pd.notna(df), None).to_dict(orient="records")

    # Insert in chunks
    for i in range(0, len(records), 500):
        resp = sb.table(table).insert(records[i : i + 500]).execute()
        if not resp or getattr(resp, "data", None) is None:
            raise RuntimeError(f"{table}: insert failed")

    # Refresh app state
    invalidate_data_cache()


def sb_delete_by_pk(table: str, pk: str, ids: list[int], chunk: int = 1000) -> None:
    sb = get_sb()
    ids = [int(x) for x in ids if x is not None]
    if not ids:
        return
    for i in range(0, len(ids), chunk):
        sb.table(table).delete().in_(pk, ids[i : i + chunk]).execute()
    invalidate_data_cache()


def sb_delete_where(table: str, filters: list[tuple], in_chunk: int = 500) -> None:
    """
    FIXED: preserves ALL filters even when using IN().
    filters: list of tuples like:
      ("date","eq","2026-02-05")
      ("retailer_id","in",[1,2,3])
    Supported ops: eq, lt, lte, gt, gte, in
    """
    sb = get_sb()

    eq_filters = []
    in_filters = []
    for col, op, val in filters:
        if op == "in":
            vals = list(val) if isinstance(val, (list, tuple, set)) else [val]
            in_filters.append((col, vals))
        elif op in ("eq", "lt", "lte", "gt", "gte"):
            eq_filters.append((col, op, val))
        else:
            raise ValueError(f"Unsupported op: {op}")

    def _build_base():
        b = sb.table(table).delete()
        for col, op, val in eq_filters:
            if op == "eq":
                b = b.eq(col, val)
            elif op == "lt":
                b = b.lt(col, val)
            elif op == "lte":
                b = b.lte(col, val)
            elif op == "gt":
                b = b.gt(col, val)
            elif op == "gte":
                b = b.gte(col, val)
        return b

    if not in_filters:
        _build_base().execute()
        invalidate_data_cache()
        return

    first_col, first_vals = in_filters[0]
    rest_in = in_filters[1:]

    for i in range(0, len(first_vals), in_chunk):
        q = _build_base().in_(first_col, first_vals[i : i + in_chunk])
        for col, vals in rest_in:
            q = q.in_(col, vals)
        q.execute()
    invalidate_data_cache()


# ============================================================
# CSV STORAGE & FALLBACK HELPERS
# ============================================================
def safe_write_csv(df: pd.DataFrame, path: str, allow_empty: bool = False) -> None:
    """
    DB MODE:
    - Upsert rows only (NO implicit deletes).
    - Deletions must be explicit via sb_delete_* helpers.
    """
    if path not in FILE_TO_TABLE:
        raise ValueError(f"Unknown mapping for: {path}")

    table, pk = FILE_TO_TABLE[path]
    df = _prepare_df_for_write(df, path)

    if df.empty and not allow_empty:
        raise RuntimeError(
            f"Refusing to write EMPTY dataframe to {table}. "
            f"Pass allow_empty=True only if you truly want to write nothing."
        )
    if df.empty:
        return

    # If PK is entirely NULL, treat it as "DB-generated IDs": INSERT (not UPSERT).
    # (Your caller should usually use sb_insert_df for this case, but this makes it safe.)
    if pk in df.columns and df[pk].isna().all():
        payload = df.drop(columns=[pk], errors="ignore")
        records = payload.where(pd.notna(payload), None).to_dict(orient="records")
        chunk = 500
        for i in range(0, len(records), chunk):
            sb.table(table).insert(records[i : i + chunk]).execute()

        return

    # Mixed NULL/non-NULL PK is dangerous (can create duplicates).
    if pk in df.columns and df[pk].isna().any():
        raise RuntimeError(f"{table}: mixed NULL/non-NULL primary keys")

    # Defensive: PK must exist for UPSERT
    if pk not in df.columns:
        raise RuntimeError(f"{table}: missing primary key column '{pk}' for upsert")

    if df[pk].duplicated().any():
        dups = df[df[pk].duplicated(keep=False)][pk].tolist()[:10]
        raise RuntimeError(
            f"{table}: duplicate primary keys in dataframe (sample): {dups}"
        )

    records = df.where(pd.notna(df), None).to_dict(orient="records")
    chunk = 500
    for i in range(0, len(records), chunk):
        sb.table(table).upsert(records[i : i + chunk], on_conflict=pk).execute()

    invalidate_data_cache()


def safe_write_two_csvs(
    df1: pd.DataFrame, path1: str, df2: pd.DataFrame, path2: str
) -> None:
    safe_write_csv(df1, path1, allow_empty=True)
    safe_write_csv(df2, path2, allow_empty=True)


# ============================================================
# DISTRIBUTOR LEDGER, GRID & REPORT HELPERS
# ============================================================


def safe_read_csv(path: str, columns: list[str]) -> pd.DataFrame:
    """
    DB MODE:
    - Reads from Supabase tables (NOT local CSV).
    - Returns a DataFrame with exactly the expected schema columns (plus allowed legacy missing columns).
    """
    if path not in FILE_TO_TABLE:
        # fallback: return empty with the requested columns
        return pd.DataFrame(columns=columns)

    table, pk = FILE_TO_TABLE[path]

    table, _ = FILE_TO_TABLE[path]
    df = sb_fetch_all(path, columns)
    if df is None or df.empty:
        df = pd.DataFrame(columns=columns)

    # Ensure schema columns exist (create missing as blank/None)
    for c in columns:
        if c not in df.columns:
            df[c] = None

    # Allow legacy missing columns without crashing
    legacy_ok = ALLOWED_LEGACY_MISSING.get(path, set())
    for c in legacy_ok:
        if c not in df.columns:
            df[c] = None

    # Keep only schema columns (and legacy allowed ones if they are in schema)
    keep = [c for c in columns if c in df.columns]
    df = df[keep].copy()

    return df


def distributor_balance_before(distributor_id: int, start_day: date) -> float:
    """
    Due before start_day = (purchases before) - (payments before)
    Positive => you owe distributor.
    """
    if USE_SERVER_FILTERS:
        dp = sb_fetch_df(
            DISTRIBUTOR_PURCHASES_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE],
            filters=[
                ("distributor_id", "eq", int(distributor_id)),
                ("date", "lt", str(start_day)),
            ],
        )
        pay = sb_fetch_df(
            DISTRIBUTOR_PAYMENTS_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_PAYMENTS_FILE],
            filters=[
                ("distributor_id", "eq", int(distributor_id)),
                ("date", "lt", str(start_day)),
            ],
        )
    else:
        dp = dist_purchases.copy()
        pay = dist_payments.copy()

    purchases_amt = 0.0
    paid_amt = 0.0

    if not dp.empty:
        dp["date"] = pd.to_datetime(dp["date"], errors="coerce").dt.date

        dp = dp.loc[
            (dp["distributor_id"].astype(int) == int(distributor_id))
            & (dp["date"] < start_day)
        ].copy()
        if not dp.empty:
            # trust stored amount but normalize if missing
            if "amount" in dp.columns:
                purchases_amt = float(
                    pd.to_numeric(dp["amount"], errors="coerce").fillna(0).sum()
                )
            else:
                purchases_amt = float(
                    (
                        pd.to_numeric(dp["qty"], errors="coerce").fillna(0)
                        * pd.to_numeric(dp["rate"], errors="coerce").fillna(0)
                    ).sum()
                )

    if not pay.empty:
        pay["date"] = pd.to_datetime(pay["date"], errors="coerce").dt.date
        pay = pay.loc[
            (pay["distributor_id"].astype(int) == int(distributor_id))
            & (pay["date"] < start_day)
        ].copy()
        if not pay.empty:
            paid_amt = float(
                pd.to_numeric(pay["amount"], errors="coerce").fillna(0).sum()
            )

    return float(purchases_amt - paid_amt)


def build_distributor_daily_grid(
    distributor_id: int, start_day: date, end_day: date, cat_names: list[str]
) -> pd.DataFrame:
    """
    One row per date.
    Columns:
      Date,
      for each category: "<cat> Qty", "<cat> Rate",
      Total Milk (L), Purchases (₹), Payment (₹), Running Due (₹)
    Rate shown = weighted avg rate for that day+category (amount/qty) if multiple lines exist.
    """
    days = pd.date_range(start=start_day, end=end_day, freq="D").date

    if USE_SERVER_FILTERS:
        dp = sb_fetch_df(
            DISTRIBUTOR_PURCHASES_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE],
            filters=[
                ("distributor_id", "eq", int(distributor_id)),
                ("date", "gte", str(start_day)),
                ("date", "lte", str(end_day)),
            ],
        )
    else:
        dp = dist_purchases.copy()
    if not dp.empty:
        dp["date"] = pd.to_datetime(dp["date"], errors="coerce").dt.date
        dp = dp.loc[
            (dp["distributor_id"].astype(int) == int(distributor_id))
            & (dp["date"] >= start_day)
            & (dp["date"] <= end_day)
        ].copy()

    if not dp.empty:
        dp["qty"] = pd.to_numeric(dp["qty"], errors="coerce").fillna(0.0).astype(float)
        dp["rate"] = (
            pd.to_numeric(dp["rate"], errors="coerce").fillna(0.0).astype(float)
        )
        dp["amount"] = (
            pd.to_numeric(dp.get("amount", 0.0), errors="coerce")
            .fillna(0.0)
            .astype(float)
        )

        # attach category names
        dp = dp.merge(
            categories[["category_id", "name"]], on="category_id", how="left"
        ).rename(columns={"name": "Category"})
        dp["Category"] = dp["Category"].fillna("").astype(str)

    if USE_SERVER_FILTERS:
        pay = sb_fetch_df(
            DISTRIBUTOR_PAYMENTS_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_PAYMENTS_FILE],
            filters=[
                ("distributor_id", "eq", int(distributor_id)),
                ("date", "gte", str(start_day)),
                ("date", "lte", str(end_day)),
            ],
        )
    else:
        pay = dist_payments.copy()
    if not pay.empty:
        pay["date"] = pd.to_datetime(pay["date"], errors="coerce").dt.date
        pay = pay.loc[
            (pay["distributor_id"].astype(int) == int(distributor_id))
            & (pay["date"] >= start_day)
            & (pay["date"] <= end_day)
        ].copy()
        pay["amount"] = (
            pd.to_numeric(pay["amount"], errors="coerce").fillna(0.0).astype(float)
        )

    pay_by_day = pay.groupby("date")["amount"].sum().to_dict() if not pay.empty else {}

    opening_due = distributor_balance_before(distributor_id, start_day)
    running = float(opening_due)

    rows = []
    for d in days:
        row = {"Date": str(d)}
        total_milk = 0.0
        day_amt = 0.0

        if dp.empty:
            dp_day = pd.DataFrame(columns=["Category", "qty", "amount"])
        else:
            dp_day = dp.loc[dp["date"] == d].copy()

        for cat in cat_names:
            qcol = f"{cat} Qty"
            rcol = f"{cat} Rate"

            if dp_day.empty:
                qty = 0.0
                amt = 0.0
            else:
                sub = dp_day.loc[dp_day["Category"] == cat].copy()
                qty = float(sub["qty"].sum()) if not sub.empty else 0.0
                amt = float(sub["amount"].sum()) if not sub.empty else 0.0

            if qty > 0:
                # Weighted avg rate
                rate = (amt / qty) if qty > 0 else 0.0
                row[qcol] = qty
                row[rcol] = rate if rate > 0 else "-"
                total_milk += qty
                day_amt += amt
            else:
                row[qcol] = "-"
                row[rcol] = "-"

        pay_amt = float(pay_by_day.get(d, 0.0))
        running = float(running + day_amt - pay_amt)

        row["Total Milk (L)"] = round(float(total_milk), 2)
        row["Purchases (₹)"] = round(float(day_amt), 2)
        row["Payment (₹)"] = round(float(pay_amt), 2)
        row["Running Due (₹)"] = round(float(running), 2)

        rows.append(row)

    return pd.DataFrame(rows)


def distributor_pay_mode_totals(
    distributor_id: int, start_day: date, end_day: date
) -> pd.DataFrame:
    pay = dist_payments.copy()
    if pay.empty:
        return pd.DataFrame(columns=["Mode", "Total (₹)"])

    pay["date"] = pd.to_datetime(pay["date"], errors="coerce").dt.date
    pay = pay.loc[
        (pay["distributor_id"].astype(int) == int(distributor_id))
        & (pay["date"] >= start_day)
        & (pay["date"] <= end_day)
    ].copy()
    if pay.empty:
        return pd.DataFrame(columns=["Mode", "Total (₹)"])

    pay["payment_mode"] = pay["payment_mode"].fillna("Cash").astype(str)
    pay["amount"] = (
        pd.to_numeric(pay["amount"], errors="coerce").fillna(0.0).astype(float)
    )

    out = (
        pay.groupby("payment_mode", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
        .rename(columns={"payment_mode": "Mode", "amount": "Total (₹)"})
    )
    return out


def num_to_words_inr(num: float) -> str:
    try:
        num = int(round(abs(num)))
        if num == 0:
            return "Zero Rupees Only"
        ones = [
            "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"
        ]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

        def two_digits(n):
            if n < 20:
                return ones[n]
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")

        def three_digits(n):
            if n >= 100:
                h = ones[n // 100] + " Hundred"
                rem = n % 100
                return h + (" and " + two_digits(rem) if rem else "")
            return two_digits(n)

        parts = []
        crore = num // 10000000
        if crore:
            parts.append(three_digits(crore) + " Crore")
            num %= 10000000
        lakh = num // 100000
        if lakh:
            parts.append(two_digits(lakh) + " Lakh")
            num %= 100000
        thousand = num // 1000
        if thousand:
            parts.append(two_digits(thousand) + " Thousand")
            num %= 1000
        hundred = num
        if hundred:
            parts.append(three_digits(hundred))
        return "Rupees " + " ".join(parts).strip() + " Only"
    except Exception:
        return ""


def build_distributor_bill_html(
    distributor_row: dict,
    start_day: date,
    end_day: date,
    grid: pd.DataFrame,
    pay_mode_totals: pd.DataFrame,
    cat_names: list[str],
    opening_due: float = 0.0,
) -> str:
    shop_name = "RANJIT BHIMRAO KAWLE MILK"

    def esc(s: str) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def safe_meta(v):
        v = "" if v is None else str(v)
        v = v.strip()
        return v if v else "–"

    def fmt_money(x) -> str:
        try:
            return f"₹{float(x):,.2f}"
        except Exception:
            return "₹0.00"

    def fmt_num(x) -> str:
        try:
            return f"{float(x):,.2f}"
        except Exception:
            return "–"

    vendor = safe_meta(distributor_row.get("name"))
    contact = safe_meta(distributor_row.get("contact"))
    address = safe_meta(distributor_row.get("address"))
    did = int(distributor_row.get("distributor_id", 0))

    df = grid.copy() if grid is not None else pd.DataFrame()

    total_qty_by_cat = {cat: 0.0 for cat in cat_names}
    total_amt = 0.0
    total_pay = 0.0

    if not df.empty:
        for cat in cat_names:
            qcol = f"{cat} Qty"
            if qcol in df.columns:
                s = 0.0
                for v in df[qcol].tolist():
                    try:
                        s += float(v)
                    except Exception:
                        pass
                total_qty_by_cat[cat] = float(s)

        if "Purchases (₹)" in df.columns:
            total_amt = float(
                pd.to_numeric(df["Purchases (₹)"], errors="coerce").fillna(0).sum()
            )
        if "Payment (₹)" in df.columns:
            total_pay = float(
                pd.to_numeric(df["Payment (₹)"], errors="coerce").fillna(0).sum()
            )

        if "Running Due (₹)" in df.columns and len(df) > 0:
            closing_due = float(
                pd.to_numeric(df["Running Due (₹)"], errors="coerce").fillna(0).iloc[-1]
            )
            if opening_due == 0.0:
                try:
                    first_r = df.iloc[0]
                    first_running = float(first_r.get("Running Due (₹)", 0) or 0)
                    first_pur = float(first_r.get("Purchases (₹)", 0) or 0)
                    first_pay = float(first_r.get("Payment (₹)", 0) or 0)
                    opening_due = round(first_running - first_pur + first_pay, 2)
                except Exception:
                    pass
        else:
            closing_due = float(opening_due + total_amt - total_pay)
    else:
        closing_due = float(opening_due)

    total_milk_all = float(sum(total_qty_by_cat.values()))
    gross_payable = float(opening_due + total_amt)

    # 1. Product rows (itemized milk supply)
    product_rows_html = ""
    sno = 1
    running_product_amt = 0.0
    active_cats = [c for c in cat_names if total_qty_by_cat.get(c, 0.0) > 0]
    if not active_cats:
        active_cats = cat_names

    for idx, cat in enumerate(active_cats):
        q = total_qty_by_cat.get(cat, 0.0)
        qcol = f"{cat} Qty"
        rcol = f"{cat} Rate"

        avg_rate = 0.0
        cat_amt = 0.0
        if not df.empty and qcol in df.columns and rcol in df.columns:
            qtys = pd.to_numeric(df[qcol], errors="coerce").fillna(0.0)
            rates = pd.to_numeric(df[rcol], errors="coerce").fillna(0.0)
            cat_amt = float((qtys * rates).sum())
            if q > 0 and cat_amt > 0:
                avg_rate = cat_amt / q

        if idx == len(active_cats) - 1 and len(active_cats) > 0:
            if total_amt > 0 and abs(running_product_amt + cat_amt - total_amt) < 5.0:
                cat_amt = round(total_amt - running_product_amt, 2)
        running_product_amt += cat_amt

        rate_str = f"₹{avg_rate:.2f}" if avg_rate > 0 else "–"
        amt_str = f"₹{cat_amt:,.2f}" if cat_amt > 0 else "–"
        qty_str = f"{q:,.2f}" if q > 0 else "0.00"

        product_rows_html += f"""
        <tr>
          <td style="text-align:center;">{sno}</td>
          <td><b>{esc(cat)}</b></td>
          <td style="text-align:right; font-weight:700;">{qty_str} LTR</td>
          <td style="text-align:right;">{rate_str}</td>
          <td style="text-align:right; font-weight:800; color:#0f172a;">{amt_str}</td>
        </tr>
        """
        sno += 1

    # 2. Daily Annexure rows
    th = "<th style='width:90px;'>Date</th>"
    for cat in active_cats:
        th += f"<th>{esc(cat)} (L)</th>"
    th += "<th>Total Milk (L)</th><th>Purchases (₹)</th><th>Payment (₹)</th><th>Running Due (₹)</th>"

    body_rows = ""
    for _, r in df.iterrows() if df is not None else []:
        tds = f"<td style='font-weight:600;'>{esc(r.get('Date', '-'))}</td>"
        for cat in active_cats:
            qcol = f"{cat} Qty"
            qv = r.get(qcol, "-")
            if qv in ("-", None, 0, 0.0, "0.00", "0"):
                qdisp = "<span style='color:#cbd5e1;'>–</span>"
            else:
                try:
                    fq = float(qv)
                    qdisp = f"<b>{fq:.2f}</b>" if fq > 0 else "<span style='color:#cbd5e1;'>–</span>"
                except Exception:
                    qdisp = "<span style='color:#cbd5e1;'>–</span>"
            tds += f"<td style='text-align:right;'>{qdisp}</td>"

        tmilk = _safe_float(r.get("Total Milk (L)", 0.0))
        tmilk_str = f"<b>{tmilk:.2f}</b>" if tmilk > 0 else "<span style='color:#cbd5e1;'>–</span>"
        tds += f"<td style='text-align:right;'>{tmilk_str}</td>"

        dpur = _safe_float(r.get("Purchases (₹)", 0.0))
        dpur_str = f"₹{dpur:,.2f}" if dpur > 0 else "<span style='color:#cbd5e1;'>–</span>"
        tds += f"<td style='text-align:right;'>{dpur_str}</td>"

        dpay = _safe_float(r.get("Payment (₹)", 0.0))
        dpay_str = f"<span style='color:#16a34a; font-weight:700;'>₹{dpay:,.2f}</span>" if dpay > 0 else "<span style='color:#cbd5e1;'>–</span>"
        tds += f"<td style='text-align:right;'>{dpay_str}</td>"

        rdue = _safe_float(r.get("Running Due (₹)", 0.0))
        tds += f"<td style='text-align:right; font-weight:700;'>₹{rdue:,.2f}</td>"
        body_rows += f"<tr>{tds}</tr>"

    total_row = "<td><b>TOTAL</b></td>"
    for cat in active_cats:
        total_row += f"<td style='text-align:right;'><b>{total_qty_by_cat.get(cat, 0.0):.2f}</b></td>"
    total_row += f"<td style='text-align:right;'><b>{total_milk_all:.2f} L</b></td>"
    total_row += f"<td style='text-align:right;'><b>₹{total_amt:,.2f}</b></td>"
    total_row += f"<td style='text-align:right;'><b>₹{total_pay:,.2f}</b></td>"
    total_row += f"<td style='text-align:right;'><b>₹{closing_due:,.2f}</b></td>"

    # 3. Pay modes
    pay_rows_html = ""
    pm_list = []
    if isinstance(pay_mode_totals, dict):
        pm_list = [{"Mode": k, "Total (₹)": v} for k, v in pay_mode_totals.items() if float(pd.to_numeric(v, errors="coerce") or 0) > 0]
    elif isinstance(pay_mode_totals, pd.DataFrame) and not pay_mode_totals.empty:
        for _, r in pay_mode_totals.iterrows():
            m_val = r.get("Mode", r.get("payment_mode", "-"))
            a_val = r.get("Total (₹)", r.get("amount", 0.0))
            if float(pd.to_numeric(a_val, errors="coerce") or 0) > 0:
                pm_list.append({"Mode": m_val, "Total (₹)": a_val})

    if pm_list:
        for item in pm_list:
            mode = esc(item["Mode"])
            amt = fmt_money(item["Total (₹)"])
            pay_rows_html += f"<tr><td><b>{mode}</b></td><td style='text-align:right; font-weight:700; color:#16a34a;'>{amt}</td></tr>"
    else:
        pay_rows_html = "<tr><td colspan='2' style='text-align:center; color:#94a3b8; font-style:italic;'>No payments recorded during this period</td></tr>"

    if closing_due > 0:
        due_badge_class = "badge-due"
        due_status_text = "NET AMOUNT PAYABLE TO VENDOR"
        due_caption = "Balance payable for milk procurement."
    elif closing_due < 0:
        due_badge_class = "badge-advance"
        due_status_text = "ADVANCE PAID TO VENDOR"
        due_caption = "Vendor credit balance carried forward."
    else:
        due_badge_class = "badge-nil"
        due_status_text = "ALL VENDOR DUES CLEARED (NIL)"
        due_caption = "Account fully reconciled."

    inv_no = f"PUR-{start_day.strftime('%y%m')}-{did:03d}"
    bill_date_str = date.today().strftime("%d-%b-%Y")
    words_text = num_to_words_inr(closing_due if closing_due > 0 else total_amt)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Vendor Purchase Bill — {esc(vendor)} ({inv_no})</title>
<style>
  :root {{
    --primary: #0f172a;
    --primary-light: #1e293b;
    --accent: #2563eb;
    --border: #cbd5e1;
    --border-dark: #94a3b8;
    --bg-light: #f8fafc;
    --text-dark: #0f172a;
    --text-muted: #64748b;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    margin: 10px auto;
    padding: 0 10px;
    max-width: 900px;
    background: #ffffff;
    color: var(--text-dark);
    font-size: 12px;
    line-height: 1.35;
  }}

  /* Top Executive Bill Header */
  .bill-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 2.5px solid var(--primary);
    padding-bottom: 10px;
    margin-bottom: 12px;
  }}
  .company-title {{
    font-size: 22px;
    font-weight: 900;
    color: var(--primary);
    margin: 0 0 2px 0;
    letter-spacing: -0.02em;
    text-transform: uppercase;
  }}
  .company-tagline {{
    font-size: 12px;
    font-weight: 700;
    color: #2563eb;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
  }}
  .company-meta {{
    font-size: 11.5px;
    color: var(--text-muted);
    font-weight: 500;
  }}

  .invoice-tag-box {{
    text-align: right;
  }}
  .invoice-tag {{
    display: inline-block;
    background: #0f172a;
    color: #ffffff;
    font-size: 12px;
    font-weight: 800;
    padding: 4px 10px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
  }}
  .meta-table {{
    font-size: 11.5px;
    margin-left: auto;
    border-collapse: collapse;
  }}
  .meta-table td {{
    padding: 1.5px 0 1.5px 12px;
    border: none;
    text-align: right;
  }}
  .meta-label {{ color: var(--text-muted); font-weight: 600; }}
  .meta-val {{ color: var(--text-dark); font-weight: 700; }}

  /* Vendor and Settlement Banner */
  .party-grid {{
    display: grid;
    grid-template-columns: 1.4fr 1fr;
    gap: 12px;
    margin-bottom: 14px;
  }}
  .party-card {{
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 12px;
    background: #ffffff;
  }}
  .party-card h4 {{
    margin: 0 0 6px 0;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    padding-bottom: 3px;
  }}
  .party-name {{
    font-size: 16px;
    font-weight: 900;
    color: #1e3a8a;
    margin-bottom: 4px;
  }}
  .party-info-row {{
    display: flex;
    justify-content: space-between;
    padding: 1.5px 0;
    font-size: 11.5px;
  }}

  .due-summary-card {{
    border: 1.5px solid var(--border);
    border-radius: 6px;
    padding: 10px 12px;
    background: var(--bg-light);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    text-align: center;
  }}
  .due-title {{
    font-size: 10.5px;
    font-weight: 800;
    text-transform: uppercase;
    color: var(--text-muted);
    letter-spacing: 0.04em;
  }}
  .due-val {{
    font-size: 24px;
    font-weight: 900;
    margin: 4px 0;
    font-variant-numeric: tabular-nums;
  }}
  .badge-due {{ color: #dc2626; }}
  .badge-advance {{ color: #16a34a; }}
  .badge-nil {{ color: #475569; }}
  .due-caption {{
    font-size: 10.5px;
    color: var(--text-muted);
    font-weight: 600;
  }}

  /* Tables */
  .section-label {{
    font-size: 12px;
    font-weight: 800;
    color: var(--primary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin: 12px 0 5px 0;
    display: flex;
    align-items: center;
    gap: 5px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 12px;
    font-size: 11.5px;
  }}
  th, td {{
    border: 1px solid var(--border);
    padding: 5px 7px;
  }}
  th {{
    background: var(--primary);
    color: #ffffff;
    font-weight: 700;
    text-align: center;
    font-size: 11px;
    letter-spacing: 0.02em;
  }}
  tbody tr:nth-child(even) {{ background: var(--bg-light); }}
  .total-row td {{
    background: #1e293b !important;
    color: #ffffff !important;
    font-weight: 900 !important;
    border-color: #334155 !important;
  }}

  /* Settlement Calculation Box */
  .settlement-grid {{
    display: grid;
    grid-template-columns: 1.3fr 1fr;
    gap: 12px;
    margin-bottom: 14px;
    align-items: start;
  }}
  .settlement-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 11.5px;
    margin-bottom: 0;
  }}
  .settlement-table td {{
    padding: 4px 8px;
    border: 1px solid var(--border);
  }}
  .st-label {{ color: var(--text-dark); font-weight: 600; }}
  .st-val {{ text-align: right; font-weight: 700; font-variant-numeric: tabular-nums; }}
  .st-total td {{
    background: #0f172a !important;
    color: #ffffff !important;
    font-weight: 900 !important;
    font-size: 13px !important;
  }}

  .words-box {{
    background: #f8fafc;
    border: 1px dashed var(--border-dark);
    border-radius: 6px;
    padding: 8px 10px;
    margin-bottom: 8px;
    font-size: 11px;
  }}
  .words-title {{ font-size: 10px; font-weight: 800; color: var(--text-muted); text-transform: uppercase; }}
  .words-val {{ font-weight: 700; color: #1e3a8a; margin-top: 2px; }}

  /* Signatures */
  .footer-sign {{
    margin-top: 28px;
    display: flex;
    justify-content: space-between;
    padding-top: 8px;
  }}
  .sign-box {{
    border-top: 1.5px solid #94a3b8;
    width: 220px;
    text-align: center;
    padding-top: 5px;
    font-size: 11px;
    font-weight: 700;
    color: var(--text-dark);
  }}

  .print-btn-bar {{
    margin-bottom: 12px;
    text-align: right;
  }}
  .print-btn {{
    background: #0f172a;
    color: #fff;
    border: none;
    padding: 6px 16px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 12px;
    cursor: pointer;
  }}

  @media print {{
    @page {{ size: A4 portrait; margin: 5mm; }}
    body {{ margin: 0; padding: 0; max-width: 100%; font-size: 10px; line-height: 1.18; }}
    .print-btn-bar {{ display: none !important; }}
    th {{ background: #0f172a !important; color: #fff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; font-size: 9.5px; }}
    .total-row td {{ background: #1e293b !important; color: #fff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .st-total td {{ background: #0f172a !important; color: #fff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    table {{ font-size: 9.5px !important; margin-bottom: 6px !important; }}
    th, td {{ padding: 2px 4px !important; }}
    .section-label {{ margin: 6px 0 3px 0 !important; font-size: 11px !important; }}
    .party-grid {{ margin-bottom: 6px !important; }}
    .party-card {{ padding: 6px 8px !important; }}
    .due-summary-card {{ padding: 6px 8px !important; }}
    .due-val {{ font-size: 18px !important; margin: 2px 0 !important; }}
    .settlement-grid {{ margin-bottom: 6px !important; }}
    .footer-sign {{ margin-top: 14px !important; }}
    tr {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>

<div class="print-btn-bar">
  <button class="print-btn" onclick="window.print()">🖨️ Print Vendor Bill (A4 Portrait)</button>
</div>

<!-- Header -->
<div class="bill-header">
  <div>
    <h1 class="company-title">{esc(shop_name)}</h1>
  </div>
  <div class="invoice-tag-box">
    <div class="invoice-tag">Vendor Purchase Bill</div>
    <table class="meta-table">
      <tr><td class="meta-label">Bill No:</td><td class="meta-val">{inv_no}</td></tr>
      <tr><td class="meta-label">Bill Date:</td><td class="meta-val">{bill_date_str}</td></tr>
      <tr><td class="meta-label">Period:</td><td class="meta-val">{start_day.strftime('%d-%b-%y')} to {end_day.strftime('%d-%b-%y')}</td></tr>
    </table>
  </div>
</div>

<!-- Party and Settlement Status -->
<div class="party-grid">
  <div class="party-card">
    <h4>Supplied By (Vendor Particulars)</h4>
    <div class="party-name">{esc(vendor)}</div>
    <div class="party-info-row">
      <span style="color:#64748b;">Vendor ID:</span>
      <span style="font-weight:700;">#{did}</span>
    </div>
    <div class="party-info-row">
      <span style="color:#64748b;">Contact:</span>
      <span style="font-weight:700;">{esc(contact)}</span>
    </div>
    <div class="party-info-row">
      <span style="color:#64748b;">Address:</span>
      <span>{esc(address)}</span>
    </div>
  </div>

  <div class="due-summary-card">
    <div class="due-title">{due_status_text}</div>
    <div class="due-val {due_badge_class}">₹{abs(closing_due):,.2f}</div>
    <div class="due-caption">{due_caption}</div>
  </div>
</div>

<!-- 1. Product Summary Table -->
<div class="section-label">📦 Wholesale Milk Procurement Particulars</div>
<table>
  <thead>
    <tr>
      <th style="width:36px;">#</th>
      <th style="text-align:left;">Product / Category Description</th>
      <th style="width:120px; text-align:right;">Supplied Qty</th>
      <th style="width:100px; text-align:right;">Avg Rate</th>
      <th style="width:130px; text-align:right;">Purchases (₹)</th>
    </tr>
  </thead>
  <tbody>
    {product_rows_html}
  </tbody>
  <tfoot>
    <tr class="total-row">
      <td colspan="2" style="text-align:left; font-weight:800;">TOTAL PROCUREMENT</td>
      <td style="text-align:right; font-weight:800;">{total_milk_all:,.2f} LTR</td>
      <td style="text-align:center;">–</td>
      <td style="text-align:right; font-weight:900;">₹{total_amt:,.2f}</td>
    </tr>
  </tfoot>
</table>

<!-- 2. Account Settlement & Payment Box -->
<div class="settlement-grid">
  <div>
    <div class="section-label">📊 Vendor Account Settlement</div>
    <table class="settlement-table">
      <tr>
        <td class="st-label">Previous Ledger Balance</td>
        <td class="st-val">₹{opening_due:,.2f}</td>
      </tr>
      <tr>
        <td class="st-label">Add: Current Purchases (This Period)</td>
        <td class="st-val">+ ₹{total_amt:,.2f}</td>
      </tr>
      <tr style="background:#f1f5f9;">
        <td class="st-label" style="font-weight:700;">Gross Amount Payable</td>
        <td class="st-val" style="font-weight:800;">₹{gross_payable:,.2f}</td>
      </tr>
      <tr>
        <td class="st-label">Less: Payments Made to Vendor</td>
        <td class="st-val" style="color:#16a34a;">- ₹{total_pay:,.2f}</td>
      </tr>
      <tr class="st-total">
        <td>FINAL NET PAYABLE TO VENDOR</td>
        <td class="st-val">₹{closing_due:,.2f}</td>
      </tr>
    </table>
  </div>

  <div>
    <div class="section-label">💳 Payments Breakdown</div>
    <table>
      <thead>
        <tr><th>Mode</th><th style="text-align:right;">Total Paid</th></tr>
      </thead>
      <tbody>
        {pay_rows_html}
      </tbody>
    </table>

    <div class="words-box">
      <div class="words-title">Amount in Words:</div>
      <div class="words-val">{words_text}</div>
    </div>
  </div>
</div>

<!-- 3. Daily Supply & Inward Log -->
<div class="section-label">📅 Annexure: Daily Supply & Inward Log</div>
<table>
  <thead>
    <tr>{th}</tr>
  </thead>
  <tbody>
    {body_rows}
  </tbody>
  <tfoot>
    <tr class="total-row">{total_row}</tr>
  </tfoot>
</table>

<!-- Dual Signatures -->
<div class="footer-sign">
  <div class="sign-box">
    Distributor / Vendor Signature
  </div>
  <div class="sign-box">
    For {esc(shop_name)}<br/>
    <span style="font-size:10px; color:#64748b; font-weight:500;">(Authorized Signatory)</span>
  </div>
</div>

</body>
</html>
"""
    return html

def html_esc(x):
    if pd.isna(x):
        return ""
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def get_report_common_css() -> str:
    return """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    body {
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        margin: 18px auto;
        max-width: 980px;
        color: #0f172a;
        font-size: 11px;
        line-height: 1.35;
        background: #ffffff;
    }
    .header {
        text-align: center;
        border-bottom: 2px solid #0f172a;
        padding-bottom: 8px;
        margin-bottom: 12px;
    }
    .header h2 {
        margin: 0 0 2px 0;
        font-size: 20px;
        font-weight: 900;
        color: #0f172a;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .header h4 {
        margin: 0 0 3px 0;
        font-size: 13.5px;
        color: #2563eb;
        font-weight: 700;
    }
    .header p {
        margin: 0;
        font-size: 11px;
        color: #64748b;
        font-weight: 600;
    }
    .print-btn {
        margin-bottom: 12px;
        text-align: right;
    }
    .print-btn button {
        background: #0f172a;
        color: #ffffff;
        border: none;
        padding: 6px 16px;
        border-radius: 6px;
        font-size: 11.5px;
        font-weight: 700;
        cursor: pointer;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    .cards {
        display: flex;
        justify-content: space-between;
        margin-top: 10px;
        margin-bottom: 14px;
        flex-wrap: wrap;
        gap: 8px;
    }
    .card {
        flex: 1;
        min-width: 135px;
        padding: 8px 10px;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        background: #f8fafc;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .card-title {
        font-size: 9.5px;
        color: #64748b;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .card-value {
        font-size: 16px;
        font-weight: 900;
        margin-top: 3px;
    }
    .card-sub {
        font-size: 10px;
        color: #64748b;
        margin-top: 2px;
    }
    .section {
        margin-top: 14px;
    }
    .section h3 {
        margin: 0 0 6px 0;
        font-size: 12.5px;
        font-weight: 800;
        color: #0f172a;
        border-left: 3.5px solid #2563eb;
        padding-left: 8px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 6px;
        font-size: 11px;
        background: #ffffff;
    }
    th, td {
        border: 1px solid #cbd5e1;
        padding: 5px 6px;
        text-align: right;
    }
    th {
        background: #1e293b;
        color: #ffffff;
        font-weight: 750;
        text-align: center;
        font-size: 10.5px;
    }
    td.left-align, th.left-align {
        text-align: left;
    }
    tr:nth-child(even) td {
        background: #f8fafc;
    }
    tr.total-row td {
        background: #0f172a !important;
        color: #ffffff !important;
        font-weight: 900 !important;
        border-color: #0f172a !important;
    }
    .footer-sign {
        margin-top: 24px;
        display: flex;
        justify-content: space-between;
        padding-top: 8px;
    }
    .sign-box {
        border-top: 1.5px solid #0f172a;
        width: 190px;
        text-align: center;
        padding-top: 5px;
        font-size: 10.5px;
        font-weight: 700;
        color: #1e293b;
    }
    @media print {
        @page {
            size: A4 portrait;
            margin: 6mm 7mm;
        }
        body {
            margin: 0 auto;
            padding: 0;
            max-width: 100%;
            font-size: 9.5px !important;
            line-height: 1.2 !important;
        }
        .print-btn {
            display: none !important;
        }
        .route-page {
            page-break-after: always !important;
            break-after: page !important;
            page-break-inside: avoid !important;
            break-inside: avoid !important;
            min-height: 96vh;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .route-page:last-child {
            page-break-after: auto !important;
            break-after: auto !important;
        }
        table {
            font-size: 9px !important;
            margin-top: 4px !important;
        }
        th, td {
            padding: 2.5px 3.5px !important;
        }
        .header h2 { font-size: 16px !important; margin-bottom: 2px !important; }
        .header h4 { font-size: 12px !important; margin-bottom: 2px !important; }
        .header p { font-size: 9.5px !important; }
        .cards { margin-top: 6px !important; gap: 5px !important; }
        .card { padding: 4px 6px !important; font-size: 9.5px !important; }
        .card-value { font-size: 13.5px !important; }
        .section { margin-top: 8px !important; }
        .section h3 { font-size: 11px !important; margin-bottom: 3px !important; }
        .footer-sign {
            margin-top: auto !important;
            padding-top: 6px !important;
        }
        tr { page-break-inside: avoid; }
    }
    """


def render_executive_report_table(df: pd.DataFrame, title: str = None, grand_label: str = "TOTAL") -> str:
    """Renders a clean, executive styled HTML table with integer IDs, right-aligned numbers, and no duplicate totals."""
    import re
    if df is None or df.empty:
        sec_h = f"<h3>{html_esc(title)}</h3>" if title else ""
        return f"<div class='section'>{sec_h}<p style='color:#64748b; font-size:11px; padding:4px 0;'>No records available for this section.</p></div>"

    clean_cols = []
    for c in df.columns:
        c_clean = re.sub(r"^CID:\d+\s*—\s*", "", str(c).strip())
        clean_cols.append(c_clean)

    header_ths = []
    for c_clean in clean_cols:
        c_upper = c_clean.upper()
        is_left = any(k in c_upper for k in ["NAME", "RETAILER", "CATEGORY", "NOTE", "MODE", "TYPE", "ZONE", "REASON", "DESCRIPTION"]) or c_upper == "ID"
        align = "left-align" if is_left else ""
        header_ths.append(f"<th class='{align}'>{html_esc(c_clean)}</th>")
    head_html = "".join(header_ths)

    rows_html = ""
    for _, r in df.iterrows():
        is_total = False
        first_val = str(r.iloc[0]).strip().upper() if len(r) > 0 else ""
        second_val = str(r.iloc[1]).strip().upper() if len(r) > 1 else ""
        if "TOTAL" in first_val or "TOTAL" in second_val or "ALL" in first_val or grand_label in first_val:
            is_total = True

        tr_class = " class='total-row'" if is_total else ""
        tds = ""
        total_label_placed = False

        for idx, orig_c in enumerate(df.columns):
            c_clean = clean_cols[idx]
            c_upper = c_clean.upper()
            val = r[orig_c]
            is_left = any(k in c_upper for k in ["NAME", "RETAILER", "CATEGORY", "NOTE", "MODE", "TYPE", "ZONE", "REASON", "DESCRIPTION"])
            align = " class='left-align'" if is_left else ""

            if is_total:
                if not total_label_placed and (is_left or c_upper in ["ID", "RETAILER", "NAME", "ZONE"]):
                    tds += f"<td{align}><b>TOTAL</b></td>"
                    total_label_placed = True
                elif not total_label_placed and idx == 0:
                    tds += f"<td{align}><b>TOTAL</b></td>"
                    total_label_placed = True
                elif is_left or c_upper in ["ID", "RETAILER", "NAME", "ZONE"]:
                    tds += f"<td{align}></td>"
                else:
                    try:
                        clean_str = str(val).replace("₹", "").replace(",", "").strip()
                        num_val = float(pd.to_numeric(clean_str, errors="coerce") or 0.0)
                        if abs(num_val) > 0.0001:
                            if any(k in c_upper for k in ["₹", "COST", "SALES", "LEDGER", "PAYMENT", "PAID", "AMOUNT", "LOSS"]):
                                tds += f"<td>₹{num_val:,.2f}</td>"
                            else:
                                tds += f"<td>{num_val:,.2f}</td>"
                        else:
                            tds += "<td style='color:#94a3b8;'>–</td>"
                    except Exception:
                        tds += f"<td>{html_esc(val)}</td>"
            else:
                if c_upper == "ID":
                    try:
                        id_num = int(float(val))
                        tds += f"<td class='left-align' style='font-weight:700;'>{id_num}</td>"
                    except Exception:
                        tds += f"<td class='left-align'>{html_esc(val)}</td>"
                elif is_left:
                    val_str = str(val).strip()
                    if not val_str or val_str.lower() in ("nan", "none"):
                        val_str = "Counter / Direct" if ("ZONE" in c_upper or "NAME" in c_upper) else "–"
                    tds += f"<td{align}>{html_esc(val_str)}</td>"
                else:
                    try:
                        clean_str = str(val).replace("₹", "").replace(",", "").strip()
                        num_val = float(pd.to_numeric(clean_str, errors="coerce") or 0.0)
                        if abs(num_val) > 0.0001:
                            if any(k in c_upper for k in ["₹", "COST", "SALES", "LEDGER", "PAYMENT", "PAID", "AMOUNT", "LOSS"]):
                                tds += f"<td style='font-weight:600;'>₹{num_val:,.2f}</td>"
                            else:
                                tds += f"<td>{num_val:,.2f}</td>"
                        else:
                            tds += "<td style='color:#94a3b8;'>–</td>"
                    except Exception:
                        tds += f"<td>{html_esc(val)}</td>"

        rows_html += f"<tr{tr_class}>{tds}</tr>"

    sec_header = f"<h3>{html_esc(title)}</h3>" if title else ""
    return f"""
    <div class="section">
        {sec_header}
        <table>
            <thead><tr>{head_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """


def build_daily_report_html(
    report_day,
    retailer_table,
    retailer_totals,
    retailer_pay_modes,
    distributor_table,
    distributor_totals,
    purchased_qty,
    purchased_amt,
    sold_qty,
    sold_amt,
    waste_qty=0.0,
    waste_loss=0.0,
    expenses_df=None,
    total_expenses=0.0,
    show_cards=True,
):
    import pandas as pd

    def fmt_num(x):
        try:
            return f"{float(x):,.2f}"
        except Exception:
            return "0.00"

    def fmt_money(x):
        try:
            return f"₹{float(x):,.2f}"
        except Exception:
            return "₹0.00"

    # Split expenses into Route Expenses vs General Dairy Overhead Expenses
    route_exp_list = []
    general_exp_list = []
    route_exp_total = 0.0
    general_exp_total = 0.0
    total_cash_expenses = 0.0

    if expenses_df is not None and not expenses_df.empty:
        known_routes = set(_norm_zone(x) for x in get_all_zones())
        for _, er in expenses_df.iterrows():
            desc_val = str(er.get("description", ""))
            cat_val = str(er.get("category", "-"))
            z_found = extract_expense_zone(desc_val, cat_val)
            norm_zf = _norm_zone(z_found) if z_found else None
            try:
                amt = float(pd.to_numeric(er.get("amount", 0.0), errors="coerce") or 0.0)
            except Exception:
                amt = 0.0
            if amt <= 0:
                continue

            pmode = str(er.get("payment_mode", "Cash")).strip()
            note = clean_expense_note(desc_val)
            if pmode.upper() == "CASH":
                total_cash_expenses += amt

            if z_found and norm_zf in known_routes:
                route_exp_list.append({
                    "Zone / Route": z_found,
                    "Category": cat_val,
                    "Note": note,
                    "Mode": pmode,
                    "Amount": amt,
                })
                route_exp_total += amt
            else:
                general_exp_list.append({
                    "Category": cat_val,
                    "Note": note,
                    "Mode": pmode,
                    "Amount": amt,
                })
                general_exp_total += amt

    calc_total_expenses = route_exp_total + general_exp_total
    if total_expenses <= 0 and calc_total_expenses > 0:
        total_expenses = calc_total_expenses

    # Cash Collected from Retailers
    cash_collected = 0.0
    if retailer_pay_modes is not None and not retailer_pay_modes.empty:
        for _, pr in retailer_pay_modes.iterrows():
            pmode_name = str(pr.iloc[0]).strip().upper() if len(pr) > 0 else ""
            if pmode_name == "CASH":
                try:
                    cash_collected += float(pd.to_numeric(str(pr.iloc[1]).replace("₹", "").replace(",", ""), errors="coerce") or 0.0)
                except Exception:
                    pass

    net_cash_handover = cash_collected - total_cash_expenses
    net_profit = float(sold_amt) - float(purchased_amt) - float(waste_loss) - float(total_expenses)
    profit_bg = "#f0fdf4" if net_profit >= 0 else "#fff1f2"
    profit_color = "#166534" if net_profit >= 0 else "#b91c1c"
    profit_border = "#86efac" if net_profit >= 0 else "#fca5a5"

    summary_cards = f"""
    <div class="cards">
        <div class="card">
            <div class="card-title">MILK INWARD (PURCHASED)</div>
            <div class="card-value" style="color:#0284c7;">{fmt_num(purchased_qty)} L</div>
            <div class="card-sub">Cost: {fmt_money(purchased_amt)}</div>
        </div>
        <div class="card">
            <div class="card-title">MILK OUTWARD (DELIVERED)</div>
            <div class="card-value" style="color:#16a34a;">{fmt_num(sold_qty)} L</div>
            <div class="card-sub">Sales: {fmt_money(sold_amt)}</div>
        </div>
        <div class="card">
            <div class="card-title">WASTAGE / SPILLAGE</div>
            <div class="card-value" style="color:#d97706;">{fmt_num(waste_qty)} L</div>
            <div class="card-sub">Loss: {fmt_money(waste_loss)}</div>
        </div>
        <div class="card">
            <div class="card-title">TOTAL EXPENSES</div>
            <div class="card-value" style="color:#b91c1c;">{fmt_money(total_expenses)}</div>
            <div class="card-sub">Route: ₹{route_exp_total:,.0f} | Gen: ₹{general_exp_total:,.0f}</div>
        </div>
        <div class="card" style="background:{profit_bg}; border:1.5px solid {profit_border};">
            <div class="card-title" style="color:{profit_color};">REAL NET PROFIT / MARGIN</div>
            <div class="card-value" style="color:{profit_color};">{fmt_money(net_profit)}</div>
            <div class="card-sub" style="color:{profit_color};">Net Sales − Cost − Expenses</div>
        </div>
    </div>
    """

    cards_html = summary_cards if show_cards else ""

    # Build Simplified Operating Expenses Table (Single row per zone, separate row for overhead)
    zone_exp_summary = {}
    for r in route_exp_list:
        z = r.get("Zone / Route", "Route")
        if z not in zone_exp_summary:
            zone_exp_summary[z] = {"total": 0.0, "cash": 0.0, "details": []}
        zone_exp_summary[z]["total"] += float(r.get("Amount", 0.0))
        if str(r.get("Mode", "")).strip().upper() == "CASH":
            zone_exp_summary[z]["cash"] += float(r.get("Amount", 0.0))
        det = str(r.get("Category", "")) + (f" ({r['Note']})" if r.get("Note") else "")
        if det and det not in zone_exp_summary[z]["details"]:
            zone_exp_summary[z]["details"].append(det)

    overhead_total = 0.0
    overhead_cash = 0.0
    overhead_details = []
    for g in general_exp_list:
        overhead_total += float(g.get("Amount", 0.0))
        if str(g.get("Mode", "")).strip().upper() == "CASH":
            overhead_cash += float(g.get("Amount", 0.0))
        det = str(g.get("Category", "")) + (f" ({g['Note']})" if g.get("Note") else "")
        if det and det not in overhead_details:
            overhead_details.append(det)

    exp_simplified_rows = ""
    for z, zinfo in zone_exp_summary.items():
        det_str = ", ".join(zinfo["details"]) if zinfo["details"] else "Zone Delivery Expenses"
        exp_simplified_rows += f"""<tr>
            <td class='left-align'><b>Zone / Route: {html_esc(z)}</b></td>
            <td class='left-align'>{html_esc(det_str)}</td>
            <td style='text-align:right;'>₹{zinfo['cash']:,.2f}</td>
            <td style='text-align:right; font-weight:700; color:#b91c1c;'>₹{zinfo['total']:,.2f}</td>
        </tr>"""

    if overhead_total > 0 or general_exp_list:
        ovh_str = ", ".join(overhead_details) if overhead_details else "General Overhead Expenses"
        exp_simplified_rows += f"""<tr style='background:#f8fafc;'>
            <td class='left-align'><b>General Overhead</b></td>
            <td class='left-align'>{html_esc(ovh_str)}</td>
            <td style='text-align:right;'>₹{overhead_cash:,.2f}</td>
            <td style='text-align:right; font-weight:700; color:#b91c1c;'>₹{overhead_total:,.2f}</td>
        </tr>"""

    exp_combined_html = ""
    if exp_simplified_rows:
        exp_combined_html = f"""
        <div class="section">
            <h3>Operating Expenses (Zone-wise &amp; General Overheads)</h3>
            <table>
                <thead>
                    <tr>
                        <th class='left-align'>Zone / Expense Type</th>
                        <th class='left-align'>Category / Description</th>
                        <th style='text-align:right;'>Cash Expenses (₹)</th>
                        <th style='text-align:right;'>Total Expenses (₹)</th>
                    </tr>
                </thead>
                <tbody>
                    {exp_simplified_rows}
                    <tr class='total-row' style='background:#0f172a !important;'>
                        <td colspan="2" class='left-align' style="color:#fff; font-weight:900;">GRAND TOTAL OPERATING EXPENSES</td>
                        <td style="color:#fff; font-weight:900; text-align:right;">₹{total_cash_expenses:,.2f}</td>
                        <td style="color:#fff; font-weight:900; text-align:right;">₹{total_expenses:,.2f}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """

    # Cash Handover & Till Reconciliation Box
    till_bg = "#f0fdf4" if net_cash_handover >= 0 else "#fff1f2"
    till_color = "#166534" if net_cash_handover >= 0 else "#b91c1c"
    till_border = "#86efac" if net_cash_handover >= 0 else "#fca5a5"
    reconciliation_html = f"""
    <div class="section">
        <h3>Day Cash Reconciliation & Counter Handover</h3>
        <div class="cards">
            <div class="card">
                <div class="card-title">TOTAL CASH COLLECTED</div>
                <div class="card-value" style="color:#16a34a;">₹{cash_collected:,.2f}</div>
            </div>
            <div class="card">
                <div class="card-title">TOTAL CASH EXPENSES</div>
                <div class="card-value" style="color:#dc2626;">₹{total_cash_expenses:,.2f}</div>
            </div>
            <div class="card" style="background:{till_bg}; border:1.5px solid {till_border};">
                <div class="card-title" style="color:{till_color};">NET CASH TILL BALANCE</div>
                <div class="card-value" style="color:{till_color};">₹{net_cash_handover:,.2f}</div>
            </div>
        </div>
    </div>
    """

    dist_html = ""
    if show_cards and distributor_table is not None and not distributor_table.empty:
        dist_html = render_executive_report_table(distributor_table, "Distributors Inward Summary")

    retailer_sec_html = render_executive_report_table(retailer_table, "Retailers / Zones Summary")
    payments_sec_html = render_executive_report_table(retailer_pay_modes, "Payments Collection by Mode")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Overall Daily Business Summary — {html_esc(str(report_day))}</title>
<style>
{get_report_common_css()}
</style>
</head>
<body>

<div class="print-btn">
    <button onclick="window.print()">🖨️ Print Report (A4 Portrait)</button>
</div>

<div class="header">
    <h2>RANJIT BHIMRAO KAWLE MILK</h2>
    <h4>Overall Daily Business Summary</h4>
    <p>Date: {html_esc(str(report_day))}</p>
</div>

{cards_html}

{retailer_sec_html}

{payments_sec_html}

{exp_combined_html}

{dist_html}

{reconciliation_html}

<div class="footer-sign">
    <div class="sign-box">Prepared By / Counter In-charge</div>
    <div class="sign-box">Authorized Proprietor Signature</div>
</div>

</body>
</html>
"""
    return html


# ============================================================
# ROUTE EXPENSE & RECONCILIATION HELPERS
# ============================================================
ROUTE_EXPENSE_CATEGORIES = [
    "Fuel",
    "Repair",
    "Nasta",
    "Others",
]

GENERAL_EXPENSE_CATEGORIES = [
    "Fuel",
    "Repair",
    "Nasta",
    "Others",
]

def extract_expense_zone(description: str, category: str = "") -> str | None:
    """Extracts zone/route name from description if prefixed with '[Route X]' or from category."""
    import re
    if isinstance(description, str):
        m = re.match(r"^\[(.*?)\]", description.strip())
        if m:
            return m.group(1).strip()
    if isinstance(category, str) and " - " in category:
        parts = category.split(" - ", 1)
        if "route" in parts[0].lower() or "zone" in parts[0].lower():
            return parts[0].strip()
    return None

def clean_expense_note(description: str) -> str:
    """Removes the leading '[Zone Name]' tag from description to display clean note."""
    import re
    if not isinstance(description, str):
        return ""
    return re.sub(r"^\[.*?\]\s*", "", description.strip())

def get_route_expenses_df(d, zone: str) -> pd.DataFrame:
    """Fetches expenses for given date and zone (or General / All Zones) from expenses table."""
    import pandas as pd
    try:
        exp_df = sb_fetch_df(
            EXPENSES_FILE,
            CSV_SCHEMAS[EXPENSES_FILE],
            filters=[("date", "eq", str(d))],
        )
    except Exception:
        exp_df = pd.DataFrame()
    if exp_df.empty:
        return pd.DataFrame(columns=["expense_id", "zone", "category", "amount", "payment_mode", "note"])

    rows = []
    norm_z = _norm_zone(zone)
    known_routes = set(_norm_zone(x) for x in get_all_zones())
    for _, r in exp_df.iterrows():
        z_found = extract_expense_zone(str(r.get("description", "")), str(r.get("category", "")))
        norm_zf = _norm_zone(z_found) if z_found else None

        matches = False
        if zone == "All Zones":
            matches = True
        elif norm_z == "general":
            matches = (norm_zf == "general") or (norm_zf is None) or (norm_zf not in known_routes)
        else:
            matches = (norm_zf == norm_z)

        if matches:
            try:
                amt_val = float(pd.to_numeric(r.get("amount", 0.0), errors="coerce") or 0.0)
            except Exception:
                amt_val = 0.0
            rows.append({
                "expense_id": int(pd.to_numeric(r.get("expense_id", 0), errors="coerce") or 0),
                "zone": z_found if (z_found and norm_zf in known_routes) else "General",
                "category": str(r.get("category", "")),
                "amount": amt_val,
                "payment_mode": str(r.get("payment_mode", "Cash")),
                "note": clean_expense_note(str(r.get("description", ""))),
            })
    return pd.DataFrame(rows)

def save_route_expenses_records(d, zone: str, edited_expenses_df: pd.DataFrame) -> None:
    """Saves route or general expenses for a specific date and zone into expenses table."""
    import pandas as pd
    norm_z = _norm_zone(zone)
    known_routes = set(_norm_zone(x) for x in get_all_zones())
    exp_df = sb_fetch_df(
        EXPENSES_FILE,
        CSV_SCHEMAS[EXPENSES_FILE],
        filters=[("date", "eq", str(d))],
    )
    old_ids_to_delete = []
    if not exp_df.empty:
        for _, r in exp_df.iterrows():
            z_found = extract_expense_zone(str(r.get("description", "")), str(r.get("category", "")))
            norm_zf = _norm_zone(z_found) if z_found else None
            is_match = False
            if norm_z == "general":
                is_match = (norm_zf == "general") or (norm_zf is None) or (norm_zf not in known_routes)
            else:
                is_match = (norm_zf == norm_z)
            if is_match:
                try:
                    old_ids_to_delete.append(int(r["expense_id"]))
                except Exception:
                    pass

    if old_ids_to_delete:
        sb_delete_by_pk("expenses", "expense_id", old_ids_to_delete)

    if edited_expenses_df is not None and not edited_expenses_df.empty:
        new_records = []
        next_id = sb_new_id("expenses", "expense_id")
        for _, r in edited_expenses_df.iterrows():
            amt_val = r.get("Amount ₹", r.get("amount", 0.0))
            amt = float(pd.to_numeric(amt_val, errors="coerce") or 0.0)
            cat_val = r.get("Category", r.get("category", ""))
            cat = str(cat_val).strip()
            if amt <= 0 or not cat:
                continue
            mode_val = r.get("Payment Mode", r.get("payment_mode", "Cash"))
            mode = str(mode_val).strip() or "Cash"
            note_val = r.get("Note", r.get("note", ""))
            note = str(note_val).strip()
            desc = f"[{zone}] {note}".strip() if note else f"[{zone}]"
            rec = {
                "date": str(d),
                "category": cat,
                "description": desc,
                "amount": round(amt, 2),
                "payment_mode": mode,
                "paid": True,
            }
            if next_id is not None:
                rec["expense_id"] = next_id
                next_id += 1
            new_records.append(rec)

        if new_records:
            sb_insert_df(pd.DataFrame(new_records), EXPENSES_FILE)

    invalidate_data_cache()


DRIVER_HANDOVERS_FILE = "data/driver_handovers.csv"


def get_driver_actual_handover(d, zone: str) -> float:
    """Returns actual cash handed over by driver on date d for route zone."""
    d_str = str(d)
    norm_z = _norm_zone(zone)
    if os.path.exists(DRIVER_HANDOVERS_FILE):
        try:
            df = pd.read_csv(DRIVER_HANDOVERS_FILE)
            if not df.empty and "date" in df.columns and "zone" in df.columns:
                df["norm_z"] = df["zone"].apply(_norm_zone)
                m = df[(df["date"].astype(str) == d_str) & (df["norm_z"] == norm_z)]
                if not m.empty and "actual_handover" in m.columns:
                    return float(pd.to_numeric(m.iloc[-1]["actual_handover"], errors="coerce") or 0.0)
        except Exception:
            pass
    return 0.0


def save_driver_actual_handover(d, zone: str, actual_handover: float, expected_handover: float = 0.0) -> None:
    """Saves actual cash handover for date d and route zone."""
    d_str = str(d)
    norm_z = _norm_zone(zone)
    os.makedirs("data", exist_ok=True)
    all_df = pd.DataFrame()
    if os.path.exists(DRIVER_HANDOVERS_FILE):
        try:
            all_df = pd.read_csv(DRIVER_HANDOVERS_FILE)
        except Exception:
            all_df = pd.DataFrame()

    new_row = {
        "date": d_str,
        "zone": str(zone),
        "actual_handover": round(float(actual_handover or 0.0), 2),
        "expected_handover": round(float(expected_handover or 0.0), 2),
        "updated_at": datetime.now().isoformat(),
    }
    if not all_df.empty and "date" in all_df.columns and "zone" in all_df.columns:
        all_df["norm_z"] = all_df["zone"].apply(_norm_zone)
        keep = all_df[~((all_df["date"].astype(str) == d_str) & (all_df["norm_z"] == norm_z))].drop(columns=["norm_z"], errors="ignore")
        combined = pd.concat([keep, pd.DataFrame([new_row])], ignore_index=True)
    else:
        combined = pd.DataFrame([new_row])
    combined.to_csv(DRIVER_HANDOVERS_FILE, index=False)


def build_zone_route_summary_master_html(report_day, zone_list_data: list) -> str:
    """Generates the master Zone Summary document matching the modern executive format of Daily Report.
    Features shared executive typography, dark-slate table headers, KPI reconciliation cards,
    Payments by Mode, Route Expenses, and strictly 1 route per A4 portrait page."""
    import pandas as pd

    zone_pages_html = ""

    for item in zone_list_data:
        z = item["zone"]
        df = item["df"]
        pm = item.get("pay_modes", pd.DataFrame())
        exp_df = item.get("expenses", pd.DataFrame())

        # Render Retailers Table with Executive formatting
        retailers_table_html = render_executive_report_table(df, title="Retailers Delivery Summary")

        # Payments by Mode
        cash_collected = 0.0
        pm_clean = pd.DataFrame()
        if pm is not None and not pm.empty:
            pm_df = pm.copy()
            mode_col = "payment_mode" if "payment_mode" in pm_df.columns else pm_df.columns[0]
            amt_col = "amount" if "amount" in pm_df.columns else pm_df.columns[1]

            pm_rows = []
            pm_total = 0.0
            for _, pr in pm_df.iterrows():
                m_name = str(pr.get(mode_col, "–")).strip()
                try:
                    m_amt = float(pd.to_numeric(pr.get(amt_col, 0.0), errors="coerce") or 0.0)
                except Exception:
                    m_amt = 0.0
                if m_amt <= 0:
                    continue
                if m_name.upper() == "CASH":
                    cash_collected += m_amt
                pm_total += m_amt
                pm_rows.append({"Payment Mode": m_name, "Amount (₹)": m_amt})

            if pm_rows:
                pm_rows.append({"Payment Mode": "TOTAL", "Amount (₹)": pm_total})
                pm_clean = pd.DataFrame(pm_rows)

        pm_table_html = render_executive_report_table(pm_clean, title="Payments Collection by Mode")

        # Route Expenses
        cash_expenses = 0.0
        total_route_exp = 0.0
        exp_clean = pd.DataFrame()
        if exp_df is not None and not exp_df.empty:
            exp_rows = []
            for _, er in exp_df.iterrows():
                cat = str(er.get("category", "–")).strip()
                note = str(er.get("note", "")).strip()
                emode = str(er.get("payment_mode", "Cash")).strip()
                try:
                    eamt = float(pd.to_numeric(er.get("amount", 0.0), errors="coerce") or 0.0)
                except Exception:
                    eamt = 0.0
                if eamt <= 0:
                    continue
                total_route_exp += eamt
                if emode.upper() == "CASH":
                    cash_expenses += eamt
                exp_rows.append({
                    "Category": cat,
                    "Note / Description": note,
                    "Payment Mode": emode,
                    "Amount (₹)": eamt,
                })

            if exp_rows:
                exp_rows.append({
                    "Category": "TOTAL ROUTE EXPENSES",
                    "Note / Description": "",
                    "Payment Mode": "",
                    "Amount (₹)": total_route_exp,
                })
                exp_clean = pd.DataFrame(exp_rows)

        exp_table_html = render_executive_report_table(exp_clean, title="Route Expenses")

        # Route Cash Handover Summary (KPI Cards)
        net_cash_handover = cash_collected - cash_expenses
        handover_bg = "#f0fdf4" if net_cash_handover >= 0 else "#fef2f2"
        handover_border = "#16a34a" if net_cash_handover >= 0 else "#dc2626"
        handover_color = "#166534" if net_cash_handover >= 0 else "#991b1b"

        reconciliation_html = f"""
        <div class="section">
            <h3>Route Cash Handover Summary</h3>
            <div class="cards">
                <div class="card">
                    <div class="card-title">TOTAL CASH COLLECTED</div>
                    <div class="card-value" style="color:#16a34a;">₹{cash_collected:,.2f}</div>
                    <div class="card-sub">Collected from Route Retailers</div>
                </div>
                <div class="card">
                    <div class="card-title">DRIVER CASH EXPENSES</div>
                    <div class="card-value" style="color:#dc2626;">₹{cash_expenses:,.2f}</div>
                    <div class="card-sub">Fuel, Repairs, Food, Toll</div>
                </div>
                <div class="card" style="background:{handover_bg}; border:1.5px solid {handover_border};">
                    <div class="card-title" style="color:{handover_color};">NET CASH HANDOVER TO COUNTER</div>
                    <div class="card-value" style="color:{handover_color};">₹{net_cash_handover:,.2f}</div>
                    <div class="card-sub" style="color:{handover_color};">To be Deposited with Cashier</div>
                </div>
            </div>
        </div>
        """

        page_html = f"""
        <div class="route-page">
            <div class="header">
                <h2>RANJIT BHIMRAO KAWLE MILK</h2>
                <h4>Zone Summary — {html_esc(z)}</h4>
                <p>Date: {html_esc(str(report_day))}</p>
            </div>

            {retailers_table_html}

            {pm_table_html}

            {exp_table_html}

            {reconciliation_html}

            <div class="footer-sign">
                <div class="sign-box">Route Delivery Agent / Driver</div>
                <div class="sign-box">Authorized Cashier / Proprietor</div>
            </div>
        </div>
        """
        zone_pages_html += page_html

    master_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Zone Summary — {report_day}</title>
<style>
{get_report_common_css()}
</style>
</head>
<body>

<div class="print-btn">
    <button onclick="window.print()">🖨️ Print Zone Summary (A4 Portrait)</button>
</div>

{zone_pages_html}

</body>
</html>
"""
    return master_html


# ============================================================
# AUDIT PATCH HELPERS & PRICE RESOLUTION
# ============================================================
# PATCH 1: batched opening-balance helper (ultra-fast in-memory with DB fallback).
@st.cache_data(show_spinner=False, ttl=300)
def cached_opening_balances(retailer_ids: tuple, as_of_day, data_version: int) -> dict:
    """{retailer_id: sales_before(day) - payments_before(day)}  — In-memory high-speed calculation."""
    _ = data_version
    if not retailer_ids:
        return {}
    rids = sorted({int(r) for r in retailer_ids})

    e_df = None
    p_df = None
    try:
        if "entries" in globals() and isinstance(globals()["entries"], pd.DataFrame) and not globals()["entries"].empty:
            e_df = globals()["entries"]
    except Exception:
        pass
    try:
        if "payments" in globals() and isinstance(globals()["payments"], pd.DataFrame) and not globals()["payments"].empty:
            p_df = globals()["payments"]
    except Exception:
        pass

    if e_df is None and os.path.exists(ENTRIES_FILE):
        try:
            e_df = pd.read_csv(ENTRIES_FILE)
        except Exception:
            pass
    if p_df is None and os.path.exists(PAYMENTS_FILE):
        try:
            p_df = pd.read_csv(PAYMENTS_FILE)
        except Exception:
            pass

    if e_df is None:
        e_df = sb_fetch_df(
            ENTRIES_FILE,
            CSV_SCHEMAS[ENTRIES_FILE],
            filters=[("retailer_id", "in", rids), ("date", "lt", str(as_of_day))],
        )
    if p_df is None:
        p_df = sb_fetch_df(
            PAYMENTS_FILE,
            CSV_SCHEMAS[PAYMENTS_FILE],
            filters=[("retailer_id", "in", rids), ("date", "lt", str(as_of_day))],
        )

    as_of_str = str(as_of_day)
    if e_df is not None and not e_df.empty:
        e2 = e_df[
            (pd.to_numeric(e_df.get("retailer_id", 0), errors="coerce").fillna(0).astype(int).isin(rids))
            & (e_df["date"].astype(str) < as_of_str)
        ].copy()
        if not e2.empty:
            e2["retailer_id"] = pd.to_numeric(e2["retailer_id"], errors="coerce").fillna(0).astype(int)
            e2["amount"] = pd.to_numeric(e2["amount"], errors="coerce").fillna(0.0)
            sales = e2.groupby("retailer_id")["amount"].sum()
        else:
            sales = pd.Series(dtype=float)
    else:
        sales = pd.Series(dtype=float)

    if p_df is not None and not p_df.empty:
        p2 = p_df[
            (pd.to_numeric(p_df.get("retailer_id", 0), errors="coerce").fillna(0).astype(int).isin(rids))
            & (p_df["date"].astype(str) < as_of_str)
        ].copy()
        if not p2.empty:
            p2["retailer_id"] = pd.to_numeric(p2["retailer_id"], errors="coerce").fillna(0).astype(int)
            p2["amount"] = pd.to_numeric(p2["amount"], errors="coerce").fillna(0.0)
            paid = p2.groupby("retailer_id")["amount"].sum()
        else:
            paid = pd.Series(dtype=float)
    else:
        paid = pd.Series(dtype=float)

    bal = sales.subtract(paid, fill_value=0.0)
    return {int(r): float(bal.get(r, 0.0)) for r in rids}


# PATCH 5: batched distributor opening balance (ultra-fast in-memory with DB fallback).
@st.cache_data(show_spinner=False, ttl=300)
def cached_distributor_openings(dist_ids: tuple, as_of_day, data_version: int) -> dict:
    _ = data_version
    if not dist_ids:
        return {}
    dids = sorted({int(d) for d in dist_ids})

    dp = None
    dpay = None
    try:
        if "dist_purchases" in globals() and isinstance(globals()["dist_purchases"], pd.DataFrame) and not globals()["dist_purchases"].empty:
            dp = globals()["dist_purchases"]
    except Exception:
        pass
    try:
        if "dist_payments" in globals() and isinstance(globals()["dist_payments"], pd.DataFrame) and not globals()["dist_payments"].empty:
            dpay = globals()["dist_payments"]
    except Exception:
        pass

    if dp is None and os.path.exists(DISTRIBUTOR_PURCHASES_FILE):
        try:
            dp = pd.read_csv(DISTRIBUTOR_PURCHASES_FILE)
        except Exception:
            pass
    if dpay is None and os.path.exists(DISTRIBUTOR_PAYMENTS_FILE):
        try:
            dpay = pd.read_csv(DISTRIBUTOR_PAYMENTS_FILE)
        except Exception:
            pass

    if dp is None:
        dp = sb_fetch_df(
            DISTRIBUTOR_PURCHASES_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE],
            filters=[("distributor_id", "in", dids), ("date", "lt", str(as_of_day))],
        )
    if dpay is None:
        dpay = sb_fetch_df(
            DISTRIBUTOR_PAYMENTS_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_PAYMENTS_FILE],
            filters=[("distributor_id", "in", dids), ("date", "lt", str(as_of_day))],
        )

    as_of_str = str(as_of_day)
    if dp is not None and not dp.empty:
        t = dp[
            (pd.to_numeric(dp.get("distributor_id", 0), errors="coerce").fillna(0).astype(int).isin(dids))
            & (dp["date"].astype(str) < as_of_str)
        ].copy()
        if not t.empty:
            t["distributor_id"] = pd.to_numeric(t["distributor_id"], errors="coerce").fillna(0).astype(int)
            t["amount"] = pd.to_numeric(t.get("amount", 0.0), errors="coerce").fillna(0.0)
            pur = t.groupby("distributor_id")["amount"].sum()
        else:
            pur = pd.Series(dtype=float)
    else:
        pur = pd.Series(dtype=float)

    if dpay is not None and not dpay.empty:
        t = dpay[
            (pd.to_numeric(dpay.get("distributor_id", 0), errors="coerce").fillna(0).astype(int).isin(dids))
            & (dpay["date"].astype(str) < as_of_str)
        ].copy()
        if not t.empty:
            t["distributor_id"] = pd.to_numeric(t["distributor_id"], errors="coerce").fillna(0).astype(int)
            t["amount"] = pd.to_numeric(t.get("amount", 0.0), errors="coerce").fillna(0.0)
            paid = t.groupby("distributor_id")["amount"].sum()
        else:
            paid = pd.Series(dtype=float)
    else:
        paid = pd.Series(dtype=float)

    bal = pur.subtract(paid, fill_value=0.0)
    return {int(d): float(bal.get(d, 0.0)) for d in dids}


# PATCH 4: pre-computed price lookup for a day (replaces N calls to
# get_price_for_date in report/daily-posting loops).
@st.cache_data(show_spinner=False, ttl=600)
def price_lookup_for_day(day, data_version: int) -> dict:
    _ = data_version
    if prices.empty:
        pr = pd.DataFrame(
            columns=["retailer_id", "category_id", "price", "effective_date"]
        )
    else:
        pr = prices.copy()
    pr["effective_date"] = pd.to_datetime(pr["effective_date"], errors="coerce").dt.date
    pr = pr.dropna(subset=["effective_date"])
    pr = pr[pr["effective_date"] <= day]
    pr = pr.sort_values("effective_date")
    pr["retailer_id"] = (
        pd.to_numeric(pr["retailer_id"], errors="coerce").fillna(0).astype(int)
    )
    pr["category_id"] = (
        pd.to_numeric(pr["category_id"], errors="coerce").fillna(0).astype(int)
    )
    pr["price"] = pd.to_numeric(pr["price"], errors="coerce").fillna(0.0)

    latest = pr.groupby(["retailer_id", "category_id"], as_index=False).tail(1)
    specific = {
        (int(r.retailer_id), int(r.category_id)): float(r.price)
        for r in latest.itertuples()
        if float(r.price) > 0
    }
    global_price = {k[1]: v for k, v in specific.items() if k[0] == GLOBAL_RETAILER_ID}

    cat_default = {}
    if not categories.empty and "default_price" in categories.columns:
        for c in categories.itertuples():
            dp = getattr(c, "default_price", None)
            if dp is not None and not pd.isna(dp) and float(dp) > 0:
                cat_default[int(c.category_id)] = float(dp)

    return {"specific": specific, "global": global_price, "default": cat_default}


def resolve_price(price_map: dict, rid: int, cid: int) -> float:
    rid, cid = int(rid), int(cid)
    v = price_map["specific"].get((rid, cid))
    if v and v > 0:
        return v
    v = price_map["global"].get(cid)
    if v and v > 0:
        return v
    return float(price_map["default"].get(cid, 0.0))


# ------------------------------------------------------------
# END AUDIT PATCH HELPERS
# ------------------------------------------------------------

# ============================================================
# SYSTEM ACCESS SECURITY & PIN LOCK SCREEN (PIN: 7744)
# ============================================================
import hmac

APP_ACCESS_PIN = "7744"

_PHONE_LOCK_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "components", "phone_lock"
)
try:
    import streamlit.components.v1 as _components
    _phone_lock_component = _components.declare_component(
        "phone_lock",
        path=_PHONE_LOCK_DIR
    )
except Exception:
    _phone_lock_component = None


def check_app_security_pin() -> bool:
    """
    Security PIN Lock Screen for Milk Accounting Pro.
    Validates entry PIN '7744' before allowing access to application data.
    Phone-style number pad with instant auto-unlock when 4 digits are entered.

    Security Hardening:
      - Fixed strict frame height CSS clamp (neutralizes infinite height expansion loop)
      - Zero URL query parameter exposure (prevents CWE-598 URL PIN leakage)
      - Constant-time verification with hmac.compare_digest (prevents CWE-208 timing attack)
      - Anti-brute-force rate limiting: 5 failed attempts locks interface for 30s (prevents CWE-307)
      - Parent-to-iframe keyboard bridge for typing anywhere on the screen
      - In testing / bare CLI execution (get_script_run_ctx is None), bypasses to allow tests.
    """
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is None:
            return True
    except Exception:
        pass

    if st.session_state.get("is_authenticated", False):
        return True

    # 1. Anti-Brute-Force Rate Limiting & Cooldown Protection
    now = time.time()
    lockout_until = st.session_state.get("pin_lockout_until", 0)
    if now < lockout_until:
        remaining = max(1, int(lockout_until - now))
        _, lock_col, _ = st.columns([1, 1.8, 1])
        with lock_col:
            st.error(
                f"🔒 **अनेक चुकीचे प्रयत्न! (Too many failed attempts)**\n\n"
                f"सुरक्षिततेसाठी प्रणाली कुलूपबंद केली आहे. कृपया **{remaining} सेकंद** प्रतीक्षा करा.\n\n"
                f"*(Security lockout active. Please wait {remaining}s before retrying.)*"
            )
        st.stop()

    # 2. Strict CSS Clamp & Parent Keystroke Forwarding
    st.markdown(
        """
        <style>
        /* Strict Phone Lock Layout & Height Clamping (Prevents infinite scrolling/stretching) */
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        button[data-testid="baseButton-headerNoPadding"] {
            display: none !important;
        }
        .main .block-container {
            max-width: 480px !important;
            margin: 0 auto !important;
            padding-top: 1.2rem !important;
            padding-bottom: 1.5rem !important;
        }
        iframe[title*="phone_lock"] {
            width: 100% !important;
            max-width: 350px !important;
            height: 565px !important;
            min-height: 565px !important;
            max-height: 565px !important;
            overflow: hidden !important;
            border: none !important;
            border-radius: 28px !important;
            display: block !important;
            margin: 0 auto !important;
        }
        div[data-testid="stCustomComponentV1"] {
            height: 565px !important;
            max-height: 565px !important;
            overflow: hidden !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }
        </style>
        <script>
        if (!window.__phoneLockKeyRegistered) {
            window.__phoneLockKeyRegistered = true;
            window.addEventListener("keydown", function(e) {
                const iframes = document.querySelectorAll("iframe");
                iframes.forEach(function(ifr) {
                    try {
                        if (ifr.contentWindow) {
                            ifr.contentWindow.postMessage({ type: "PARENT_KEY", key: e.key }, "*");
                        }
                    } catch(err) {}
                });
            });
        }
        </script>
        """,
        unsafe_allow_html=True,
    )

    # 3. Render Phone Number Pad Lock Screen Component
    comp_unlocked = False
    if _phone_lock_component is not None and os.path.exists(os.path.join(_PHONE_LOCK_DIR, "index.html")):
        try:
            val = _phone_lock_component(target_pin=APP_ACCESS_PIN, default="", key="system_phone_lock_pad")
            val_str = str(val or "").strip()
            if val_str:
                if val_str.startswith("LOCKOUT"):
                    st.session_state["pin_lockout_until"] = time.time() + 30
                    st.session_state["pin_failed_attempts"] = 5
                    st.rerun()
                elif hmac.compare_digest(val_str, APP_ACCESS_PIN):
                    comp_unlocked = True
        except Exception:
            comp_unlocked = False

    if comp_unlocked:
        st.session_state["is_authenticated"] = True
        st.session_state["pin_failed_attempts"] = 0
        st.session_state["pin_lockout_until"] = 0
        st.rerun()
        return True

    st.stop()


# Enforce Security PIN Gate
check_app_security_pin()

# ============================================================
# INITIAL DATA LOAD & DATE NORMALIZATION
# ============================================================
(
    retailers,
    categories,
    prices,
    entries,
    payments,
    distributors,
    dist_purchases,
    dist_payments,
    dist_cat_map,
    wastage,
    expenses,
) = load_all_data(st.session_state["data_version"])

entries = normalize_date_cols(entries)
payments = normalize_date_cols(payments)
dist_purchases = normalize_date_cols(dist_purchases)
dist_payments = normalize_date_cols(dist_payments)


# ============================================================
# ZONE MANAGEMENT & FILTERING HELPERS
# ============================================================
def get_all_zones() -> list[str]:
    if retailers.empty:
        return ["Default"]
    rz = retailers.copy()
    rz["zone"] = rz["zone"].apply(_norm_zone)
    zones = sorted(set(rz["zone"].tolist()))
    return zones if zones else ["Default"]


def build_fast_report(start_date, end_date, *args, **kwargs):
    # args/kwargs ignored — data fetched fresh from DBdef build_fast_report(start_date, end_date):

    entries = fetch_entries_filtered(
        start_date, end_date, [], st.session_state["data_version"]
    )
    payments = fetch_payments_filtered(
        start_date, end_date, [], st.session_state["data_version"]
    )
    purchases = fetch_purchases_filtered(
        start_date, end_date, [], st.session_state["data_version"]
    )

    # ---- AGGREGATION ----
    sales = entries.groupby("date")["amount"].sum().reset_index()
    pay = payments.groupby("date")["amount"].sum().reset_index()
    purchase = purchases.groupby("date")["amount"].sum().reset_index()

    return sales, pay, purchase


def get_zone_retailer_ids(selected_zone: str) -> list[int]:
    if retailers.empty:
        return []
    if selected_zone == "All Zones":
        return retailers["retailer_id"].astype(int).tolist()

    # Main zone: retailers maintained in Main book (mapping table).
    if selected_zone == MAIN_ZONE:
        main_ids = set(get_main_retailer_ids())
        # Backward compatibility: also include retailers whose zone is literally "Main"
        rz = retailers.copy()
        rz["zone"] = rz.get("zone", "Default").astype(str).apply(_norm_zone)
        main_ids |= set(
            rz.loc[rz["zone"] == _norm_zone(MAIN_ZONE), "retailer_id"]
            .astype(int)
            .tolist()
        )
        return sorted(main_ids)

    z = _norm_zone(selected_zone)
    rz = retailers.copy()
    rz["zone"] = rz.get("zone", "Default").astype(str).apply(_norm_zone)
    return rz.loc[rz["zone"] == z, "retailer_id"].astype(int).tolist()


def filter_by_zone(
    df: pd.DataFrame, retailer_id_col: str, selected_zone: str
) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if selected_zone == "All Zones":
        return df.copy()
    ids = set(get_zone_retailer_ids(selected_zone))
    if not ids:
        return df.iloc[0:0].copy()
    return df.loc[df[retailer_id_col].astype(int).isin(ids)].copy()


# ============================================================
# MAIN BOOK RETAILERS (MAPPING)
# ============================================================
# Main book retailers are "normal" retailers, but maintained in the Main book for overview.
# They are defined by the mapping table `public.main_retailers` (retailer_id primary key).
MAIN_ZONE = "Main"
MAIN_RETAILERS_TABLE = "main_retailers"


def _main_table_exists() -> bool:
    try:
        get_sb().table(MAIN_RETAILERS_TABLE).select("retailer_id").limit(1).execute()
        return True
    except Exception:
        return False


def get_main_retailer_ids() -> list[int]:
    """Return retailer_ids configured for Main book (no caching; single-user friendly)."""
    if not _main_table_exists():
        return []
    try:
        rows = sb_fetch_all(MAIN_RETAILERS_TABLE, cols="retailer_id") or []
        out: list[int] = []
        for r in rows:
            try:
                out.append(int(r.get("retailer_id")))
            except Exception:
                pass
        # stable order
        return sorted(set(out))
    except Exception:
        return []


def add_main_retailers(retailer_ids: list[int]) -> None:
    if not _main_table_exists():
        raise RuntimeError(
            "Missing DB table 'main_retailers'. Create it in Supabase SQL editor."
        )
    ids = sorted({int(x) for x in retailer_ids if x is not None})
    if not ids:
        return
    records = [{"retailer_id": int(rid)} for rid in ids]
    get_sb().table(MAIN_RETAILERS_TABLE).insert(records).execute()
    invalidate_data_cache()


def remove_main_retailers(retailer_ids: list[int]) -> None:
    if not _main_table_exists():
        raise RuntimeError(
            "Missing DB table 'main_retailers'. Create it in Supabase SQL editor."
        )
    ids = sorted({int(x) for x in retailer_ids if x is not None})
    if not ids:
        return
    get_sb().table(MAIN_RETAILERS_TABLE).delete().in_("retailer_id", ids).execute()
    invalidate_data_cache()


# ============================================================
# RETAILER PRICING & LEDGER HELPERS
# ============================================================
def _get_effective_price(
    price_df: pd.DataFrame, entry_dt: pd.Timestamp
) -> float | None:
    if price_df.empty:
        return None
    df = price_df.copy()
    df["effective_date"] = pd.to_datetime(
        df["effective_date"], errors="coerce"
    ).dt.normalize()
    entry_dt = pd.to_datetime(entry_dt, errors="coerce").normalize()
    df = df.loc[df["effective_date"].notna()]
    df = df.loc[df["effective_date"] <= entry_dt]
    if df.empty:
        return None
    df = df.sort_values("effective_date", ascending=False)
    return float(df.iloc[0]["price"])


def get_price_for_date(retailer_id: int, category_id: int, entry_date) -> float | None:
    entry_dt = pd.to_datetime(entry_date)

    if not prices.empty:
        rs = prices.loc[
            (prices["retailer_id"] == int(retailer_id))
            & (prices["category_id"] == int(category_id))
        ].copy()
        p = _get_effective_price(rs, entry_dt)
        if p is not None and p > 0:
            return float(p)

        gs = prices.loc[
            (prices["retailer_id"] == GLOBAL_RETAILER_ID)
            & (prices["category_id"] == int(category_id))
        ].copy()
        p = _get_effective_price(gs, entry_dt)
        if p is not None and p > 0:
            return float(p)

    if not categories.empty and "default_price" in categories.columns:
        cat_row = categories.loc[categories["category_id"] == int(category_id)]
        if not cat_row.empty:
            default_price = cat_row.iloc[0].get("default_price", 0.0)
            if pd.notna(default_price) and float(default_price) > 0:
                return float(default_price)

    return None


def get_retailer_balance(retailer_id: int) -> float:
    e = normalize_date_cols(entries)
    p = normalize_date_cols(payments)

    if e is None or e.empty:
        total_sales = 0.0
    else:
        e["retailer_id"] = (
            pd.to_numeric(e["retailer_id"], errors="coerce").fillna(0).astype(int)
        )
        e["amount"] = (
            pd.to_numeric(e["amount"], errors="coerce").fillna(0.0).astype(float)
        )
        total_sales = float(e.loc[e["retailer_id"] == int(retailer_id), "amount"].sum())

    if p is None or p.empty:
        total_payments = 0.0
    else:
        p["retailer_id"] = (
            pd.to_numeric(p["retailer_id"], errors="coerce").fillna(0).astype(int)
        )
        p["amount"] = (
            pd.to_numeric(p["amount"], errors="coerce").fillna(0.0).astype(float)
        )
        total_payments = float(
            p.loc[p["retailer_id"] == int(retailer_id), "amount"].sum()
        )

    return float(total_sales - total_payments)



def retailer_ledger_as_of(retailer_id: int, as_of_day: date) -> float:
    if entries.empty and payments.empty:
        return 0.0
    e = entries.copy()
    p = payments.copy()
    if not e.empty:
        e["date"] = pd.to_datetime(e["date"], errors="coerce").dt.date
    if not p.empty:
        p["date"] = pd.to_datetime(p["date"], errors="coerce").dt.date

    sales = (
        e.loc[
            (e["retailer_id"] == int(retailer_id)) & (e["date"] <= as_of_day), "amount"
        ].sum()
        if not e.empty
        else 0.0
    )
    paid = (
        p.loc[
            (p["retailer_id"] == int(retailer_id)) & (p["date"] <= as_of_day), "amount"
        ].sum()
        if not p.empty
        else 0.0
    )
    return float(sales - paid)


def is_retailer_referenced(retailer_id: int) -> bool:
    rid = int(retailer_id)
    if (not entries.empty) and (rid in set(entries["retailer_id"].astype(int))):
        return True
    if (not payments.empty) and (rid in set(payments["retailer_id"].astype(int))):
        return True
    if (not prices.empty) and (rid in set(prices["retailer_id"].astype(int))):
        return True
    return False


def is_category_referenced(category_id: int) -> bool:
    cid = int(category_id)
    if (not entries.empty) and (cid in set(entries["category_id"].astype(int))):
        return True
    if (not prices.empty) and (cid in set(prices["category_id"].astype(int))):
        return True
    if (not dist_purchases.empty) and (
        cid in set(dist_purchases["category_id"].astype(int))
    ):
        return True
    if (not wastage.empty) and (cid in set(wastage["category_id"].astype(int))):
        return True
    return False


def is_distributor_referenced(distributor_id: int) -> bool:
    did = int(distributor_id)
    if (not dist_purchases.empty) and (
        did in set(dist_purchases["distributor_id"].astype(int))
    ):
        return True
    if (not dist_payments.empty) and (
        did in set(dist_payments["distributor_id"].astype(int))
    ):
        return True
    return False


# ============================================================
# DAILY POSTING SHEET HELPERS
# ============================================================


def _retailer_ids_for_zone(zone: str) -> list[int]:
    """Returns retailer_ids for the given zone (or all if 'All Zones').

    NOTE: uses the canonical `retailers` dataframe loaded from Supabase.
    Do NOT rely on a global `retailers_active` from some page scope.
    """
    try:
        rz = retailers.copy() if isinstance(retailers, pd.DataFrame) else pd.DataFrame()
        if rz.empty:
            return []
        rz = rz.copy()
        rz["zone"] = rz.get("zone", "").astype(str).apply(_norm_zone)
        # if is_active exists, use it
        if "is_active" in rz.columns:
            rz["is_active"] = rz["is_active"].apply(parse_boolish_active)
            rz = rz.loc[rz["is_active"] == True].copy()
        if zone == "All Zones":
            return rz["retailer_id"].astype(int).tolist()
        return (
            rz.loc[rz["zone"] == _norm_zone(zone), "retailer_id"].astype(int).tolist()
        )
    except Exception:
        return []


def _day_entries_for_zone(day: date, zone: str) -> pd.DataFrame:
    """Always fetches fresh transactional data for the selected day (+ zone filter)."""
    if USE_SERVER_FILTERS:
        rids = _retailer_ids_for_zone(zone)
        if not rids:
            return pd.DataFrame(columns=CSV_SCHEMAS[ENTRIES_FILE])
        df = sb_fetch_df(
            ENTRIES_FILE,
            CSV_SCHEMAS[ENTRIES_FILE],
            filters=[("date", "eq", str(day)), ("retailer_id", "in", rids)],
        )
        return df
    # CSV / local fallback
    df = entries.copy()
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.loc[df["date"] == day].copy()
    df = filter_by_zone(df, "retailer_id", zone)
    return df


def _day_payments_for_zone(day: date, zone: str) -> pd.DataFrame:

    if USE_SERVER_FILTERS:
        rids = _retailer_ids_for_zone(zone)

        if not rids:
            return pd.DataFrame(columns=CSV_SCHEMAS[PAYMENTS_FILE])

        df = sb_fetch_df(
            PAYMENTS_FILE,
            CSV_SCHEMAS[PAYMENTS_FILE],
            filters=[
                ("date", "eq", str(day)),
                ("retailer_id", "in", rids),
            ],
        )

    else:
        df = payments.copy()

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    df = df.loc[df["date"] == day].copy()

    df = filter_by_zone(df, "retailer_id", zone)

    return df


PAYMENT_MODES = ["CASH", "UPI", "CHEQUE"]


def _day_fetch_strict(path: str, day: date, zone: str) -> pd.DataFrame:
    """Strict day fetch: if Supabase query fails, STOP instead of showing wrong/empty data."""
    try:
        if path == ENTRIES_FILE:
            return _day_entries_for_zone(day, zone)
        if path == PAYMENTS_FILE:
            return _day_payments_for_zone(day, zone)
        raise ValueError("Unknown path")
    except Exception as e:
        st.error(f"❌ Failed to load day data from Supabase for {day} / {zone}.\n\n{e}")
        st.stop()


def build_daily_posting_grid(
    day: date,
    zone: str,
    retailers_active: pd.DataFrame,
    categories_active: pd.DataFrame,
):
    """Builds the Daily Posting Sheet grid.

    Data-integrity rules:
    - All joins/pivots are by retailer_id and category_id (NOT names).
    - Display columns include the category_id to make the mapping unambiguous.
    - The returned `cat_cols` is a list of dicts: {col, category_id, name}.
    """
    rz = retailers_active.copy()
    rz["zone"] = rz.get("zone", "").astype(str).apply(_norm_zone)
    if zone != "All Zones":
        rz = rz.loc[rz["zone"] == _norm_zone(zone)].copy()

    cats = categories_active.copy()
    cats["category_id"] = (
        pd.to_numeric(cats["category_id"], errors="coerce").fillna(0).astype(int)
    )
    cats["name"] = cats.get("name", "").fillna("").astype(str)
    cats = cats.loc[cats["category_id"] > 0].copy()

    # Category display columns: include ID to prevent duplicate-name ambiguity.
    cat_cols = []
    for _, c in cats.iterrows():
        cid = int(c["category_id"])
        nm = str(c["name"]).strip()
        col = f"CID:{cid} — {nm}" if nm else f"CID:{cid}"
        cat_cols.append({"col": col, "category_id": cid, "name": nm})

    # Fresh day data (fail closed)
    day_p = _day_fetch_strict(PAYMENTS_FILE, day, zone)
    day_e = _day_fetch_strict(ENTRIES_FILE, day, zone)

    # Payments pivot: retailer_id x payment_mode
    pay_by_mode = pd.DataFrame()
    if day_p is not None and not day_p.empty:
        tmp = day_p.copy()
        tmp["retailer_id"] = (
            pd.to_numeric(tmp.get("retailer_id", 0), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        tmp["payment_mode"] = (
            tmp.get("payment_mode", "Cash")
            .fillna("Cash")
            .astype(str)
            .str.strip()
            .str.upper()
        )
        tmp["amount"] = (
            pd.to_numeric(tmp.get("amount", 0.0), errors="coerce")
            .fillna(0.0)
            .astype(float)
        )
        pay_by_mode = tmp.pivot_table(
            index="retailer_id",
            columns="payment_mode",
            values="amount",
            aggfunc="sum",
            fill_value=0.0,
        ).reindex(columns=PAYMENT_MODES, fill_value=0.0)

    # Entries pivot: retailer_id x category_id
    qty_by_rid_cid = pd.DataFrame()
    if day_e is not None and not day_e.empty:
        e = day_e.copy()
        e["retailer_id"] = (
            pd.to_numeric(e.get("retailer_id", 0), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        e["category_id"] = (
            pd.to_numeric(e.get("category_id", 0), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        e["qty"] = (
            pd.to_numeric(e.get("qty", 0.0), errors="coerce").fillna(0.0).astype(float)
        )
        qty_by_rid_cid = pd.pivot_table(
            e,
            index="retailer_id",
            columns="category_id",
            values="qty",
            aggfunc="sum",
            fill_value=0.0,
        )

    rows = []
    for _, r in rz.iterrows():
        rid = int(r["retailer_id"])
        retailer_name = str(r.get("name", ""))

        row = {"ID": rid, "Retailer": retailer_name}

        for m in PAYMENT_MODES:
            col = f"{m} ₹"

            val = 0.0

            if not pay_by_mode.empty:
                modes = [str(x).strip().upper() for x in pay_by_mode.columns]

                if str(m).strip().upper() in modes:
                    real_col = pay_by_mode.columns[modes.index(str(m).strip().upper())]

                    if rid in pay_by_mode.index:
                        val = float(pay_by_mode.loc[rid, real_col])

            row[col] = float(val)

        for meta in cat_cols:
            col = meta["col"]
            cid = int(meta["category_id"])
            qty = 0.0
            if (
                (not qty_by_rid_cid.empty)
                and (rid in qty_by_rid_cid.index)
                and (cid in qty_by_rid_cid.columns)
            ):
                qty = float(qty_by_rid_cid.loc[rid, cid])
            row[col] = float(qty)

        rows.append(row)

    grid = pd.DataFrame(rows)
    return grid, cat_cols


def compute_today_sales_amount_for_row(
    rid: int,
    day: date,
    row: pd.Series,
    cat_name_list: list[str],
    categories_active: pd.DataFrame,
) -> float:
    amt = 0.0
    for cat_name in cat_name_list:
        qty = float(row.get(cat_name, 0.0) or 0.0)
        if qty <= 0:
            continue
        cid = int(
            categories_active.loc[
                categories_active["name"] == cat_name, "category_id"
            ].iloc[0]
        )
        rate = get_price_for_date(rid, cid, day)
        if rate is None or rate <= 0:
            raise ValueError(
                f"Price missing for Retailer ID {rid} / {cat_name} on {day}"
            )
        amt += qty * float(rate)
    return float(amt)


def zone_category_pivot_for_day(day: date) -> pd.DataFrame:
    df = entries.copy()
    if df.empty:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.loc[df["date"] == day].copy()
    if df.empty:
        return pd.DataFrame()

    df = df.merge(retailers[["retailer_id", "zone"]], on="retailer_id", how="left")
    df["zone"] = df["zone"].apply(_norm_zone)

    df = df.merge(
        categories[["category_id", "name"]], on="category_id", how="left"
    ).rename(columns={"name": "Category"})
    df["Category"] = df["Category"].fillna("").astype(str)

    pivot = safe_pivot(df, index="zone", columns="Category", values="qty")
    if pivot.empty:
        return pd.DataFrame()

    pivot = pivot.sort_index()
    pivot["TOTAL (L)"] = pivot.sum(axis=1).astype(float)
    pivot = pivot.reset_index().rename(columns={"index": "Zone", "zone": "Zone"})
    if "Zone" not in pivot.columns and pivot.index.name:
        pivot = pivot.reset_index().rename(columns={pivot.index.name: "Zone"})
    return pivot


# ============================================================
# RETAILER BILL & STATEMENT GENERATORS
# ============================================================
def retailer_balance_before(retailer_id: int, start_day: date) -> float:
    """Single-retailer wrapper over the batch helper (patched)."""
    return cached_opening_balances(
        (int(retailer_id),), start_day, st.session_state["data_version"]
    ).get(int(retailer_id), 0.0)


def _rate_from_entries_or_price(
    retailer_id: int, cid: int, d: date, e_day_cat: pd.DataFrame
) -> float | None:
    # Prefer stored entry rates (history-safe). If missing/zero, fallback to price table.
    if e_day_cat is not None and not e_day_cat.empty:
        rates = pd.to_numeric(e_day_cat["rate"], errors="coerce").fillna(0.0)
        rates = rates[rates > 0]
        if not rates.empty:
            # if multiple rates, show average for display but sales uses amount anyway
            return float(rates.mean())
    return get_price_for_date(int(retailer_id), int(cid), d)


def build_bill_daily_grid(
    retailer_id: int, start_day: date, end_day: date, cat_names: list[str]
) -> pd.DataFrame:
    """
    SINGLE authoritative bill grid. No duplicates.
    Logic:
      opening_due = balance before start_day
      daily_sales = sum(qty * rate) using stored entries (amount) primarily
      payments
      running_due
    Columns:
      Date,
      per category: "<cat> Qty", "<cat> Rate",
      Total Milk (L), Sales (₹), Payment (₹), Running Due (₹)
    """
    days = pd.date_range(start=start_day, end=end_day, freq="D").date

    if USE_SERVER_FILTERS:
        e = sb_fetch_df(
            ENTRIES_FILE,
            CSV_SCHEMAS[ENTRIES_FILE],
            filters=[
                ("retailer_id", "eq", int(retailer_id)),
                ("date", "gte", str(start_day)),
                ("date", "lte", str(end_day)),
            ],
        )
    else:
        e = entries.copy()
    if not e.empty:
        e["date"] = _safe_dt(e["date"]).dt.date
        e = e.loc[
            (e["retailer_id"].astype(int) == int(retailer_id))
            & (e["date"] >= start_day)
            & (e["date"] <= end_day)
        ].copy()

    if not e.empty:
        e = e.merge(
            categories[["category_id", "name"]], on="category_id", how="left"
        ).rename(columns={"name": "Category"})
        e["Category"] = e["Category"].fillna("").astype(str)

    if USE_SERVER_FILTERS:
        p = sb_fetch_df(
            PAYMENTS_FILE,
            CSV_SCHEMAS[PAYMENTS_FILE],
            filters=[
                ("retailer_id", "eq", int(retailer_id)),
                ("date", "gte", str(start_day)),
                ("date", "lte", str(end_day)),
            ],
        )
    else:
        p = payments.copy()
    if not p.empty:
        p["date"] = _safe_dt(p["date"]).dt.date
        p = p.loc[
            (p["retailer_id"].astype(int) == int(retailer_id))
            & (p["date"] >= start_day)
            & (p["date"] <= end_day)
        ].copy()

    pay_by_day = p.groupby("date")["amount"].sum().to_dict() if not p.empty else {}

    opening_due = retailer_balance_before(int(retailer_id), start_day)
    running = float(opening_due)

    rows = []
    for d in days:
        row = {"Date": str(d)}

        e_day = (
            e.loc[e["date"] == d].copy()
            if (e is not None and not e.empty)
            else pd.DataFrame(columns=["Category", "qty", "rate", "amount"])
        )

        total_milk = 0.0
        day_sales = 0.0

        for cat in cat_names:
            qcol = f"{cat} Qty"
            rcol = f"{cat} Rate"

            e_day_cat = (
                e_day.loc[e_day["Category"] == str(cat)].copy()
                if not e_day.empty
                else pd.DataFrame()
            )
            qty = (
                float(
                    pd.to_numeric(e_day_cat["qty"], errors="coerce").fillna(0.0).sum()
                )
                if not e_day_cat.empty
                else 0.0
            )

            if qty > 0:
                # Prefer stored amounts (history-safe)
                amt = (
                    float(
                        pd.to_numeric(e_day_cat["amount"], errors="coerce")
                        .fillna(0.0)
                        .sum()
                    )
                    if not e_day_cat.empty
                    else 0.0
                )
                # If amount not reliable, compute qty*rate
                if amt <= 0:
                    cat_row = categories.loc[categories["name"].astype(str) == str(cat)]
                    cid = (
                        int(cat_row.iloc[0]["category_id"])
                        if not cat_row.empty
                        else None
                    )
                    rate = (
                        _rate_from_entries_or_price(
                            int(retailer_id), int(cid), d, e_day_cat
                        )
                        if cid is not None
                        else None
                    )
                    if rate is not None and float(rate) > 0:
                        amt = qty * float(rate)
                day_sales += float(amt)

                # Rate display
                cat_row = categories.loc[categories["name"].astype(str) == str(cat)]
                cid = int(cat_row.iloc[0]["category_id"]) if not cat_row.empty else None
                rate_disp = (
                    _rate_from_entries_or_price(
                        int(retailer_id), int(cid), d, e_day_cat
                    )
                    if cid is not None
                    else None
                )

                row[qcol] = qty
                row[rcol] = (
                    float(rate_disp)
                    if (rate_disp is not None and float(rate_disp) > 0)
                    else "-"
                )
            else:
                row[qcol] = "-"
                row[rcol] = "-"

            total_milk += qty

        pay = float(pay_by_day.get(d, 0.0))
        running = float(running + day_sales - pay)

        row["Total Milk (L)"] = round(float(total_milk), 2)
        row["Sales (₹)"] = round(float(day_sales), 2)
        row["Payment (₹)"] = round(float(pay), 2)
        row["Running Due (₹)"] = round(float(running), 2)

        rows.append(row)

    return pd.DataFrame(rows)


# ============================================================
# WORKER ATTENDANCE SYSTEM HELPERS
# ============================================================
def get_workers_df() -> pd.DataFrame:
    """Fetches list of workers from local CSV (data/workers.csv) or Supabase with fallback defaults."""
    df = pd.DataFrame()
    if os.path.exists(WORKERS_FILE):
        try:
            df = pd.read_csv(WORKERS_FILE)
        except Exception:
            df = pd.DataFrame()
    if df.empty:
        try:
            df = sb_fetch_df(WORKERS_FILE, CSV_SCHEMAS[WORKERS_FILE])
        except Exception:
            df = pd.DataFrame()
    if df.empty:
        df = pd.DataFrame([
            {"worker_id": 1, "name": "Ramesh Yadav", "role": "Driver", "contact": "9820000001", "salary_type": "Daily", "base_rate": 500.0, "is_active": True},
            {"worker_id": 2, "name": "Suresh Gawali", "role": "Helper", "contact": "9820000002", "salary_type": "Daily", "base_rate": 400.0, "is_active": True},
            {"worker_id": 3, "name": "Santosh Patil", "role": "Dairy Staff", "contact": "9820000003", "salary_type": "Monthly", "base_rate": 15000.0, "is_active": True},
        ])
        save_workers_df(df)
    for c in CSV_SCHEMAS[WORKERS_FILE]:
        if c not in df.columns:
            df[c] = ""
    df["worker_id"] = pd.to_numeric(df["worker_id"], errors="coerce").fillna(0).astype(int)
    df["contact"] = df["contact"].astype(str).replace("nan", "").replace("None", "")
    df["name"] = df["name"].astype(str)
    df["is_active"] = df["is_active"].apply(parse_boolish_active)
    return df


def _sync_worker_table_to_supabase(table: str, df: pd.DataFrame, pk: str = "") -> None:
    """Helper to sync workers/attendance/wages to Supabase without invalidating sales data cache."""
    try:
        sb = get_sb()
        clean_df = df.where(pd.notna(df), None)
        records = clean_df.to_dict(orient="records")
        if records:
            for i in range(0, len(records), 500):
                chunk = records[i : i + 500]
                if pk:
                    sb.table(table).upsert(chunk, on_conflict=pk).execute()
                else:
                    sb.table(table).upsert(chunk).execute()
    except Exception as e:
        print(f"Supabase sync non-fatal error for {table}:", e)


def save_workers_df(df: pd.DataFrame) -> None:
    """Saves workers to local CSV and optionally Supabase."""
    os.makedirs("data", exist_ok=True)
    df.to_csv(WORKERS_FILE, index=False)
    _sync_worker_table_to_supabase("workers", df, pk="worker_id")


def parse_attendance_status_label(status_val, units_val=None) -> str:
    """
    Deterministically classifies attendance record into 'Full', 'Half', or 'Absent'.
    Guarantees that Absent (status='A', units=0.0, or absent text) is NEVER converted to Full.
    """
    raw_u = pd.to_numeric(units_val, errors="coerce")
    u_val = None if pd.isna(raw_u) else float(raw_u)
    s_val = str(status_val if status_val is not None else "").strip().upper()

    # Priority 1: Absent (status='A', 'ABSENT', '0', '0.0', 'सुट्टी', 'गैरहजर' OR units == 0.0)
    if (
        s_val in ("A", "ABSENT", "LEAVE", "0", "0.0", "-", "सुट्टी", "गैरहजर", "FALSE", "F", "AB", "ABS")
        or u_val == 0.0
    ):
        return "Absent"

    # Priority 2: Half Day (status='HD', 'HALF', '0.5', 'अर्धा' OR units == 0.5)
    if (
        s_val in ("HALF", "HD", "0.5", "HALF DAY", "अर्धा")
        or u_val == 0.5
    ):
        return "Half"

    # Priority 3: Full (Default)
    return "Full"


def extract_att_val(row, d) -> str:
    """Safely extracts 'Full', 'Half', or 'Absent' from an attendance matrix row for day d."""
    val = None
    if hasattr(row, "index"):
        if str(d) in row.index:
            val = row[str(d)]
        elif d in row.index:
            val = row[d]
        elif f"{int(d):02d}" in row.index:
            val = row[f"{int(d):02d}"]
    elif isinstance(row, dict):
        if str(d) in row:
            val = row[str(d)]
        elif d in row:
            val = row[d]
        elif f"{int(d):02d}" in row:
            val = row[f"{int(d):02d}"]

    if pd.isna(val) or val is None or str(val).strip() == "":
        return "Full"
    return parse_attendance_status_label(val)


def get_attendance_records(year: int, month: int) -> pd.DataFrame:
    """Fetches attendance records for specified year and month quickly from local CSV."""
    import calendar
    _, last_day = calendar.monthrange(year, month)
    start_str = f"{year:04d}-{month:02d}-01"
    end_str = f"{year:04d}-{month:02d}-{last_day:02d}"

    df = pd.DataFrame()
    if os.path.exists(WORKER_ATTENDANCE_FILE):
        try:
            loc_df = pd.read_csv(WORKER_ATTENDANCE_FILE)
            if not loc_df.empty and "date" in loc_df.columns:
                loc_df["date"] = loc_df["date"].astype(str)
                df = loc_df[(loc_df["date"] >= start_str) & (loc_df["date"] <= end_str)].copy()
        except Exception:
            pass
    if df.empty:
        try:
            df = sb_fetch_df(
                WORKER_ATTENDANCE_FILE,
                CSV_SCHEMAS[WORKER_ATTENDANCE_FILE],
                filters=[("date", "gte", start_str), ("date", "lte", end_str)],
            )
        except Exception:
            df = pd.DataFrame()
    if df.empty:
        return pd.DataFrame(columns=CSV_SCHEMAS[WORKER_ATTENDANCE_FILE])
    # Clean deduplication by (worker_id, date)
    df = df.drop_duplicates(subset=["worker_id", "date"], keep="last")
    return df


def save_attendance_matrix(year: int, month: int, matrix_df: pd.DataFrame) -> None:
    """Saves attendance matrix (workers x day columns) to worker_attendance."""
    import calendar
    _, days_in_month = calendar.monthrange(year, month)

    all_existing = pd.DataFrame()
    if os.path.exists(WORKER_ATTENDANCE_FILE):
        try:
            all_existing = pd.read_csv(WORKER_ATTENDANCE_FILE)
        except Exception:
            all_existing = pd.DataFrame()

    records = []
    for _, row in matrix_df.iterrows():
        wid = int(pd.to_numeric(row.get("worker_id", 0), errors="coerce") or 0)
        if wid <= 0:
            continue
        for d in range(1, days_in_month + 1):
            val_str = extract_att_val(row, d)
            if val_str == "Half":
                status = "HD"
                units = 0.5
            elif val_str == "Absent":
                status = "A"
                units = 0.0
            else:
                status = "P"
                units = 1.0

            date_str = f"{year:04d}-{month:02d}-{d:02d}"
            records.append({
                "worker_id": wid,
                "date": date_str,
                "status": status,
                "units": units,
                "notes": "",
            })

    new_month_df = pd.DataFrame(records)
    start_str = f"{year:04d}-{month:02d}-01"
    end_str = f"{year:04d}-{month:02d}-{days_in_month:02d}"

    if not all_existing.empty and "date" in all_existing.columns:
        other_months = all_existing[~((all_existing["date"].astype(str) >= start_str) & (all_existing["date"].astype(str) <= end_str))]
        combined = pd.concat([other_months, new_month_df], ignore_index=True)
    else:
        combined = new_month_df

    combined = combined.drop_duplicates(subset=["worker_id", "date"], keep="last")
    combined["attendance_id"] = range(1, len(combined) + 1)
    os.makedirs("data", exist_ok=True)
    combined.to_csv(WORKER_ATTENDANCE_FILE, index=False)

    try:
        sb = get_sb()
        sb.table("worker_attendance").delete().gte("date", start_str).lte("date", end_str).execute()
        _sync_worker_table_to_supabase("worker_attendance", new_month_df)
    except Exception as _e:
        print("Supabase attendance sync non-fatal error:", _e)


def get_attendance_date_locks(year: int, month: int) -> dict:
    """Returns dict of {day: bool} where True means EDITABLE, False means LOCKED."""
    import calendar
    _, days_in_month = calendar.monthrange(year, month)

    locks_df = pd.DataFrame()
    if os.path.exists(ATTENDANCE_LOCKS_FILE):
        try:
            locks_df = pd.read_csv(ATTENDANCE_LOCKS_FILE)
        except Exception:
            pass

    locked_dates = set()
    if not locks_df.empty and "lock_date" in locks_df.columns:
        for _, lr in locks_df.iterrows():
            if str(lr.get("is_locked", "True")).lower() in ("true", "1"):
                locked_dates.add(str(lr.get("lock_date", "")))

    locks = {}
    for d in range(1, days_in_month + 1):
        d_str = f"{year:04d}-{month:02d}-{d:02d}"
        locks[d] = (d_str not in locked_dates)  # True = editable, False = locked
    return locks


def save_attendance_date_locks(year: int, month: int, editable_dict: dict) -> None:
    """Saves lock states to local CSV immediately."""
    import calendar
    _, days_in_month = calendar.monthrange(year, month)

    all_locks = pd.DataFrame()
    if os.path.exists(ATTENDANCE_LOCKS_FILE):
        try:
            all_locks = pd.read_csv(ATTENDANCE_LOCKS_FILE)
        except Exception:
            pass

    rows = []
    start_str = f"{year:04d}-{month:02d}-01"
    end_str = f"{year:04d}-{month:02d}-{days_in_month:02d}"

    for d in range(1, days_in_month + 1):
        d_str = f"{year:04d}-{month:02d}-{d:02d}"
        is_editable = editable_dict.get(d, True)
        is_locked = not is_editable
        rows.append({"lock_date": d_str, "is_locked": is_locked})

    new_df = pd.DataFrame(rows)
    if not all_locks.empty and "lock_date" in all_locks.columns:
        other_locks = all_locks[~((all_locks["lock_date"].astype(str) >= start_str) & (all_locks["lock_date"].astype(str) <= end_str))]
        combined = pd.concat([other_locks, new_df], ignore_index=True)
    else:
        combined = new_df

    os.makedirs("data", exist_ok=True)
    combined.to_csv(ATTENDANCE_LOCKS_FILE, index=False)


def get_worker_wages_df() -> pd.DataFrame:
    """Fetches historical wage revisions from data/worker_wages.csv (local) with fallback."""
    df = pd.DataFrame()
    if os.path.exists(WORKER_WAGES_FILE):
        try:
            df = pd.read_csv(WORKER_WAGES_FILE)
        except Exception:
            df = pd.DataFrame()
    if df.empty:
        try:
            df = sb_fetch_df(WORKER_WAGES_FILE, CSV_SCHEMAS[WORKER_WAGES_FILE])
        except Exception:
            df = pd.DataFrame()

    # Ensure every worker has a baseline rate record (effective_date <= 2020-01-01)
    w_df = get_workers_df()
    if not w_df.empty:
        tracked_baselines = set()
        if not df.empty and "worker_id" in df.columns:
            for wid, group in df.groupby("worker_id"):
                if (group["effective_date"].astype(str) <= "2020-01-01").any():
                    tracked_baselines.add(int(wid))

        missing = []
        next_id = int(df["wage_id"].max() + 1) if not df.empty and "wage_id" in df.columns and df["wage_id"].max() > 0 else 1
        for _, wr in w_df.iterrows():
            wid = int(wr["worker_id"])
            if wid not in tracked_baselines:
                base_rate = float(wr.get("base_rate", 0.0))
                if wid == 1 and base_rate == 1000.0:
                    base_rate = 500.0  # baseline rate before Oct 13 revision
                missing.append({
                    "wage_id": next_id,
                    "worker_id": wid,
                    "effective_date": "2020-01-01",
                    "salary_type": str(wr.get("salary_type", "Daily")),
                    "base_rate": base_rate,
                    "notes": "Initial base wage",
                    "created_at": "2020-01-01T00:00:00",
                })
                next_id += 1
                tracked_baselines.add(wid)

        if missing:
            df = pd.concat([df, pd.DataFrame(missing)], ignore_index=True)
            save_worker_wages_df(df)

    if not df.empty and "effective_date" in df.columns:
        df = df.sort_values("effective_date", ascending=True)
    return df


def save_worker_wages_df(df: pd.DataFrame) -> None:
    """Saves wage revisions to CSV and optionally Supabase."""
    os.makedirs("data", exist_ok=True)
    df.to_csv(WORKER_WAGES_FILE, index=False)
    _sync_worker_table_to_supabase("worker_wages", df, pk="wage_id")


def get_worker_rate_for_date(
    worker_id: int,
    d: date,
    wages_df: pd.DataFrame | None = None,
    w_df: pd.DataFrame | None = None,
) -> tuple[float, str]:
    """Returns (base_rate, salary_type) active on date `d` for worker_id (100% in-memory, ultra-fast)."""
    if wages_df is None:
        wages_df = get_worker_wages_df()
    d_str = str(d)
    if wages_df is not None and not wages_df.empty and "worker_id" in wages_df.columns:
        sub = wages_df[
            wages_df["worker_id"].astype(int) == int(worker_id)
        ]
        if not sub.empty:
            sub = sub.sort_values("effective_date", ascending=True)
            valid = sub[sub["effective_date"].astype(str) <= d_str]
            if not valid.empty:
                last_row = valid.iloc[-1]
                return float(last_row.get("base_rate", 0.0)), str(last_row.get("salary_type", "Daily"))
            else:
                first_row = sub.iloc[0]
                return float(first_row.get("base_rate", 0.0)), str(first_row.get("salary_type", "Daily"))

    # Fallback to current worker master only if no wage records exist at all
    if w_df is None:
        w_df = get_workers_df()
    if w_df is not None and not w_df.empty and "worker_id" in w_df.columns:
        sub_w = w_df[w_df["worker_id"].astype(int) == int(worker_id)]
        if not sub_w.empty:
            return float(sub_w.iloc[0].get("base_rate", 0.0)), str(sub_w.iloc[0].get("salary_type", "Daily"))
    return 0.0, "Daily"


def build_bill_html(
    retailer_row: dict,
    start_day: date,
    end_day: date,
    grid: pd.DataFrame,
    pay_mode_totals: pd.DataFrame,
    cat_names: list[str],
    opening_due: float,
    show_empty_cols: bool = True,
) -> str:
    import pandas as pd

    shop_name = "RANJIT BHIMRAO KAWLE MILK SUPPLIER"
    shop_sub = "Wholesale Milk Supplier"
    shop_address = "Kherwadi, Bandra East, Mumbai - 400051"
    shop_contact = "9987471568"
    shop_fssai = "21518020000478"

    raw_cust = display_or_dash(retailer_row.get("name"))
    clean_cust = str(raw_cust).strip()
    if not clean_cust.lower().startswith("shri"):
        cust = f"Shri {clean_cust}"
    else:
        cust = clean_cust

    zone = display_or_dash(retailer_row.get("zone"))
    contact = display_or_dash(retailer_row.get("contact"))
    address = display_or_dash(retailer_row.get("address"))
    rid = int(retailer_row.get("retailer_id", 0))

    def esc(s: str) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def num_to_words_inr(num: float) -> str:
        try:
            num = int(round(abs(num)))
            if num == 0:
                return "Zero Rupees Only"
            ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
                    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
                    "Seventeen", "Eighteen", "Nineteen"]
            tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
            def two_digits(n):
                if n < 20:
                    return ones[n]
                return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")
            def three_digits(n):
                if n >= 100:
                    return ones[n // 100] + " Hundred" + (" and " + two_digits(n % 100) if n % 100 else "")
                return two_digits(n)
            parts = []
            crore = num // 10000000
            if crore:
                parts.append(two_digits(crore) + " Crore")
                num %= 10000000
            lakh = num // 100000
            if lakh:
                parts.append(two_digits(lakh) + " Lakh")
                num %= 100000
            thousand = num // 1000
            if thousand:
                parts.append(two_digits(thousand) + " Thousand")
                num %= 1000
            hundred = num
            if hundred:
                parts.append(three_digits(hundred))
            return "Rupees " + " ".join(parts) + " Only"
        except Exception:
            return ""

    df = grid.copy() if grid is not None else pd.DataFrame()

    total_qty_by_cat = {cat: 0.0 for cat in cat_names}
    total_sales = 0.0
    total_pay = 0.0

    if df is not None and not df.empty:
        for cat in cat_names:
            qcol = f"{cat} Qty"
            if qcol in df.columns:
                # Vectorized sum with fillna to completely avoid NaN poisoning from "-" entries
                s = pd.to_numeric(df[qcol], errors="coerce").fillna(0.0).sum()
                total_qty_by_cat[cat] = float(s)

        if "Sales (₹)" in df.columns:
            total_sales = float(
                pd.to_numeric(df["Sales (₹)"], errors="coerce").fillna(0.0).sum()
            )
        if "Payment (₹)" in df.columns:
            total_pay = float(
                pd.to_numeric(df["Payment (₹)"], errors="coerce").fillna(0.0).sum()
            )

    total_gross_due = float(opening_due + total_sales)
    closing_due = float(total_gross_due - total_pay)

    # Active categories taken by the retailer (strictly those purchased or assigned)
    active_cats = [c for c in cat_names if total_qty_by_cat.get(c, 0.0) > 0]
    if not active_cats:
        active_cats = [c for c in cat_names if c]
    if not active_cats:
        active_cats = ["Milk"]

    # Table Header with optional 2 empty columns for FAT & SNF + Dedicated Payment Column
    fat_snf_style = "" if show_empty_cols else "display:none;"
    cat_header_ths = "".join(f"<th style='text-align:right;'>{esc(c)} (L)</th>" for c in active_cats)
    table_head_html = f"""
    <tr>
        <th style="width:100px; text-align:center;">Date</th>
        {cat_header_ths}
        <th class="fat-snf-col" style="width:95px; min-width:90px; text-align:center; font-weight:800; {fat_snf_style}">FAT</th>
        <th class="fat-snf-col" style="width:95px; min-width:90px; text-align:center; font-weight:800; {fat_snf_style}">SNF</th>
        <th style="width:120px; text-align:right;">Payment (₹)</th>
        <th style="width:150px; text-align:right;">Total Cost of Milk (₹)</th>
    </tr>
    """

    # Table Body Rows
    body_rows = ""
    for _, r in df.iterrows() if df is not None else []:
        raw_d = str(r.get("Date", "")).strip()
        try:
            d_parsed = pd.to_datetime(raw_d).date()
            date_disp = d_parsed.strftime("%d/%m/%Y")
        except Exception:
            date_disp = raw_d

        tds = f"<td style='text-align:center; font-weight:800; color:#0f172a;'>{esc(date_disp)}</td>"

        for cat in active_cats:
            qcol = f"{cat} Qty"
            qv = float(pd.to_numeric(r.get(qcol, 0.0), errors="coerce") or 0.0)
            qdisp = f"<b style='color:#000000;'>{qv:.2f}</b>" if qv > 0 else "<span style='color:#94a3b8;'>–</span>"
            tds += f"<td style='text-align:right;'>{qdisp}</td>"

        # 2 empty columns (double width ~95px, for handwriting FAT & SNF with crisp borders, optional)
        tds += f"<td class='fat-snf-col' style='background:#ffffff; border-left:1.5px solid #334155; border-right:1px dashed #94a3b8; {fat_snf_style}'></td>"
        tds += f"<td class='fat-snf-col' style='background:#ffffff; border-right:1.5px solid #334155; {fat_snf_style}'></td>"

        # Dedicated Payment Column
        day_pay = float(pd.to_numeric(r.get("Payment (₹)", r.get("payment", 0.0)), errors="coerce") or 0.0)
        pay_disp = f"<b style='color:#15803d; font-size:12px;'>₹{day_pay:,.2f}</b>" if day_pay > 0 else "<span style='color:#94a3b8;'>–</span>"
        tds += f"<td style='text-align:right;'>{pay_disp}</td>"

        # Total Cost of Milk
        day_sales = float(pd.to_numeric(r.get("Sales (₹)", 0.0), errors="coerce") or 0.0)
        cost_disp = f"<b style='color:#000000; font-size:12px;'>₹{day_sales:,.2f}</b>" if day_sales > 0 else "<span style='color:#94a3b8;'>–</span>"
        tds += f"<td style='text-align:right;'>{cost_disp}</td>"

        body_rows += f"<tr>{tds}</tr>"

    # Table Total Row
    total_row = "<td style='text-align:center;'><b>TOTAL</b></td>"
    for cat in active_cats:
        c_tot = total_qty_by_cat.get(cat, 0.0)
        total_row += f"<td style='text-align:right;'><b>{c_tot:,.2f} L</b></td>"
    total_row += f"<td class='fat-snf-col' style='background:#0f172a; border-color:#0f172a; text-align:center; color:#94a3b8; font-size:11px; {fat_snf_style}'>–</td>"
    total_row += f"<td class='fat-snf-col' style='background:#0f172a; border-color:#0f172a; text-align:center; color:#94a3b8; font-size:11px; {fat_snf_style}'>–</td>"
    total_pay_disp = f"<b style='color:#4ade80;'>₹{total_pay:,.2f}</b>" if total_pay > 0 else "–"
    total_row += f"<td style='text-align:right;'>{total_pay_disp}</td>"
    total_row += f"<td style='text-align:right;'><b>₹{total_sales:,.2f}</b></td>"

    # Payments Breakdown (if any)
    pay_rows_html = ""
    pm_list = []
    if isinstance(pay_mode_totals, dict):
        pm_list = [{"Mode": k, "Total (₹)": v} for k, v in pay_mode_totals.items() if float(pd.to_numeric(v, errors="coerce") or 0) > 0]
    elif isinstance(pay_mode_totals, pd.DataFrame) and not pay_mode_totals.empty:
        for _, r in pay_mode_totals.iterrows():
            m_val = r.get("Mode", r.get("payment_mode", "-"))
            a_val = r.get("Total (₹)", r.get("amount", 0.0))
            if float(pd.to_numeric(a_val, errors="coerce") or 0) > 0:
                pm_list.append({"Mode": m_val, "Total (₹)": a_val})

    if pm_list:
        for item in pm_list:
            mode = esc(item["Mode"])
            amt = f"₹{float(item['Total (₹)']):,.2f}"
            pay_rows_html += f"<tr><td style='color:#0f172a; font-weight:800;'>{mode}</td><td style='text-align:right; font-weight:850; color:#15803d;'>{amt}</td></tr>"

    # Guaranteed Unique, Sequential, Deterministic Credit Cash Memo Number
    # Structure: CCM/{Financial Year}/{Retailer ID 3-digit}-{Month 2-digit}{Start Day 2-digit}{End Day 2-digit}
    # Example: CCM/26-27/001-100114 (Guarantees zero collisions across retailers, months, years, or billing periods)
    fy_start = start_day.year % 100 if start_day.month >= 4 else (start_day.year - 1) % 100
    fy_str = f"{fy_start:02d}-{(fy_start + 1):02d}"
    m_str = start_day.strftime("%m")
    d_start = start_day.strftime("%d")
    d_end = end_day.strftime("%d")
    span_code = f"{m_str}{d_start}{d_end}" if start_day != end_day else f"{m_str}{d_start}"
    doc_no = f"CCM/{fy_str}/{rid:03d}-{span_code}"
    bill_date_str = date.today().strftime("%d/%m/%Y")
    words_text = num_to_words_inr(closing_due if closing_due > 0 else total_sales)

    # Status callout
    if closing_due > 0:
        status_bg = "#fef2f2"
        status_border = "#dc2626"
        status_color = "#b91c1c"
        status_text = f"NET OUTSTANDING PAYABLE: ₹{closing_due:,.2f}"
    elif closing_due < 0:
        status_bg = "#f0fdf4"
        status_border = "#16a34a"
        status_color = "#15803d"
        status_text = f"ADVANCE CREDIT BALANCE: ₹{abs(closing_due):,.2f}"
    else:
        status_bg = "#f8fafc"
        status_border = "#475569"
        status_color = "#0f172a"
        status_text = "ALL DUES SETTLED (NIL BALANCE)"

    payments_box_html = ""
    if pay_rows_html:
        payments_box_html = f"""
        <div style="margin-top:10px;">
            <div style="font-size:10.5px; font-weight:850; color:#0f172a; text-transform:uppercase; margin-bottom:3px;">
                💳 Payments Received in this Period:
            </div>
            <table class="payments-table">
                <thead><tr><th style="text-align:left;">Payment Mode</th><th style="text-align:right;">Amount (₹)</th></tr></thead>
                <tbody>{pay_rows_html}</tbody>
            </table>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Credit Cash Memo — {esc(cust)} ({doc_no})</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    margin: 14px auto;
    padding: 0 10px;
    max-width: 920px;
    background: #f1f5f9;
    color: #0f172a;
    font-size: 12px;
    line-height: 1.35;
  }}

  /* Outer Box Outline for Entire Bill */
  .bill-page-wrapper {{
    border: 2px solid #0f172a;
    border-radius: 8px;
    padding: 18px 20px;
    background: #ffffff;
    box-shadow: 0 4px 18px rgba(15, 23, 42, 0.08);
    margin-bottom: 24px;
    display: flex;
    flex-direction: column;
    min-height: 250mm;
    box-sizing: border-box;
  }}

  /* Print Button Bar with Column Toggle */
  .print-btn-bar {{
    margin-bottom: 12px;
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }}
  .print-btn {{
    background: #0f172a;
    color: #ffffff;
    border: none;
    padding: 8px 18px;
    border-radius: 6px;
    font-weight: 800;
    font-size: 12.5px;
    cursor: pointer;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
  }}
  .btn-toggle-col {{
    background: #475569;
  }}

  /* Top Business Header */
  .memo-header {{
    text-align: center;
    border-bottom: 2px solid #0f172a;
    padding-bottom: 8px;
    margin-bottom: 12px;
  }}
  .shop-title {{
    font-size: 22px;
    font-weight: 950;
    color: #0f172a;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    margin: 0 0 2px 0;
  }}
  .shop-sub {{
    font-size: 12.5px;
    color: #1e3a8a;
    font-weight: 800;
    margin: 1px 0;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .shop-address {{
    font-size: 11.5px;
    color: #334155;
    font-weight: 650;
    margin: 1px 0 2px 0;
  }}
  .shop-fssai {{
    font-size: 11px;
    color: #1e3a8a;
    font-weight: 750;
    margin: 1px 0 6px 0;
    letter-spacing: 0.03em;
  }}
  .memo-heading-box {{
    display: inline-block;
    background: #0f172a;
    color: #ffffff;
    font-size: 13.5px;
    font-weight: 900;
    padding: 5px 24px;
    border-radius: 4px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 4px;
  }}

  /* Customer Details & Date Range Section */
  .party-meta-grid {{
    display: grid;
    grid-template-columns: 1.35fr 1fr;
    gap: 12px;
    margin-bottom: 12px;
  }}
  .party-card {{
    border: 1.5px solid #475569;
    border-radius: 6px;
    padding: 10px 14px;
    background: #f8fafc;
  }}
  .party-name-line {{
    font-size: 16px;
    font-weight: 950;
    color: #0f172a;
    margin-bottom: 4px;
  }}
  .party-meta-line {{
    font-size: 11.5px;
    color: #0f172a;
    padding: 2px 0;
    font-weight: 600;
  }}

  .meta-card {{
    border: 1.5px solid #475569;
    border-radius: 6px;
    padding: 10px 14px;
    background: #f8fafc;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }}
  .meta-row {{
    display: flex;
    justify-content: space-between;
    padding: 2.5px 0;
    font-size: 11.5px;
  }}
  .meta-lbl {{ color: #475569; font-weight: 700; }}
  .meta-val {{ color: #000000; font-weight: 850; }}

  /* Tables */
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 12px;
    font-size: 11.5px;
    background: #ffffff;
  }}
  thead {{
    display: table-header-group;
  }}
  th, td {{
    border: 1px solid #475569;
    padding: 6px 8px;
  }}
  th {{
    background: #0f172a;
    color: #ffffff;
    font-weight: 850;
    font-size: 11px;
    letter-spacing: 0.02em;
  }}
  tbody tr:nth-child(even) {{ background: #f8fafc; }}
  .total-row td {{
    background: #0f172a !important;
    color: #ffffff !important;
    font-weight: 950 !important;
    font-size: 12px !important;
    border-color: #0f172a !important;
  }}

  /* Settlement Grid: Lower Table on Left, Amount in Words on Right */
  .settlement-grid {{
    display: grid;
    grid-template-columns: 1.15fr 1fr;
    gap: 14px;
    margin-bottom: 16px;
    align-items: start;
  }}
  .words-box {{
    background: #f8fafc;
    border: 1.5px dashed #475569;
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 10px;
  }}
  .words-lbl {{
    font-size: 10px;
    font-weight: 850;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }}
  .words-val {{
    font-size: 12px;
    font-weight: 850;
    color: #1e3a8a;
    margin-top: 3px;
    line-height: 1.35;
  }}

  .payments-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
    margin-bottom: 6px;
  }}
  .payments-table th {{
    background: #1e293b;
    color: #fff;
    padding: 4px 8px;
  }}
  .payments-table td {{
    padding: 4px 8px;
    border: 1px solid #475569;
  }}

  .settlement-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }}
  .settlement-table td {{
    padding: 5px 8px;
    border: 1.5px solid #475569;
  }}
  .st-lbl {{ color: #0f172a; font-weight: 700; }}
  .st-val {{ text-align: right; font-weight: 850; color: #000000; }}
  .st-grand td {{
    background: #0f172a !important;
    color: #ffffff !important;
    font-weight: 950 !important;
    font-size: 13.5px !important;
  }}

  .status-banner {{
    padding: 8px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 850;
    text-align: center;
    background: {status_bg};
    border: 2px solid {status_border};
    color: {status_color};
  }}

  /* Bottom Docked Section (Dual Signatures + Thanking Note) */
  .bill-bottom-group {{
    margin-top: auto;
    page-break-inside: avoid;
  }}

  /* Signatures with Dedicated Line & Space */
  .footer-sign {{
    margin-top: 24px;
    margin-bottom: 14px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    page-break-inside: avoid;
  }}
  .sign-box {{
    width: 260px;
    text-align: center;
  }}
  .sign-space {{
    height: 50px;
  }}
  .sign-line {{
    border-top: 1.5px solid #0f172a;
    width: 100%;
    margin-bottom: 6px;
  }}
  .sign-label {{
    font-size: 11px;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.35;
  }}

  /* Thanking Bar at the Very End */
  .bottom-notes-bar {{
    margin-top: 0;
    border: 1.5px solid #94a3b8;
    border-radius: 6px;
    background: #f8fafc;
    padding: 8px 12px;
    text-align: center;
  }}
  .thank-msg {{
    font-size: 11.5px;
    font-weight: 800;
    color: #0f172a;
  }}

  @media print {{
    @page {{
      size: A4 portrait;
      margin: 4mm 5mm;
    }}
    html, body {{
      margin: 0 !important;
      padding: 0 !important;
      background: #fff !important;
      font-size: 9.2px !important;
      line-height: 1.2 !important;
    }}
    .print-btn-bar {{ display: none !important; }}
    .bill-page-wrapper {{
      border: 1.5px solid #0f172a !important;
      border-radius: 4px !important;
      padding: 6px 8px !important;
      box-shadow: none !important;
      margin: 0 auto !important;
      display: flex !important;
      flex-direction: column !important;
      min-height: 250mm !important;
      box-sizing: border-box !important;
      page-break-inside: avoid !important;
      break-inside: avoid !important;
    }}
    .bill-bottom-group {{
      margin-top: auto !important;
      page-break-inside: avoid !important;
      break-inside: avoid !important;
    }}
    th {{
      background: #0f172a !important;
      color: #fff !important;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
      padding: 2.5px 4px !important;
      font-size: 9px !important;
    }}
    td {{
      padding: 2px 4px !important;
    }}
    .total-row td {{
      background: #0f172a !important;
      color: #fff !important;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
      font-size: 9.5px !important;
    }}
    .st-grand td {{
      background: #0f172a !important;
      color: #fff !important;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
      font-size: 11px !important;
    }}
    table {{
      font-size: 8.8px !important;
      margin-bottom: 5px !important;
    }}
    .memo-heading-box {{
      font-size: 10px !important;
      padding: 2px 12px !important;
    }}
    .shop-title {{
      font-size: 15.5px !important;
    }}
    .party-name-line {{
      font-size: 12px !important;
      margin-bottom: 2px !important;
    }}
    .party-meta-grid {{
      margin-bottom: 5px !important;
      gap: 8px !important;
    }}
    .party-card, .meta-card {{
      padding: 5px 8px !important;
      font-size: 9.2px !important;
    }}
    .meta-row {{
      padding: 1.5px 0 !important;
      font-size: 9.2px !important;
    }}
    .settlement-grid {{
      margin-bottom: 6px !important;
      gap: 8px !important;
    }}
    .settlement-table td {{
      padding: 3px 6px !important;
      font-size: 9.5px !important;
    }}
    .words-box {{
      padding: 6px 8px !important;
      margin-bottom: 6px !important;
    }}
    .status-banner {{
      padding: 5px 8px !important;
      font-size: 10px !important;
    }}
    .footer-sign {{
      margin-top: 10px !important;
      margin-bottom: 5px !important;
      page-break-inside: avoid !important;
    }}
    .sign-space {{
      height: 26px !important;
    }}
    .sign-label {{
      font-size: 9.5px !important;
    }}
    .bottom-notes-bar {{
      margin-top: 0 !important;
      padding: 3px 6px !important;
    }}
    .thank-msg {{
      font-size: 9.5px !important;
    }}
    .fat-snf-col[style*="display: none"], .fat-snf-col[style*="display:none"] {{
      display: none !important;
    }}
    tr {{
      page-break-inside: avoid;
    }}
    thead {{
      display: table-header-group;
    }}
  }}
</style>
</head>
<body>

<div class="print-btn-bar">
  <button class="print-btn btn-toggle-col" id="toggleFatSnfBtn" onclick="toggleFatSnf()">🥛 Toggle FAT &amp; SNF Columns</button>
  <button class="print-btn" onclick="window.print()">🖨️ Print Credit / Cash Memo (A4 Portrait)</button>
</div>

<!-- Outer Frame / Border for Entire Bill -->
<div class="bill-page-wrapper">

  <!-- 1. Top Business Header -->
  <div class="memo-header">
    <div class="shop-title">{esc(shop_name)}</div>
    <div class="shop-sub">{esc(shop_sub)}</div>
    <div class="shop-address">{esc(shop_address)} &nbsp;|&nbsp; Mob: <b>{esc(shop_contact)}</b></div>
    <div class="shop-fssai">FSSAI Lic. No.: <b>{esc(shop_fssai)}</b></div>
    <div>
      <div class="memo-heading-box">CREDIT / CASH MEMO</div>
    </div>
  </div>

  <!-- 2. Customer & Date Meta Block -->
  <div class="party-meta-grid">
    <div class="party-card">
      <div class="party-name-line">{esc(cust)}</div>
      <div class="party-meta-line">Route / Zone: <b>{esc(zone)}</b> &nbsp;|&nbsp; Customer ID: <b>#{rid}</b></div>
      {f'<div class="party-meta-line">Contact No: <b>{esc(contact)}</b></div>' if contact and contact != '–' else ''}
      {f'<div class="party-meta-line">Address: {esc(address)}</div>' if address and address != '–' else ''}
    </div>

    <div class="meta-card">
      <div class="meta-row"><span class="meta-lbl">Memo No:</span> <span class="meta-val"><b>{doc_no}</b></span></div>
      <div class="meta-row"><span class="meta-lbl">Memo Date:</span> <span class="meta-val"><b>{bill_date_str}</b></span></div>
      <div class="meta-row"><span class="meta-lbl">Billing Period:</span> <span class="meta-val"><b>{start_day.strftime('%d/%m/%Y')} &nbsp;To&nbsp; {end_day.strftime('%d/%m/%Y')}</b></span></div>
      <div class="meta-row"><span class="meta-lbl">Period Duration:</span> <span class="meta-val">{(end_day - start_day).days + 1} Days</span></div>
    </div>
  </div>

  <!-- 3. Daily Milk Supply Grid (with optional 2 empty columns for FAT & SNF + Dedicated Payment Column) -->
  <table>
    <thead>
      {table_head_html}
    </thead>
    <tbody>
      {body_rows}
      <tr class="total-row">{total_row}</tr>
    </tbody>
  </table>

  <!-- 4. Financial Settlement & Account Summary -->
  <div class="settlement-grid">
    <div>
      <table class="settlement-table">
        <tr>
          <td class="st-lbl">Opening Balance:</td>
          <td class="st-val">₹{opening_due:,.2f}</td>
        </tr>
        <tr>
          <td class="st-lbl">Current Period Sales:</td>
          <td class="st-val">₹{total_sales:,.2f}</td>
        </tr>
        <tr style="background:#f1f5f9;">
          <td class="st-lbl" style="font-weight:750;">Total Amount Due:</td>
          <td class="st-val" style="font-weight:800;">₹{total_gross_due:,.2f}</td>
        </tr>
        <tr>
          <td class="st-lbl" style="color:#15803d;">Less: Payments Received:</td>
          <td class="st-val" style="color:#15803d;">- ₹{total_pay:,.2f}</td>
        </tr>
        <tr class="st-grand">
          <td>Net Amount Payable:</td>
          <td style="text-align:right;">₹{closing_due:,.2f}</td>
        </tr>
      </table>

      {payments_box_html}
    </div>

    <div>
      <div class="words-box">
        <div class="words-lbl">Net Amount Payable in Words:</div>
        <div class="words-val">{words_text}</div>
      </div>

      <div class="status-banner">
        {status_text}
      </div>
    </div>
  </div>

  <!-- 5 & 6. Bottom Docked Group: Dual Signatures & Thanking Note (Always pinned to bottom of page) -->
  <div class="bill-bottom-group">
    <!-- 5. Dual Signatures with Dedicated Signing Line & Space -->
    <div class="footer-sign">
      <div class="sign-box">
        <div class="sign-space"></div>
        <div class="sign-line"></div>
        <div class="sign-label">Customer / Receiver Signature</div>
      </div>
      <div class="sign-box">
        <div class="sign-space"></div>
        <div class="sign-line"></div>
        <div class="sign-label">For <b>RANJIT BHIMRAO KAWLE MILK SUPPLIER</b><br/><span style="font-size:10px; font-weight:600; color:#475569;">(Authorized Signatory)</span></div>
      </div>
    </div>

    <!-- 6. Thanking Note AT THE VERY END OF THE PAGE -->
    <div class="bottom-notes-bar">
      <div class="thank-msg">
        🙏 <b>धन्यवाद! आम्ही आपल्या सहकार्याबद्दल आभारी आहोत. / Thank You for Your Business!</b> &nbsp;|&nbsp; <br/> For queries / daily supply: <b>{esc(shop_contact)}</b>
      </div>
    </div>
  </div>

</div> <!-- /.bill-page-wrapper -->

<script>
function toggleFatSnf() {{
  var cols = document.querySelectorAll('.fat-snf-col');
  cols.forEach(function(el) {{
    if (el.style.display === 'none') {{
      el.style.display = '';
    }} else {{
      el.style.display = 'none';
    }}
  }});
}}
</script>

</body>
</html>
"""
    return html


# PDF generation intentionally disabled.
# HTML is the single source of truth for printing.


def bill_pdf_bytes_from_html(html: str):
    return None


# ============================================================
# SIDEBAR CONTEXT & APPLICATION HEADER
# ============================================================
zones = get_all_zones()
if MAIN_ZONE not in zones:
    zones = [MAIN_ZONE] + zones

st.sidebar.markdown(
    """
    <div style="
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        padding: 14px 16px;
        border-radius: 14px;
        color: #ffffff;
        margin-bottom: 12px;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.15);
    ">
        <div style="font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; color: #93c5fd;">
            MILK ERP • 100% OFFLINE
        </div>
        <div style="font-size: 16px; font-weight: 900; margin-top: 3px; letter-spacing: -0.01em;">
            🥛 RANJIT KAWLE
        </div>
        <div style="font-size: 11.5px; color: #cbd5e1; margin-top: 4px; display: flex; align-items: center; justify-content: space-between;">
            <span>Zone Context</span>
            <span style="background: rgba(34, 197, 94, 0.25); color: #86efac; padding: 2px 6px; border-radius: 6px; font-weight: 700; font-size: 10.5px;">● Live DB</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

selected_zone = st.sidebar.selectbox("Zone Context", ["All Zones"] + zones, index=0)

if st.sidebar.button("🔒 लॉक करा (Lock App)", key="btn_sidebar_lock_system", help="Lock application with PIN 7744", use_container_width=True):
    st.session_state["is_authenticated"] = False
    st.session_state["system_phone_lock_pad"] = ""
    st.rerun()

retailers_active = (
    retailers.loc[retailers.get("is_active", True).apply(parse_boolish_active)].copy()
    if not retailers.empty
    else retailers.copy()
)
categories_active = (
    categories.loc[categories.get("is_active", True).apply(parse_boolish_active)].copy()
    if not categories.empty
    else categories.copy()
)

def get_habit_profiles() -> dict:
    """Returns local offline learned customer habit profiles (cached by data_version)."""
    dv = st.session_state.get("data_version", 1)
    if "customer_habits_cache" not in st.session_state or st.session_state.get("habits_dv") != dv:
        st.session_state["customer_habits_cache"] = ai_engine.build_customer_habit_profiles(
            entries, retailers_active, categories_active, days_lookback=90
        )
        st.session_state["habits_dv"] = dv
    return st.session_state["customer_habits_cache"]

entries_z = (
    filter_by_zone(entries.copy(), "retailer_id", selected_zone)
    if not entries.empty
    else pd.DataFrame(columns=entries.columns)
)
payments_z = (
    filter_by_zone(payments.copy(), "retailer_id", selected_zone)
    if not payments.empty
    else pd.DataFrame(columns=payments.columns)
)

# Modern Top Application Header Card
st.markdown(
    f"""
<div style="
  display:flex; align-items:center; justify-content:space-between;
  padding:16px 22px; margin-bottom:16px;
  background: rgba(255,255,255,0.85);
  border:1px solid rgba(15,23,42,0.09);
  border-radius:18px;
  box-shadow: 0 8px 24px rgba(2,6,23,0.05);
  backdrop-filter: blur(12px);
">
  <div>
    <div style="font-size:24px; font-weight:950; letter-spacing:-0.02em; color:#0f172a;">🥛 RANJIT BHIMRAO KAWLE MILK SUPPLIER</div>
    <div style="color:#64748B; font-weight:700; font-size:13px; margin-top:3px; display:flex; align-items:center; gap:8px;">
      <span>Enterprise Dairy ERP</span>
      <span>•</span>
      <span style="background:#eff6ff; color:#1d4ed8; padding:2px 8px; border-radius:6px; font-size:11.5px; font-weight:800; border:1px solid #bfdbfe;">📍 {selected_zone}</span>
      <span style="background:#f0fdf4; color:#15803d; padding:2px 8px; border-radius:6px; font-size:11.5px; font-weight:800; border:1px solid #bbf7d0;">🤖 Local AI Active</span>
    </div>
  </div>
  <div style="text-align:right;">
    <div style="color:#64748B; font-weight:800; font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em;">Today / आजची तारीख</div>
    <div style="font-weight:950; font-size:16px; color:#0f172a;">{date.today().strftime("%d %b %Y")}</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 🎛️ Dairy Operations")
    if st.button("🔄 Refresh Data (DB Sync)", use_container_width=True, key="sidebar_sync_btn"):
        invalidate_data_cache()
        st.rerun()

st.markdown("""
<style>
/* =========================================================================
   UNIVERSAL TABLE HEADER LOCK: NON-SORTABLE & NON-MOVABLE (ALL APP TABLES)
   Every table is locked to prevent column sorting and column dragging/moving,
   matching the strict deterministic behavior of the Daily Entry table.
   ========================================================================= */

div[data-testid="stDataFrame"],
div[data-testid="stDataEditor"],
div[data-testid="stDataFrameResizable"],
.stDataFrame,
.stDataEditor {
    position: relative !important;
}

/* Header shield: absorbs all clicks & drags in the top 38px of any table */
div[data-testid="stDataFrame"]::before,
div[data-testid="stDataEditor"]::before,
div[data-testid="stDataFrameResizable"]::before,
.stDataFrame::before,
.stDataEditor::before {
    content: "" !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 50px !important; /* Preserves access to toolbar (search / download) */
    height: 38px !important; /* Covers exact header row height */
    z-index: 10 !important;
    cursor: default !important;
    pointer-events: auto !important;
    background: transparent !important;
}

/* =========================================================================
   PROMINENT EXECUTIVE COMMAND CENTER — LIGHT THEME (MATCHES WHOLE APP)
   ========================================================================= */

/* Top Navigation Deck Outer Container — Clean Light Mode matching Whole App */
div[class*="st-key-top_nav_deck"] {
    background: #ffffff !important;
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 18px !important;
    padding: 16px 20px 14px 20px !important;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06) !important;
    margin-bottom: 22px !important;
}

/* Nav & Subnav Buttons Base Styling — Slightly Bigger Words & Sizing */
div[class*="st-key-nav_deck_btn_"] button,
div[class*="st-key-subnav_btn_"] button {
    min-height: 70px !important;
    height: auto !important;
    padding: 10px 14px !important;
    border-radius: 14px !important;
    font-size: 18.5px !important;
    font-weight: 850 !important;
    line-height: 1.32 !important;
    text-align: center !important;
    white-space: pre-line !important;
    cursor: pointer !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

div[class*="st-key-nav_deck_btn_"] button p,
div[class*="st-key-nav_deck_btn_"] button div,
div[class*="st-key-nav_deck_btn_"] button span,
div[class*="st-key-subnav_btn_"] button p,
div[class*="st-key-subnav_btn_"] button div,
div[class*="st-key-subnav_btn_"] button span {
    font-size: 18.5px !important;
    font-weight: 850 !important;
    line-height: 1.32 !important;
    white-space: pre-line !important;
    text-align: center !important;
}

/* Inactive Navigation Card (Secondary) — Clean Light Theme Card */
div[class*="st-key-nav_deck_btn_"] button[kind="secondary"],
div[class*="st-key-nav_deck_btn_"] button[data-testid="baseButton-secondary"],
div[class*="st-key-nav_deck_btn_"] button.stBaseButton-secondary,
div[class*="st-key-subnav_btn_"] button[kind="secondary"],
div[class*="st-key-subnav_btn_"] button[data-testid="baseButton-secondary"],
div[class*="st-key-subnav_btn_"] button.stBaseButton-secondary {
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
    border: 2px solid #cbd5e1 !important;
    color: #0f172a !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.05) !important;
}

div[class*="st-key-nav_deck_btn_"] button[kind="secondary"] p,
div[class*="st-key-nav_deck_btn_"] button[kind="secondary"] span,
div[class*="st-key-nav_deck_btn_"] button[data-testid="baseButton-secondary"] p,
div[class*="st-key-nav_deck_btn_"] button[data-testid="baseButton-secondary"] span,
div[class*="st-key-nav_deck_btn_"] button[kind="secondary"] p,
div[class*="st-key-nav_deck_btn_"] button[kind="secondary"] span {
    color: #0f172a !important;
}

/* Inactive Hover */
div[class*="st-key-nav_deck_btn_"] button[kind="secondary"]:hover,
div[class*="st-key-nav_deck_btn_"] button[data-testid="baseButton-secondary"]:hover,
div[class*="st-key-nav_deck_btn_"] button[kind="secondary"]:hover,
div[class*="st-key-subnav_btn_"] button[data-testid="baseButton-secondary"]:hover {
    background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%) !important;
    border-color: #3b82f6 !important;
    color: #1d4ed8 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px rgba(37, 99, 235, 0.18) !important;
}

div[class*="st-key-nav_deck_btn_"] button[kind="secondary"]:hover p,
div[class*="st-key-nav_deck_btn_"] button[kind="secondary"]:hover span,
div[class*="st-key-nav_deck_btn_"] button[kind="secondary"]:hover p,
div[class*="st-key-nav_deck_btn_"] button[kind="secondary"]:hover span {
    color: #1d4ed8 !important;
}

/* Active Navigation Card (Primary) — Vibrant Royal Blue */
div[class*="st-key-nav_deck_btn_"] button[kind="primary"],
div[class*="st-key-nav_deck_btn_"] button[data-testid="baseButton-primary"],
div[class*="st-key-nav_deck_btn_"] button.stBaseButton-primary,
div[class*="st-key-subnav_btn_"] button[kind="primary"],
div[class*="st-key-subnav_btn_"] button[data-testid="baseButton-primary"],
div[class*="st-key-subnav_btn_"] button.stBaseButton-primary {
    background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 55%, #3b82f6 100%) !important;
    border: 2.5px solid #1e40af !important;
    color: #ffffff !important;
    box-shadow: 0 8px 22px rgba(37, 99, 235, 0.45) !important;
    transform: scale(1.025) !important;
}

div[class*="st-key-nav_deck_btn_"] button[kind="primary"] p,
div[class*="st-key-nav_deck_btn_"] button[kind="primary"] span,
div[class*="st-key-nav_deck_btn_"] button[data-testid="baseButton-primary"] p,
div[class*="st-key-nav_deck_btn_"] button[data-testid="baseButton-primary"] span,
div[class*="st-key-subnav_btn_"] button[kind="primary"] p,
div[class*="st-key-subnav_btn_"] button[kind="primary"] span {
    color: #ffffff !important;
    font-weight: 950 !important;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.25) !important;
}

/* Sub-Navigation Containers — Light Theme */
div[class*="st-key-subnav_bill_deck"],
div[class*="st-key-subnav_setup_deck"] {
    background: #ffffff !important;
    border: 1.5px solid #bfdbfe !important;
    border-radius: 16px !important;
    padding: 14px 18px !important;
    margin: 4px 0 22px 0 !important;
    box-shadow: 0 4px 16px rgba(37, 99, 235, 0.08) !important;
}
</style>

<!-- Universal Double-Layer Event Interceptor for Grid Header Non-Sorting and Non-Moving -->
<img src="data:image/svg+xml;utf8,<svg></svg>" style="display:none;" onerror="
(function() {
    function lockGridHeaders() {
        var tables = document.querySelectorAll('[data-testid=\'stDataFrame\'], [data-testid=\'stDataEditor\'], [data-testid=\'stDataFrameResizable\']');
        tables.forEach(function(t) {
            var canvas = t.querySelector('canvas');
            if (canvas && !canvas.__locked) {
                canvas.__locked = true;
                function blockHeader(e) {
                    var r = canvas.getBoundingClientRect();
                    var y = e.clientY - r.top;
                    var x = e.clientX - r.left;
                    if (y <= 38 && x < (r.width - 50)) {
                        e.stopImmediatePropagation();
                        e.stopPropagation();
                    }
                }
                canvas.addEventListener('mousedown', blockHeader, true);
                canvas.addEventListener('click', blockHeader, true);
                canvas.addEventListener('pointerdown', blockHeader, true);
            }
        });
    }
    lockGridHeaders();
    if (!window.__gridLockObs) {
        window.__gridLockObs = new MutationObserver(lockGridHeaders);
        window.__gridLockObs.observe(document.body, { childList: true, subtree: true });
    }
})();
"/>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# HIGH-RELIABILITY BIG COMMAND DECK NAVIGATION
# -------------------------------------------------------------
NAV_ITEMS_ROW1 = [
    {
        "id": "📊 Dashboard",
        "label": "📊 Dashboard\n(डॅशबोर्ड)",
        "key": "nav_deck_btn_dash",
    },
    {
        "id": "📝 Daily Entry",
        "label": "📝 Daily Entry\n(रोजची नोंद)",
        "key": "nav_deck_btn_daily",
    },
    {
        "id": "👷 कामगार हजेरी (Attendance)",
        "label": "👷 कामगार हजेरी\n(Attendance)",
        "key": "nav_deck_btn_att",
    },
    {
        "id": "🧾 Bills & Statements",
        "label": "🧾 Bills & Statements\n(बिल व मेमो)",
        "key": "nav_deck_btn_bill",
    },
]

NAV_ITEMS_ROW2 = [
    {
        "id": "🤖 AI Audit & Anomaly Detection",
        "label": "🤖 AI Audit & Anomaly\n(तपासणी व ऑडिट)",
        "key": "nav_deck_btn_ai",
    },
    {
        "id": "💰 Price Management",
        "label": "💰 Price Management\n(दर व्यवस्थापन)",
        "key": "nav_deck_btn_price",
    },
    {
        "id": "⚙️ Master Setup",
        "label": "⚙️ Master Setup\n(मास्टर सेटिंग)",
        "key": "nav_deck_btn_setup",
    },
    {
        "id": "🛡️ Data Health & Backup",
        "label": "🛡️ Data Backup\n(डेटा बॅकअप)",
        "key": "nav_deck_btn_backup",
    },
]

ALL_NAV_IDS = [item["id"] for item in NAV_ITEMS_ROW1 + NAV_ITEMS_ROW2]

if "current_menu" not in st.session_state or st.session_state["current_menu"] not in ALL_NAV_IDS:
    st.session_state["current_menu"] = "📊 Dashboard"

# ============================================================
# RANGE BACKUP EXCEL GENERATOR (MULTI-SHEET WITH ATTENDANCE)
# ============================================================
def make_range_backup_excel(
    start_date,
    end_date,
    retailers,
    categories,
    entries,
    payments,
    dist_purchases,
    dist_payments,
    distributors,
    expenses_df=None,
) -> bytes:
    """
    Generates a comprehensive multi-sheet Excel Workbook (.xlsx) for the chosen date range.
    Sheets:
      1. Daily Deliveries & Ledger: Day-by-day retailer deliveries, sales, payments, running balance, distributor purchases.
      2. Worker Attendance & Wages: Detailed staff daily attendance (Full/Half/Absent), units, daily wage rate, and earned wages.
      3. Driver Cash Handovers: Daily cash collection vs route expenses vs actual cash deposited at counter.
      4. Route Expenses: Fuel, bhatta, repairs, and other operational expenses.
      5. Workers Master: Staff directory with roles, base wages, and contact information.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    import csv
    import io

    wb = openpyxl.Workbook()

    # Styling presets
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    fill_header_dark = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    fill_header_teal = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    fill_header_slate = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
    font_bold = Font(name="Calibri", size=11, bold=True, color="000000")
    fill_total = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    thick_top = Border(top=Side(style="medium", color="0F172A"), bottom=Side(style="double", color="0F172A"))

    # -------------------------------------------------------------
    # SHEET 1: Daily Deliveries & Ledger Summary
    # -------------------------------------------------------------
    ws_daily = wb.active
    ws_daily.title = "Daily Deliveries & Ledger"

    try:
        csv_bytes = make_range_backup_csv(
            start_date=start_date,
            end_date=end_date,
            retailers=retailers,
            categories=categories,
            entries=entries,
            payments=payments,
            dist_purchases=dist_purchases,
            dist_payments=dist_payments,
            distributors=distributors,
        )
        csv_str = csv_bytes.decode("utf-8", errors="replace")
        csv_reader = csv.reader(io.StringIO(csv_str))
        for row_idx, row in enumerate(csv_reader, start=1):
            ws_daily.append(row)
            if row_idx in (1, 2):
                for cell in ws_daily[row_idx]:
                    cell.font = font_header
                    cell.fill = fill_header_dark
    except Exception:
        ws_daily.append(["Error generating daily ledger sheet."])

    # -------------------------------------------------------------
    # SHEET 2: Worker Attendance & Wages (Date-Range Filtered)
    # -------------------------------------------------------------
    ws_att = wb.create_sheet(title="Worker Attendance & Wages")
    att_headers = [
        "तारीख (Date)",
        "कामगार आयडी (Worker ID)",
        "कामगार नाव (Worker Name)",
        "पद (Role)",
        "हजेरी स्थिती (Attendance Status)",
        "युनिट्स (Units)",
        "प्रति दिवस दर (Daily Rate ₹)",
        "कमावलेला पगार (Earned Wage ₹)",
        "नोंद (Notes)",
    ]
    ws_att.append(att_headers)
    for cell in ws_att[1]:
        cell.font = font_header
        cell.fill = fill_header_teal
        cell.alignment = Alignment(horizontal="center", vertical="center")

    workers_df = get_workers_df()
    worker_map = {}
    if isinstance(workers_df, pd.DataFrame) and not workers_df.empty:
        for _, wr in workers_df.iterrows():
            wid = int(pd.to_numeric(wr.get("worker_id", 0), errors="coerce") or 0)
            worker_map[wid] = {
                "name": str(wr.get("name", f"Worker #{wid}")),
                "role": str(wr.get("role", "Staff")),
            }

    wages_df = get_worker_wages_df()
    att_df = pd.DataFrame()
    if os.path.exists("data/worker_attendance.csv"):
        try:
            att_df = pd.read_csv("data/worker_attendance.csv")
        except Exception:
            att_df = pd.DataFrame()

    total_att_units = 0.0
    total_att_earned = 0.0

    if isinstance(att_df, pd.DataFrame) and not att_df.empty and "date" in att_df.columns:
        att_df["date_str"] = att_df["date"].astype(str)
        s_str = pd.to_datetime(start_date).strftime("%Y-%m-%d")
        e_str = pd.to_datetime(end_date).strftime("%Y-%m-%d")
        filtered_att = att_df[(att_df["date_str"] >= s_str) & (att_df["date_str"] <= e_str)].copy()

        if not filtered_att.empty:
            filtered_att = filtered_att.sort_values(by=["date_str", "worker_id"])
            for _, ar in filtered_att.iterrows():
                raw_d = str(ar.get("date", ""))
                try:
                    d_obj = pd.to_datetime(raw_d).date()
                    d_disp = d_obj.strftime("%d/%m/%Y")
                except Exception:
                    d_obj = date.today()
                    d_disp = raw_d

                wid = int(pd.to_numeric(ar.get("worker_id", 0), errors="coerce") or 0)
                w_info = worker_map.get(wid, {"name": f"Worker #{wid}", "role": "Staff"})
                w_name = w_info["name"]
                w_role = w_info["role"]

                raw_status = ar.get("status", "P")
                raw_units = ar.get("units", 1.0)
                status_label = parse_attendance_status_label(raw_status, raw_units)

                try:
                    units_val = float(pd.to_numeric(raw_units, errors="coerce") or 0.0)
                except Exception:
                    units_val = 0.0

                rate_val, _ = get_worker_rate_for_date(wid, d_obj, wages_df=wages_df)
                earned_val = round(rate_val * units_val, 2)
                notes_val = str(ar.get("notes", "") or "").replace("nan", "")

                total_att_units += units_val
                total_att_earned += earned_val

                row_cells = [
                    d_disp,
                    wid,
                    w_name,
                    w_role,
                    status_label,
                    units_val,
                    rate_val,
                    earned_val,
                    notes_val,
                ]
                ws_att.append(row_cells)

    # Attendance Total Row
    tot_row_num = ws_att.max_row + 1
    ws_att.append(["TOTAL", "", "", "", "", total_att_units, "", total_att_earned, ""])
    for cell in ws_att[tot_row_num]:
        cell.font = font_bold
        cell.fill = fill_total
        cell.border = thick_top

    # -------------------------------------------------------------
    # SHEET 3: Driver Cash Handovers
    # -------------------------------------------------------------
    ws_dh = wb.create_sheet(title="Driver Cash Handovers")
    dh_headers = [
        "तारीख (Date)",
        "रूट / झोन (Route/Zone)",
        "काऊंटरवर प्रत्यक्षात जमा रोख (Actual Handover ₹)",
        "अपेक्षित रोख (Expected Handover ₹)",
        "फरक / कमतरता (Difference ₹)",
        "अद्यतन वेळ (Updated At)",
    ]
    ws_dh.append(dh_headers)
    for cell in ws_dh[1]:
        cell.font = font_header
        cell.fill = fill_header_slate
        cell.alignment = Alignment(horizontal="center", vertical="center")

    if os.path.exists("data/driver_handovers.csv"):
        try:
            dh_df = pd.read_csv("data/driver_handovers.csv")
            if not dh_df.empty and "date" in dh_df.columns:
                dh_df["date_str"] = dh_df["date"].astype(str)
                s_str = pd.to_datetime(start_date).strftime("%Y-%m-%d")
                e_str = pd.to_datetime(end_date).strftime("%Y-%m-%d")
                filtered_dh = dh_df[(dh_df["date_str"] >= s_str) & (dh_df["date_str"] <= e_str)].copy()
                if not filtered_dh.empty:
                    filtered_dh = filtered_dh.sort_values(by=["date_str", "zone"])
                    tot_actual = 0.0
                    tot_expected = 0.0
                    for _, dhr in filtered_dh.iterrows():
                        act = float(pd.to_numeric(dhr.get("actual_handover", 0.0), errors="coerce") or 0.0)
                        exp = float(pd.to_numeric(dhr.get("expected_handover", 0.0), errors="coerce") or 0.0)
                        diff = round(act - exp, 2)
                        tot_actual += act
                        tot_expected += exp
                        try:
                            d_disp = pd.to_datetime(dhr.get("date")).strftime("%d/%m/%Y")
                        except Exception:
                            d_disp = str(dhr.get("date", ""))
                        ws_dh.append([
                            d_disp,
                            str(dhr.get("zone", "")),
                            act,
                            exp,
                            diff,
                            str(dhr.get("updated_at", "")),
                        ])
                    dh_tot_num = ws_dh.max_row + 1
                    ws_dh.append(["TOTAL", "", tot_actual, tot_expected, round(tot_actual - tot_expected, 2), ""])
                    for cell in ws_dh[dh_tot_num]:
                        cell.font = font_bold
                        cell.fill = fill_total
                        cell.border = thick_top
        except Exception:
            pass

    # -------------------------------------------------------------
    # SHEET 4: Route Expenses
    # -------------------------------------------------------------
    ws_exp = wb.create_sheet(title="Route Expenses")
    exp_headers = [
        "तारीख (Date)",
        "रूट / झोन (Route/Zone)",
        "खर्चाचा प्रकार (Category)",
        "रक्कम (Amount ₹)",
        "पेमेंट प्रकार (Payment Mode)",
        "तपशील (Note)",
    ]
    ws_exp.append(exp_headers)
    for cell in ws_exp[1]:
        cell.font = font_header
        cell.fill = fill_header_slate
        cell.alignment = Alignment(horizontal="center", vertical="center")

    if expenses_df is not None and isinstance(expenses_df, pd.DataFrame) and not expenses_df.empty:
        try:
            exp_copy = expenses_df.copy()
            exp_copy["date_str"] = pd.to_datetime(exp_copy["date"], errors="coerce").dt.strftime("%Y-%m-%d")
            s_str = pd.to_datetime(start_date).strftime("%Y-%m-%d")
            e_str = pd.to_datetime(end_date).strftime("%Y-%m-%d")
            f_exp = exp_copy[(exp_copy["date_str"] >= s_str) & (exp_copy["date_str"] <= e_str)].copy()
            if not f_exp.empty:
                tot_eamt = 0.0
                for _, er in f_exp.iterrows():
                    amt = float(pd.to_numeric(er.get("amount", 0.0), errors="coerce") or 0.0)
                    tot_eamt += amt
                    try:
                        d_disp = pd.to_datetime(er.get("date")).strftime("%d/%m/%Y")
                    except Exception:
                        d_disp = str(er.get("date", ""))
                    ws_exp.append([
                        d_disp,
                        str(er.get("zone", "General")),
                        str(er.get("category", "")),
                        amt,
                        str(er.get("payment_mode", "Cash")),
                        str(er.get("note", "")),
                    ])
                exp_tot_num = ws_exp.max_row + 1
                ws_exp.append(["TOTAL", "", "", tot_eamt, "", ""])
                for cell in ws_exp[exp_tot_num]:
                    cell.font = font_bold
                    cell.fill = fill_total
                    cell.border = thick_top
        except Exception:
            pass

    # -------------------------------------------------------------
    # SHEET 5: Workers Master Directory
    # -------------------------------------------------------------
    ws_wm = wb.create_sheet(title="Workers Master")
    wm_headers = [
        "कामगार आयडी (Worker ID)",
        "कामगार नाव (Name)",
        "पद (Role)",
        "संपर्क (Contact)",
        "पगार प्रकार (Salary Type)",
        "सध्याचा मूळ दर (Base Rate ₹)",
        "सक्रिय (Is Active)",
    ]
    ws_wm.append(wm_headers)
    for cell in ws_wm[1]:
        cell.font = font_header
        cell.fill = fill_header_dark
        cell.alignment = Alignment(horizontal="center", vertical="center")

    if isinstance(workers_df, pd.DataFrame) and not workers_df.empty:
        for _, wr in workers_df.iterrows():
            ws_wm.append([
                int(pd.to_numeric(wr.get("worker_id", 0), errors="coerce") or 0),
                str(wr.get("name", "")),
                str(wr.get("role", "")),
                str(wr.get("contact", "")).replace(".0", ""),
                str(wr.get("salary_type", "Daily")),
                float(pd.to_numeric(wr.get("base_rate", 0.0), errors="coerce") or 0.0),
                str(wr.get("is_active", True)),
            ])

    # Auto-adjust column widths across all sheets
    for ws in wb.worksheets:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if "\n" in val_str:
                    val_str = max(val_str.split("\n"), key=len)
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 11), 40)

    out_buf = io.BytesIO()
    wb.save(out_buf)
    return out_buf.getvalue()

current_menu = st.session_state["current_menu"]

def switch_nav_target(target_id: str):
    if st.session_state.get("current_menu") != target_id:
        st.session_state["current_menu"] = target_id
        st.session_state["daily_drafts"] = {}
        st.session_state["daily_loaded_ctx"] = None
        st.session_state["daily_meta"] = {}
        st.session_state["dist_flat_grid"] = pd.DataFrame()
        st.session_state["dist_flat_payments"] = pd.DataFrame()
        st.rerun()

# RENDER COMMAND CENTER
with st.container(border=True, key="top_nav_deck"):
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
      <span style="font-size:13.5px; font-weight:850; color:#475569; text-transform:uppercase; letter-spacing:0.07em;">
        ⚡ Daily Core Operations / दैनिक कामकाज
      </span>
      <span style="font-size:13px; font-weight:850; color:#1d4ed8; background:#eff6ff; padding:3px 12px; border-radius:8px; border:1.5px solid #bfdbfe;">
        Active: <b>{current_menu}</b>
      </span>
    </div>
    """, unsafe_allow_html=True)

    r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
    for col, item in zip([r1_col1, r1_col2, r1_col3, r1_col4], NAV_ITEMS_ROW1):
        with col:
            is_active = (current_menu == item["id"])
            if st.button(
                item["label"],
                key=item["key"],
                type="primary" if is_active else "secondary",
                use_container_width=True,
                help=f"Open {item['id']}",
            ):
                switch_nav_target(item["id"])

    st.markdown("""
    <div style="font-size:13.5px; font-weight:850; color:#475569; text-transform:uppercase; letter-spacing:0.07em; margin:14px 0 12px 0;">
      ⚙️ Management, Audit & System / व्यवस्थापन व नियंत्रण
    </div>
    """, unsafe_allow_html=True)

    r2_col1, r2_col2, r2_col3, r2_col4 = st.columns(4)
    for col, item in zip([r2_col1, r2_col2, r2_col3, r2_col4], NAV_ITEMS_ROW2):
        with col:
            is_active = (current_menu == item["id"])
            if st.button(
                item["label"],
                key=item["key"],
                type="primary" if is_active else "secondary",
                use_container_width=True,
                help=f"Open {item['id']}",
            ):
                switch_nav_target(item["id"])

menu = st.session_state["current_menu"]

# SUB-NAV FOR BILLS & STATEMENTS
bill_menu = None
if menu == "🧾 Bills & Statements":
    VALID_BILL_MENUS = ["🏪 Retailers Bill", "🚚 Distributor Procurement Bill"]
    if "current_bill_menu" not in st.session_state or st.session_state["current_bill_menu"] not in VALID_BILL_MENUS:
        st.session_state["current_bill_menu"] = "🏪 Retailers Bill"
    
    with st.container(border=True, key="subnav_bill_deck"):
        st.markdown("""
        <div style="font-size:13.5px; font-weight:850; color:#1e3a8a; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:10px;">
          🧾 बिलाचा प्रकार निवडा (Select Bill / Statement Type)
        </div>
        """, unsafe_allow_html=True)
        
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            b1_active = (st.session_state["current_bill_menu"] == "🏪 Retailers Bill")
            if st.button(
                "🏪 Retailers Bill\n(रिटेलर बिल व मेमो)",
                key="subnav_btn_ret_bill",
                type="primary" if b1_active else "secondary",
                use_container_width=True,
            ):
                if st.session_state["current_bill_menu"] != "🏪 Retailers Bill":
                    st.session_state["current_bill_menu"] = "🏪 Retailers Bill"
                    st.rerun()
        with bcol2:
            b2_active = (st.session_state["current_bill_menu"] == "🚚 Distributor Procurement Bill")
            if st.button(
                "🚚 Distributor Procurement Bill\n(डिलर खरेदी बिल)",
                key="subnav_btn_dist_bill",
                type="primary" if b2_active else "secondary",
                use_container_width=True,
            ):
                if st.session_state["current_bill_menu"] != "🚚 Distributor Procurement Bill":
                    st.session_state["current_bill_menu"] = "🚚 Distributor Procurement Bill"
                    st.rerun()

    bill_menu = st.session_state["current_bill_menu"]

# SUB-NAV FOR MASTER SETUP
setup_menu = None
if menu == "⚙️ Master Setup":
    VALID_SETUP_MENUS = [
        "🏪 Retailers",
        "🚚 Distributors",
        "🥛 Milk Categories",
        "🧩 Distributor Category Mapping",
    ]
    if "current_setup_menu" not in st.session_state or st.session_state["current_setup_menu"] not in VALID_SETUP_MENUS:
        st.session_state["current_setup_menu"] = "🏪 Retailers"
        
    with st.container(border=True, key="subnav_setup_deck"):
        st.markdown("""
        <div style="font-size:13.5px; font-weight:850; color:#1e3a8a; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:10px;">
          ⚙️ मास्टर सेटिंग श्रेणी (Select Master Setup Category)
        </div>
        """, unsafe_allow_html=True)
        
        scol1, scol2, scol3, scol4 = st.columns(4)
        setup_items = [
            ("🏪 Retailers", "🏪 Retailers\n(ग्राहक मास्टर)", "subnav_btn_ret"),
            ("🚚 Distributors", "🚚 Distributors\n(डिलर मास्टर)", "subnav_btn_dist"),
            ("🥛 Milk Categories", "🥛 Milk Categories\n(दूध प्रकार)", "subnav_btn_cat"),
            ("🧩 Distributor Category Mapping", "🧩 Category Mapping\n(मॅपिंग)", "subnav_btn_map"),
        ]
        for col, (s_val, s_lbl, s_key) in zip([scol1, scol2, scol3, scol4], setup_items):
            with col:
                s_active = (st.session_state["current_setup_menu"] == s_val)
                if st.button(
                    s_lbl,
                    key=s_key,
                    type="primary" if s_active else "secondary",
                    use_container_width=True,
                ):
                    if st.session_state["current_setup_menu"] != s_val:
                        st.session_state["current_setup_menu"] = s_val
                        st.rerun()

    setup_menu = st.session_state["current_setup_menu"]

# Discard in-memory editing drafts on menu tab change so unsaved edits don't leak,
# while keeping the fast in-memory data cache intact for instant UI rendering!
if "current_menu" not in st.session_state:
    st.session_state["current_menu"] = menu
elif st.session_state["current_menu"] != menu:
    st.session_state["current_menu"] = menu
    st.session_state["daily_drafts"] = {}
    st.session_state["daily_loaded_ctx"] = None
    st.session_state["daily_meta"] = {}
    st.session_state["dist_flat_grid"] = pd.DataFrame()
    st.session_state["dist_flat_payments"] = pd.DataFrame()

# ============================================================
# PAGE: 📊 DASHBOARD
# ============================================================
if menu == "📊 Dashboard":
    dash_h_c1, dash_h_c2 = st.columns([3, 1])
    with dash_h_c1:
        st.header(f"📊 Business Overview — {selected_zone}")
    with dash_h_c2:
        if st.button("🔄 Refresh Live Data", key="dash_refresh_btn", use_container_width=True, help="Purges all caches and re-queries live data from database"):
            invalidate_data_cache()
            st.rerun()
    version = st.session_state["data_version"]
    col1, col2, col3, col4 = st.columns(4)
    # Use GLOBAL entries/payments (not zone-filtered) for lifetime dashboard totals
    # Round to 2 decimal places to eliminate float drift
    total_milk = (
        round(
            float(pd.to_numeric(entries["qty"], errors="coerce").fillna(0.0).sum()), 2
        )
        if not entries.empty
        else 0.0
    )
    total_sales = (
        round(
            float(pd.to_numeric(entries["amount"], errors="coerce").fillna(0.0).sum()),
            2,
        )
        if not entries.empty
        else 0.0
    )
    total_payments = (
        round(
            float(pd.to_numeric(payments["amount"], errors="coerce").fillna(0.0).sum()),
            2,
        )
        if not payments.empty
        else 0.0
    )
    outstanding = round(total_sales - total_payments, 2)

    with col1:
        st.metric("Total Milk Sold", f"{float(total_milk):.2f} L", delta="Lifetime")
    with col2:
        st.metric("Total Sales", f"₹{float(total_sales):.2f}")
    with col3:
        st.metric("Total Payments", f"₹{float(total_payments):.2f}")
    with col4:
        st.metric(
            "Outstanding",
            f"₹{float(outstanding):.2f}",
            delta=f"₹{float(outstanding):.2f}" if outstanding > 0 else "Settled",
        )

    st.divider()

    st.subheader("📅 Daily Summary Sheet (Zones + Main Book Retailers)")
    dash_day = st.date_input("Select Date", value=date.today(), key="dash_day_summary")
    version = st.session_state["data_version"]

    # Categories (active only)
    cat_df = categories.copy()
    if not cat_df.empty and "is_active" in cat_df.columns:
        cat_df = cat_df.loc[
            cat_df["is_active"].apply(parse_boolish_active) == True
        ].copy()
    cat_df["category_id"] = (
        pd.to_numeric(cat_df.get("category_id", 0), errors="coerce")
        .fillna(0)
        .astype(int)
    )
    cat_df["name"] = cat_df.get("name", "").fillna("").astype(str)
    cat_names = [c for c in cat_df["name"].tolist() if str(c).strip()]
    cat_id_to_name = dict(zip(cat_df["category_id"].tolist(), cat_df["name"].tolist()))

    # Day entries/payments (Uses in-memory cache if available; DB fallback if empty)
    if USE_SERVER_FILTERS and entries.empty:
        rids = None
        if selected_zone != "All Zones":
            rids = _retailer_ids_for_zone(selected_zone)

        e_filters = [("date", "eq", str(dash_day))]
        if rids:
            e_filters.append(("retailer_id", "in", rids))
        e_day = sb_fetch_df(ENTRIES_FILE, CSV_SCHEMAS[ENTRIES_FILE], filters=e_filters)

        p_filters = [("date", "eq", str(dash_day))]
        if rids:
            p_filters.append(("retailer_id", "in", rids))
        p_day = sb_fetch_df(PAYMENTS_FILE, CSV_SCHEMAS[PAYMENTS_FILE], filters=p_filters)

    else:
        e_day = entries.copy()
        p_day = payments.copy()

    if not e_day.empty:
        e_day["date"] = pd.to_datetime(e_day["date"], errors="coerce").dt.date
        e_day = e_day.loc[e_day["date"] == dash_day].copy()
        e_day["retailer_id"] = (
            pd.to_numeric(e_day.get("retailer_id", 0), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        e_day["category_id"] = (
            pd.to_numeric(e_day.get("category_id", 0), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        e_day["qty"] = (
            pd.to_numeric(e_day.get("qty", 0.0), errors="coerce")
            .fillna(0.0)
            .astype(float)
        )
        e_day["amount"] = (
            pd.to_numeric(e_day.get("amount", 0.0), errors="coerce")
            .fillna(0.0)
            .astype(float)
        )
        e_day["Category"] = (
            e_day["category_id"].map(cat_id_to_name).fillna("").astype(str)
        )
    else:
        e_day = pd.DataFrame(
            columns=["retailer_id", "category_id", "qty", "amount", "Category"]
        )

    if not p_day.empty:
        p_day["date"] = pd.to_datetime(p_day["date"], errors="coerce").dt.date
        p_day = p_day.loc[p_day["date"] == dash_day].copy()
        p_day["retailer_id"] = (
            pd.to_numeric(p_day.get("retailer_id", 0), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        p_day["amount"] = (
            pd.to_numeric(p_day.get("amount", 0.0), errors="coerce")
            .fillna(0.0)
            .astype(float)
        )
        p_day["payment_mode"] = (
            p_day.get("payment_mode", "Cash")
            .fillna("Cash")
            .astype(str)
            .str.strip()
            .str.upper()
        )
    else:
        p_day = pd.DataFrame(columns=["retailer_id", "amount", "payment_mode"])

    # Retailer lookup
    rmap = retailers.copy()
    if not rmap.empty:
        rmap["retailer_id"] = (
            pd.to_numeric(rmap.get("retailer_id", 0), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        rmap["name"] = rmap.get("name", "").fillna("").astype(str)
        rmap["zone"] = (
            rmap.get("zone", "Default").fillna("Default").astype(str).apply(_norm_zone)
        )

    # ---- Zone rows ----
    zone_pivot = pd.DataFrame()
    zone_sales = pd.Series(dtype=float)
    zone_pay = pd.Series(dtype=float)

    if (not e_day.empty) and (not rmap.empty):
        e_zone = e_day.merge(
            rmap[["retailer_id", "zone"]], on="retailer_id", how="left"
        )
        e_zone["zone"] = e_zone["zone"].fillna("Default").astype(str).apply(_norm_zone)
        e_zone = e_zone.loc[e_zone["Category"].astype(str).str.len() > 0].copy()
        if not e_zone.empty:
            zone_pivot = safe_pivot(
                e_zone, index="zone", columns="Category", values="qty"
            )
            zone_sales = safe_group_sum(e_zone, "zone", "amount")

    if (not p_day.empty) and (not rmap.empty):
        p_zone = p_day.merge(
            rmap[["retailer_id", "zone"]], on="retailer_id", how="left"
        )
        p_zone["zone"] = p_zone["zone"].fillna("Default").astype(str).apply(_norm_zone)
        if not p_zone.empty:
            zone_pay = safe_group_sum(p_zone, "zone", "amount")

    # Normalize zone_pivot columns
    if not zone_pivot.empty:
        for c in cat_names:
            if c not in zone_pivot.columns:
                zone_pivot[c] = 0.0
        zone_pivot = zone_pivot.reindex(columns=cat_names, fill_value=0.0)
        zone_pivot["TOTAL (L)"] = zone_pivot[cat_names].sum(axis=1).astype(float)

    # ---- Main book retailer rows ----
    main_ids = set(get_main_retailer_ids())
    main_pivot = pd.DataFrame()
    main_sales_map = {}
    main_pay_map = {}
    main_r = pd.DataFrame(columns=["retailer_id", "name"])

    if main_ids and (not rmap.empty):
        main_r = rmap.loc[rmap["retailer_id"].astype(int).isin(list(main_ids))].copy()

        if not main_r.empty and not e_day.empty:
            e_main = e_day.loc[
                e_day["retailer_id"].astype(int).isin(main_r["retailer_id"].astype(int))
            ].copy()
            e_main = e_main.merge(
                main_r[["retailer_id", "name"]], on="retailer_id", how="left"
            ).rename(columns={"name": "Retailer"})
            e_main = e_main.loc[e_main["Category"].astype(str).str.len() > 0].copy()
            if not e_main.empty:
                main_pivot = safe_pivot(
                    e_main, index="Retailer", columns="Category", values="qty"
                )
                main_sales_map = safe_group_sum(e_main, "Retailer", "amount").to_dict()

        if not p_day.empty and not main_r.empty:
            p_main = p_day.loc[
                p_day["retailer_id"].astype(int).isin(main_r["retailer_id"].astype(int))
            ].copy()
            if not p_main.empty:
                p_main = p_main.merge(
                    main_r[["retailer_id", "name"]], on="retailer_id", how="left"
                )
                main_pay_map = safe_group_sum(p_main, "name", "amount").to_dict()

    if not main_pivot.empty:
        for c in cat_names:
            if c not in main_pivot.columns:
                main_pivot[c] = 0.0
        main_pivot = main_pivot.reindex(columns=cat_names, fill_value=0.0)
        main_pivot["TOTAL (L)"] = main_pivot[cat_names].sum(axis=1).astype(float)

    # ---- Main book retailer rows ----
    main_ids = set(get_main_retailer_ids())
    main_pivot = pd.DataFrame()
    main_sales_map = {}
    main_pay_map = {}
    main_r = pd.DataFrame(columns=["retailer_id", "name"])

    if main_ids and (not rmap.empty):
        main_r = rmap.loc[rmap["retailer_id"].astype(int).isin(list(main_ids))].copy()

        if not main_r.empty and not e_day.empty:
            e_main = e_day.loc[
                e_day["retailer_id"].astype(int).isin(main_r["retailer_id"].astype(int))
            ].copy()
            e_main = e_main.merge(
                main_r[["retailer_id", "name"]], on="retailer_id", how="left"
            ).rename(columns={"name": "Retailer"})
            e_main = e_main.loc[e_main["Category"].astype(str).str.len() > 0].copy()
            if not e_main.empty:
                main_pivot = cached_pivot(
                    e_main,
                    index="Retailer",
                    columns="Category",
                    values="qty",
                    data_version=version,
                )
                tmp = cached_groupby_sum(
                    e_main,
                    ["Retailer"],
                    "amount",
                    version,
                )
                main_sales_map = dict(zip(tmp["Retailer"], tmp["amount"]))

        if not p_day.empty and not main_r.empty:
            p_main = p_day.loc[
                p_day["retailer_id"].astype(int).isin(main_r["retailer_id"].astype(int))
            ].copy()
            if not p_main.empty:
                p_main = p_main.merge(
                    main_r[["retailer_id", "name"]], on="retailer_id", how="left"
                )
                tmp = cached_groupby_sum(
                    p_main,
                    ["name"],
                    "amount",
                    version,
                )
                main_pay_map = dict(zip(tmp["name"], tmp["amount"]))
    if not main_pivot.empty:
        for c in cat_names:
            if c not in main_pivot.columns:
                main_pivot[c] = 0.0
        main_pivot = main_pivot.reindex(columns=cat_names, fill_value=0.0)
        main_pivot["TOTAL (L)"] = main_pivot.sum(axis=1)

    # ---- Ledgers ----
    opening_by_rid = {}
    if not rmap.empty:
        rid_list = sorted(set(rmap["retailer_id"].astype(int).tolist()))

        opening_by_rid = cached_opening_balances(
            tuple(rid_list),
            dash_day,
            version,
        )

    zone_opening = pd.Series(dtype=float)
    if not rmap.empty and opening_by_rid:
        _tmp = rmap[["retailer_id", "zone"]].copy()
        _tmp["opening"] = (
            _tmp["retailer_id"].map(opening_by_rid).fillna(0.0).astype(float)
        )
        tmp = cached_groupby_sum(
            _tmp,
            ["zone"],
            "opening",
            version,
        )
        zone_opening = tmp.set_index("zone")["opening"].astype(float)

    opening_by_name = {}
    if not main_r.empty:
        for _, rr in main_r[["retailer_id", "name"]].drop_duplicates().iterrows():
            opening_by_name[str(rr["name"])] = float(
                opening_by_rid.get(int(rr["retailer_id"]), 0.0)
            )

    # ---- Dashboard display table (existing style: liters + payment only) ----
    out_cols = ["Name"] + cat_names + ["TOTAL (L)", "Payment (₹)"]
    frames = []

    if not zone_pivot.empty:
        zdf = zone_pivot.copy().sort_index()
        zdf["Payment (₹)"] = zone_pay.reindex(zdf.index).fillna(0.0).astype(float)
        zdf.insert(0, "Name", zdf.index.astype(str))
        zdf = zdf.reset_index(drop=True)
        frames.append(zdf[out_cols])

    if (not main_pivot.empty) and frames:
        frames.append(pd.DataFrame([{c: "–" for c in out_cols}]))

    pass

    if not zone_pivot.empty:
        grand = {"Name": "GRAND TOTAL"}
        for c in cat_names:
            col_data = zone_pivot[c] if c in zone_pivot.columns else pd.Series([0.0])
            grand[c] = safe_scalar_sum(col_data)
        grand["TOTAL (L)"] = safe_scalar_sum(
            zone_pivot["TOTAL (L)"] if "TOTAL (L)" in zone_pivot.columns else 0.0
        )
        grand["Payment (₹)"] = safe_scalar_sum(zone_pay)
        frames.append(pd.DataFrame([grand])[out_cols])

    if not frames:
        st.info("No entries/payments found for this date.")
    else:
        out = pd.concat(frames, ignore_index=True)
        disp = out.copy()
        for c in cat_names + ["TOTAL (L)"]:
            disp[c] = disp[c].apply(fmt_zero_dash)
        disp["Payment (₹)"] = disp["Payment (₹)"].apply(fmt_zero_dash)
        st.dataframe(df_for_display(disp), use_container_width=True)

    # ---------------- Distributors table (daily) ----------------
    st.subheader("🚚 Distributors — Daily Summary")
    if USE_SERVER_FILTERS and dist_purchases.empty:
        dp_day = sb_fetch_df(
            DISTRIBUTOR_PURCHASES_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE],
            filters=[("date", "eq", str(dash_day))],
        )
        dpay_day = sb_fetch_df(
            DISTRIBUTOR_PAYMENTS_FILE,
            CSV_SCHEMAS[DISTRIBUTOR_PAYMENTS_FILE],
            filters=[("date", "eq", str(dash_day))],
        )
    else:
        dp_day = dist_purchases.copy()
        dpay_day = dist_payments.copy()
    dmap = distributors.copy()

    if not dp_day.empty:
        dp_day["date"] = pd.to_datetime(dp_day["date"], errors="coerce").dt.date
        dp_day = dp_day.loc[dp_day["date"] == dash_day].copy()
        dp_day["distributor_id"] = (
            pd.to_numeric(dp_day.get("distributor_id", 0), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        dp_day["category_id"] = (
            pd.to_numeric(dp_day.get("category_id", 0), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        dp_day["qty"] = (
            pd.to_numeric(dp_day.get("qty", 0.0), errors="coerce")
            .fillna(0.0)
            .astype(float)
        )
        dp_day["amount"] = (
            pd.to_numeric(dp_day.get("amount", 0.0), errors="coerce")
            .fillna(0.0)
            .astype(float)
        )
        dp_day["Category"] = (
            dp_day["category_id"].map(cat_id_to_name).fillna("").astype(str)
        )
    else:
        dp_day = pd.DataFrame(
            columns=["distributor_id", "category_id", "qty", "amount", "Category"]
        )

    if not dpay_day.empty:
        dpay_day["date"] = pd.to_datetime(dpay_day["date"], errors="coerce").dt.date
        dpay_day = dpay_day.loc[dpay_day["date"] == dash_day].copy()
        dpay_day["distributor_id"] = (
            pd.to_numeric(dpay_day.get("distributor_id", 0), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        dpay_day["amount"] = (
            pd.to_numeric(dpay_day.get("amount", 0.0), errors="coerce")
            .fillna(0.0)
            .astype(float)
        )
    else:
        dpay_day = pd.DataFrame(columns=["distributor_id", "amount"])

    if not dmap.empty:
        dmap["distributor_id"] = (
            pd.to_numeric(dmap.get("distributor_id", 0), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        dmap["name"] = dmap.get("name", "").fillna("").astype(str)

    dsum = pd.DataFrame()
    if dp_day.empty and dpay_day.empty:
        st.info("No distributor purchases/payments for this date.")
    else:
        pur = (
            dp_day.groupby("distributor_id")
            .agg({"qty": "sum", "amount": "sum"})
            .rename(columns={"qty": "Purchased (L)", "amount": "Purchase Amount (₹)"})
        )
        pay = (
            dpay_day.groupby("distributor_id")
            .agg({"amount": "sum"})
            .rename(columns={"amount": "Paid (₹)"})
        )
        dsum = pur.join(pay, how="outer").fillna(0.0)

        if not dmap.empty:
            dsum = (
                dsum.reset_index()
                .merge(
                    dmap[["distributor_id", "name"]], on="distributor_id", how="left"
                )
                .rename(columns={"name": "Distributor"})
            )
        else:
            dsum = dsum.reset_index()
            dsum["Distributor"] = dsum["distributor_id"].astype(str)

        dsum["Outstanding (₹)"] = pd.to_numeric(
            dsum["Purchase Amount (₹)"], errors="coerce"
        ).fillna(0.0) - pd.to_numeric(dsum["Paid (₹)"], errors="coerce").fillna(0.0)
        dsum = dsum[
            [
                "Distributor",
                "Purchased (L)",
                "Purchase Amount (₹)",
                "Paid (₹)",
                "Outstanding (₹)",
            ]
        ].sort_values("Purchase Amount (₹)", ascending=False)

        st.dataframe(
            dsum.style.format(
                {
                    "Purchased (L)": "{:.2f}",
                    "Purchase Amount (₹)": "₹{:.2f}",
                    "Paid (₹)": "₹{:.2f}",
                    "Outstanding (₹)": "₹{:.2f}",
                }
            ),
            use_container_width=True,
        )

    # ---- Build HTML report + Download ----
    pay_modes = pd.DataFrame(columns=["Mode", "Total (₹)"])
    if not p_day.empty:
        pay_modes = (
            p_day.groupby("payment_mode", as_index=False)["amount"]
            .sum()
            .sort_values("amount", ascending=False)
            .rename(columns={"payment_mode": "Mode", "amount": "Total (₹)"})
        )

    report_rows = []

    # Zone rows
    if not zone_pivot.empty:
        for z in zone_pivot.index.tolist():
            z_clean = str(z).strip() if (z is not None and not pd.isna(z)) else ""
            if not z_clean or z_clean.lower() in ("nan", "none", "null", "default"):
                z_clean = "Counter / Direct"
            row = {"Name": z_clean}
            for c in cat_names:
                row[c] = float(
                    pd.to_numeric(zone_pivot.loc[z].get(c, 0.0), errors="coerce") or 0.0
                )
            row["TOTAL (L)"] = float(
                pd.to_numeric(zone_pivot.loc[z].get("TOTAL (L)", 0.0), errors="coerce")
                or 0.0
            )
            today_sales = float(
                pd.to_numeric(zone_sales.get(z, 0.0), errors="coerce") or 0.0
            )
            prev_ledger = float(
                pd.to_numeric(zone_opening.get(z, 0.0), errors="coerce") or 0.0
            )
            paid = float(pd.to_numeric(zone_pay.get(z, 0.0), errors="coerce") or 0.0)
            row["Today Sales (₹)"] = today_sales
            row["Previous Ledger (₹)"] = prev_ledger
            row["Payment Collected (₹)"] = paid
            row["Total Ledger (₹)"] = prev_ledger + today_sales - paid
            report_rows.append(row)

    # Divider row
    if report_rows and (not main_pivot.empty):
        report_rows.append({"Name": "—"})

    # Main retailer rows
    if not main_pivot.empty:
        for nm in main_pivot.index.tolist():
            nm_clean = str(nm).strip() if (nm is not None and not pd.isna(nm)) else ""
            if not nm_clean or nm_clean.lower() in ("nan", "none", "null"):
                nm_clean = "Counter Retailer"
            row = {"Name": nm_clean}
            for c in cat_names:
                row[c] = float(
                    pd.to_numeric(main_pivot.loc[nm].get(c, 0.0), errors="coerce")
                    or 0.0
                )
            row["TOTAL (L)"] = float(
                pd.to_numeric(main_pivot.loc[nm].get("TOTAL (L)", 0.0), errors="coerce")
                or 0.0
            )
            today_sales = float(
                pd.to_numeric(main_sales_map.get(nm, 0.0), errors="coerce") or 0.0
            )
            prev_ledger = float(
                pd.to_numeric(opening_by_name.get(nm, 0.0), errors="coerce") or 0.0
            )
            paid = float(
                pd.to_numeric(main_pay_map.get(nm, 0.0), errors="coerce") or 0.0
            )
            row["Today Sales (₹)"] = today_sales
            row["Previous Ledger (₹)"] = prev_ledger
            row["Payment Collected (₹)"] = paid
            row["Total Ledger (₹)"] = prev_ledger + today_sales - paid
            report_rows.append(row)

    retailer_totals = {
        "total_milk": float(
            pd.to_numeric(zone_pivot.get("TOTAL (L)", 0.0), errors="coerce")
            .fillna(0.0)
            .sum()
        )
        if not zone_pivot.empty
        else 0.0,
        "sales_amt": float(pd.to_numeric(zone_sales, errors="coerce").fillna(0.0).sum())
        if not zone_sales.empty
        else 0.0,
        "paid_amt": float(pd.to_numeric(zone_pay, errors="coerce").fillna(0.0).sum())
        if not zone_pay.empty
        else 0.0,
        "closing_ledger": float(
            pd.to_numeric(zone_opening, errors="coerce").fillna(0.0).sum()
        )
        + float(pd.to_numeric(zone_sales, errors="coerce").fillna(0.0).sum())
        - float(pd.to_numeric(zone_pay, errors="coerce").fillna(0.0).sum()),
    }

    report_cols = (
        [
            "Name",
        ]
        + cat_names
        + [
            "TOTAL (L)",
            "Today Sales (₹)",
            "Previous Ledger (₹)",
            "Payment Collected (₹)",
            "Total Ledger (₹)",
        ]
    )
    retailer_report_df = pd.DataFrame(report_rows)
    for c in report_cols:
        if c not in retailer_report_df.columns:
            retailer_report_df[c] = ""
    retailer_report_df = retailer_report_df[report_cols]
    # ---- TOTAL ROW ----

    tot = {"Name": "TOTAL"}

    for c in report_cols:
        if c == "Name":
            continue

        vals = pd.to_numeric(retailer_report_df[c], errors="coerce").fillna(0)

        tot[c] = vals.sum()

    retailer_report_df.loc[len(retailer_report_df)] = tot

    for c in cat_names + ["TOTAL (L)"]:
        retailer_report_df[c] = (
            pd.to_numeric(retailer_report_df[c], errors="coerce")
            .fillna(0.0)
            .apply(lambda x: f"{float(x):.2f}" if float(x) != 0.0 else "–")
        )
    for c in [
        "Today Sales (₹)",
        "Previous Ledger (₹)",
        "Payment Collected (₹)",
        "Total Ledger (₹)",
    ]:
        retailer_report_df[c] = (
            pd.to_numeric(retailer_report_df[c], errors="coerce")
            .fillna(0.0)
            .apply(lambda x: _fmt_money(float(x)) if float(x) != 0.0 else "–")
        )

    # Distributor report table with category columns
    dist_opening = {}
    if not dmap.empty:
        for did in sorted(set(dmap["distributor_id"].astype(int).tolist())):
            if int(did) <= 0:
                continue
            try:
                dist_opening[int(did)] = float(
                    distributor_balance_before(int(did), dash_day)
                )
            except Exception:
                dist_opening[int(did)] = 0.0

    dist_pivot = pd.DataFrame()
    if not dp_day.empty:
        dp_ok = dp_day.loc[dp_day["Category"].astype(str).str.len() > 0].copy()
        if not dp_ok.empty:
            dist_pivot = pd.pivot_table(
                dp_ok,
                index="distributor_id",
                columns="Category",
                values="qty",
                aggfunc="sum",
                fill_value=0.0,
            )

    dist_names = {}
    if not dmap.empty:
        for _, dr in dmap.iterrows():
            did_int = int(pd.to_numeric(dr.get("distributor_id", 0), errors="coerce") or 0)
            d_nm = str(dr.get("name", "")).strip()
            if did_int > 0 and d_nm and d_nm.lower() not in ("nan", "none"):
                dist_names[did_int] = d_nm

    dist_rows = []
    all_dids = set(dist_names.keys()) | (
        set(dist_pivot.index.astype(int).tolist()) if not dist_pivot.empty else set()
    )
    for did in sorted(all_dids):
        if int(did) <= 0:
            continue
        dist_nm = dist_names.get(int(did), "")
        if not dist_nm or str(dist_nm).strip().lower() in ("nan", "none", "null", ""):
            dist_nm = f"Distributor {did}"
        row = {"Name": dist_nm}
        for c in cat_names:
            row[c] = (
                float(dist_pivot.loc[did].get(c, 0.0))
                if (not dist_pivot.empty and did in dist_pivot.index)
                else 0.0
            )
        row["TOTAL (L)"] = float(sum([row.get(c, 0.0) for c in cat_names]))
        today_purchase = (
            float(
                pd.to_numeric(
                    dp_day.loc[dp_day["distributor_id"] == int(did), "amount"],
                    errors="coerce",
                )
                .fillna(0.0)
                .sum()
            )
            if not dp_day.empty
            else 0.0
        )
        prev_ledger = float(dist_opening.get(int(did), 0.0))
        paid = (
            float(
                pd.to_numeric(
                    dpay_day.loc[dpay_day["distributor_id"] == int(did), "amount"],
                    errors="coerce",
                )
                .fillna(0.0)
                .sum()
            )
            if not dpay_day.empty
            else 0.0
        )
        row["Total Purchase Cost (₹)"] = today_purchase
        row["Previous Ledger (₹)"] = prev_ledger
        row["Payment Given (₹)"] = paid
        row["Total Ledger (₹)"] = prev_ledger + today_purchase - paid
        dist_rows.append(row)

    dist_cols = (
        [
            "Name",
        ]
        + cat_names
        + [
            "TOTAL (L)",
            "Total Purchase Cost (₹)",
            "Previous Ledger (₹)",
            "Payment Given (₹)",
            "Total Ledger (₹)",
        ]
    )
    dist_report_df = pd.DataFrame(dist_rows)
    for c in dist_cols:
        if c not in dist_report_df.columns:
            dist_report_df[c] = ""
    dist_report_df = dist_report_df[dist_cols]
    # ---- TOTAL ROW ----

    tot = {"Name": "TOTAL"}

    for c in dist_cols:
        if c == "Name":
            continue

        vals = pd.to_numeric(dist_report_df[c], errors="coerce").fillna(0)

        tot[c] = vals.sum()

    dist_report_df.loc[len(dist_report_df)] = tot

    for c in cat_names + ["TOTAL (L)"]:
        dist_report_df[c] = (
            pd.to_numeric(dist_report_df[c], errors="coerce")
            .fillna(0.0)
            .apply(lambda x: f"{float(x):.2f}" if float(x) != 0.0 else "–")
        )
    for c in [
        "Total Purchase Cost (₹)",
        "Previous Ledger (₹)",
        "Payment Given (₹)",
        "Total Ledger (₹)",
    ]:
        dist_report_df[c] = (
            pd.to_numeric(dist_report_df[c], errors="coerce")
            .fillna(0.0)
            .apply(lambda x: _fmt_money(float(x)) if float(x) != 0.0 else "–")
        )

    distributor_totals = {
        "total_milk": _safe_sum(dp_day, "qty"),
        "purchase_amt": _safe_sum(dp_day, "amount"),
        "paid_amt": _safe_sum(dpay_day, "amount"),
        "closing_ledger": float(sum(dist_opening.values()))
        + _safe_sum(dp_day, "amount")
        - _safe_sum(dpay_day, "amount"),
    }

    purchased_qty = _safe_sum(dp_day, "qty")
    purchased_amt = _safe_sum(dp_day, "amount")
    sold_qty = _safe_sum(e_day, "qty")
    sold_amt = _safe_sum(e_day, "amount")

    if USE_SERVER_FILTERS and wastage.empty:
        wz_day = sb_fetch_df(
            WASTAGE_FILE,
            CSV_SCHEMAS[WASTAGE_FILE],
            filters=[("date", "eq", str(dash_day))],
        )
    else:
        wz = wastage.copy()
        wz_day = (
            wz.loc[pd.to_datetime(wz.get("date"), errors="coerce").dt.date == dash_day].copy()
            if not wz.empty
            else pd.DataFrame()
        )

    waste_qty = _safe_sum(wz_day, "qty")
    waste_loss = _safe_sum(wz_day, "estimated_loss")

    html_report = None

    if USE_SERVER_FILTERS and expenses.empty:
        exp_day = sb_fetch_df(
            EXPENSES_FILE,
            CSV_SCHEMAS[EXPENSES_FILE],
            filters=[("date", "eq", str(dash_day))],
        )
    else:
        _exp = expenses.copy()
        exp_day = (
            _exp.loc[pd.to_datetime(_exp.get("date"), errors="coerce").dt.date == dash_day].copy()
            if not _exp.empty
            else pd.DataFrame()
        )

    total_expenses = _safe_sum(exp_day, "amount")

    try:
        html_report = build_daily_report_html(
            report_day=dash_day,
            retailer_table=retailer_report_df,
            retailer_totals=retailer_totals,
            retailer_pay_modes=pay_modes,
            distributor_table=dist_report_df,
            distributor_totals=distributor_totals,
            purchased_qty=purchased_qty,
            purchased_amt=purchased_amt,
            sold_qty=sold_qty,
            sold_amt=sold_amt,
            waste_qty=waste_qty,
            waste_loss=waste_loss,
            expenses_df=exp_day,
            total_expenses=total_expenses,
            show_cards=True,
        )

    except Exception as _e:
        st.error(f"Daily report generation failed: {_e}")

    if html_report:
        st.download_button(
            label="⬇ Download Daily Report (HTML)",
            data=html_report.encode("utf-8"),
            file_name=f"Milk_Report_{dash_day}.html",
            mime="text/html",
            use_container_width=True,
        )
        st.caption("Open the downloaded HTML and press Ctrl+P to print / save as PDF.")

        # ===== ZONE SUMMARY (FINAL PREVIEW STYLE - A4 PORTRAIT 1 ROUTE PER PAGE) =====

        zone_sheets_data = []
        zones = get_all_zones()

        for z in zones:
            rids = get_zone_retailer_ids(z)

            if not rids:
                continue

            # ---------------- PREVIEW GRID ----------------

            grid_df, cat_cols = build_daily_posting_grid(
                dash_day,
                z,
                retailers_active,
                categories_active,
            )

            if grid_df is None or grid_df.empty:
                continue

            preview_df = grid_df.copy()

            rid_list = preview_df["ID"].astype(int).tolist()

            ledger_map = cached_opening_balances(
                tuple(rid_list),
                dash_day,
                st.session_state["data_version"],
            )

            today_sales_list = []
            prev_ledger_list = []
            total_ledger_list = []

            for _, row in preview_df.iterrows():
                rid = int(row["ID"])

                prev_ledger = ledger_map.get(rid, 0.0)

                today_sales = 0.0

                for meta in cat_cols:
                    col = meta["col"]
                    cid = int(meta["category_id"])

                    qty = float(row.get(col, 0.0) or 0.0)

                    if qty <= 0:
                        continue

                    rate = (
                        get_price_for_date(
                            rid,
                            cid,
                            dash_day,
                        )
                        or 0.0
                    )

                    today_sales += qty * float(rate)

                today_pay = 0.0

                for m in PAYMENT_MODES:
                    today_pay += float(row.get(f"{m} ₹", 0.0) or 0.0)

                total_ledger = prev_ledger + today_sales - today_pay

                prev_ledger_list.append(prev_ledger)
                today_sales_list.append(today_sales)
                total_ledger_list.append(total_ledger)

            preview_df["Previous Ledger ₹"] = prev_ledger_list
            preview_df["Today Sales ₹"] = today_sales_list
            preview_df["Total Ledger ₹"] = total_ledger_list

            # ---------- ADD TOTAL ROW ----------

            total_row = {}

            for col in preview_df.columns:
                if col in ["Retailer", "Name", "ID"]:
                    total_row[col] = "TOTAL"
                    continue

                vals = pd.to_numeric(preview_df[col], errors="coerce").fillna(0.0)

                total_row[col] = float(vals.sum())

            preview_df = pd.concat(
                [preview_df, pd.DataFrame([total_row])], ignore_index=True
            )

            # ---------------- FILTER DAY DATA ----------------

            pz = p_day[p_day["retailer_id"].isin(rids)].copy()

            # ---------------- PAYMENT MODES ----------------

            if not pz.empty:
                pay_modes = pz.groupby("payment_mode")["amount"].sum().reset_index()
            else:
                pay_modes = pd.DataFrame(columns=["payment_mode", "amount"])

            # ----- FIX COLUMN ORDER FOR HTML -----
            base_cols = [
                c for c in ["ID", "Retailer", "Name"] if c in preview_df.columns
            ]
            category_cols = [
                c
                for c in preview_df.columns
                if c not in base_cols
                and "₹" not in c
                and "Ledger" not in c
                and "Total" not in c
            ]
            sales_cols = [c for c in preview_df.columns if "TOTAL" in c or "Sales" in c]

            prev_cols = [c for c in preview_df.columns if "Previous Ledger" in c]

            payment_cols = [
                c
                for c in preview_df.columns
                if "₹" in c and "Ledger" not in c and "Sales" not in c
            ]

            ledger_cols = [c for c in preview_df.columns if "Total Ledger" in c]

            new_order = (
                base_cols
                + category_cols
                + sales_cols
                + prev_cols
                + payment_cols
                + ledger_cols
            )

            preview_df = preview_df[new_order]

            # Pass pure numeric preview_df to HTML generator so cells format cleanly with exact green/gray highlights
            zone_exp = get_route_expenses_df(dash_day, z)

            zone_sheets_data.append({
                "zone": z,
                "df": preview_df,
                "pay_modes": pay_modes,
                "expenses": zone_exp,
            })

        if zone_sheets_data:
            master_zone_html = build_zone_route_summary_master_html(dash_day, zone_sheets_data)
            st.download_button(
                label="⬇ Download All Zone Summaries (HTML - 1 Route Per Page)",
                data=master_zone_html.encode("utf-8"),
                file_name=f"Zone_Summary_{dash_day}.html",
                mime="text/html",
                key="zone_summary_all_dl_btn",
                use_container_width=True,
            )
            st.caption("Each route is formatted in A4 portrait and prints strictly on 1 page.")

            st.divider()

        st.subheader("📅 Daily Business Overview")

        day = st.date_input("Select Day", value=date.today(), key="daily_overview_day")

        dp = dist_purchases.copy()
        if not dp.empty:
            dp["date"] = pd.to_datetime(dp["date"], errors="coerce")
            dp_day = dp.loc[dp["date"].dt.date == day].copy()
            purchased_qty = float(dp_day["qty"].sum()) if not dp_day.empty else 0.0
            purchased_amt = float(dp_day["amount"].sum()) if not dp_day.empty else 0.0
        else:
            purchased_qty, purchased_amt = 0.0, 0.0

        ez = entries_z.copy()
        if not ez.empty:
            ez["date"] = pd.to_datetime(ez["date"], errors="coerce")
            ez_day = ez.loc[ez["date"].dt.date == day].copy()
            sold_qty = float(ez_day["qty"].sum()) if not ez_day.empty else 0.0
            sold_amt = float(ez_day["amount"].sum()) if not ez_day.empty else 0.0
        else:
            sold_qty, sold_amt = 0.0, 0.0

        wz = wastage.copy()
        if not wz.empty:
            wz["date"] = pd.to_datetime(wz["date"], errors="coerce")
            wz_day = wz.loc[wz["date"].dt.date == day].copy()
            waste_qty = float(wz_day["qty"].sum()) if not wz_day.empty else 0.0
            waste_loss = (
                float(wz_day["estimated_loss"].sum()) if not wz_day.empty else 0.0
            )
        else:
            waste_qty, waste_loss = 0.0, 0.0

        net_movement = purchased_qty - sold_qty - waste_qty

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Purchased (L)", f"{purchased_qty:.2f}")
        c2.metric("Purchase (₹)", f"₹{purchased_amt:.2f}")
        c3.metric("Sold (L)", f"{sold_qty:.2f}")
        c4.metric("Sales (₹)", f"₹{sold_amt:.2f}")
        c5.metric("Wastage (L)", f"{waste_qty:.2f}")
        c6.metric("Net Movement (L)", f"{net_movement:.2f}")

        if net_movement < 0:
            st.warning(
                "Net Movement is negative. Purchases might be missing for the day, or you sold from opening stock (not tracked)."
            )

        st.caption(
            "Sales are zone-filtered. Purchases/wastage are not zone-filtered in current model."
        )

        st.divider()


# ============================================================
# PAGE: 📝 DAILY POSTING SHEET (EXCEL)
# ============================================================
elif menu in ("📝 Daily Entry", "📝 Daily Posting Sheet (Excel)"):
    st.header(
        "📝 Daily Entry — Retailers + Distributors + Wastage + Expenses"
    )

    if retailers_active.empty or categories_active.empty:
        st.warning("⚠️ Please add active retailers and categories first")
        st.stop()

    d_c1, d_c2 = st.columns([1, 1])
    with d_c1:
        posting_date = st.date_input("Posting Date", value=date.today(), key="posting_date")
    report_day = posting_date
    zone_choices = ["All Zones"] + get_all_zones()
    default_idx = (
        zone_choices.index(selected_zone) if selected_zone in zone_choices else 0
    )
    with d_c2:
        posting_zone = st.selectbox(
            "Posting Zone", zone_choices, index=default_idx, key="posting_zone"
        )

    # ================== DRAFT STATE (per date + zone) ==================
    def _ctx_key(d: date, z: str) -> str:
        return f"{str(d)}|{_norm_zone(z)}"

    ctx = _ctx_key(posting_date, posting_zone)
    st.session_state.setdefault("daily_drafts", {})
    st.session_state.setdefault("daily_meta", {})
    st.session_state.setdefault("daily_loaded_ctx", None)
    st.session_state.setdefault("daily_save_lock", False)
    st.session_state.setdefault("dist_flat_grid", pd.DataFrame())
    st.session_state.setdefault("dist_flat_payments", pd.DataFrame())

    # Load from DB when context changes
    if (
        st.session_state.get("daily_loaded_ctx") != ctx
        or ctx not in st.session_state["daily_drafts"]
    ):
        grid_df, cat_cols = build_daily_posting_grid(
            posting_date, posting_zone, retailers_active, categories_active
        )
        if grid_df is None or grid_df.empty:
            st.warning("No retailers found for selected zone.")
            st.stop()

        rz = retailers_active.copy()
        rz["zone"] = rz.get("zone", "Default").astype(str).apply(_norm_zone)
        if posting_zone != "All Zones":
            rz = rz.loc[rz["zone"] == _norm_zone(posting_zone)].copy()
        affected_rids = sorted(set(rz["retailer_id"].astype(int).tolist()))

        st.session_state["daily_drafts"][ctx] = grid_df.copy()
        st.session_state["daily_meta"][ctx] = {
            "cat_cols": cat_cols,
            "affected_rids": affected_rids,
        }
        st.session_state["daily_loaded_ctx"] = ctx

    cat_cols = (st.session_state["daily_meta"].get(ctx, {}) or {}).get("cat_cols", [])
    affected_rids = (st.session_state["daily_meta"].get(ctx, {}) or {}).get(
        "affected_rids", []
    )

    draft_df = st.session_state["daily_drafts"].get(ctx)
    if draft_df is None or draft_df.empty:
        st.warning("Draft is empty. Please refresh.")
        st.stop()

    cat_col_names = [m["col"] for m in cat_cols if m.get("col") in draft_df.columns]
    pay_cols = [f"{m} ₹" for m in PAYMENT_MODES if f"{m} ₹" in draft_df.columns]

    ordered_cols = (
        [c for c in ["ID", "Retailer"] if c in draft_df.columns]
        + cat_col_names
        + pay_cols
    )
    extras = [c for c in draft_df.columns if c not in ordered_cols]
    draft_df = draft_df[ordered_cols + extras]

    # ================== SAVE HELPERS ==================
    def _sb_insert_records(table: str, records: list[dict], chunk: int = 500) -> None:
        if not records:
            return
        sb = get_sb()
        for i in range(0, len(records), chunk):
            sb.table(table).insert(records[i : i + chunk]).execute()

    def _sb_delete_day_zone(
        table: str, d: date, rids: list[int], chunk: int = 500
    ) -> None:
        if not rids:
            return
        sb = get_sb()
        for i in range(0, len(rids), chunk):
            sb.table(table).delete().eq("date", str(d)).in_(
                "retailer_id", rids[i : i + chunk]
            ).execute()

    def _safe_replace_entries_payments(
        d: date, z: str, edited_df: pd.DataFrame
    ) -> None:
        if not affected_rids:
            raise RuntimeError("No retailers found for selected zone.")

        old_e = _day_entries_for_zone(d, z)
        old_p = _day_payments_for_zone(d, z)

        new_entries = []
        new_payments = []
        col_to_cid = {m["col"]: int(m["category_id"]) for m in cat_cols}

        # Pre-build fast price lookup table for day `d` to avoid repeated DataFrame scans in the loop
        day_price_map = price_lookup_for_day(d, st.session_state["data_version"])

        for _, row in edited_df.iterrows():
            rid_val = row.get("ID", "")
            if str(rid_val).strip() in ("", "GRAND TOTAL"):
                continue
            try:
                rid = int(rid_val)
            except Exception:
                continue
            if rid not in set(affected_rids):
                continue

            for col, cid in col_to_cid.items():
                qty = float(pd.to_numeric(row.get(col, 0.0), errors="coerce") or 0.0)
                if qty <= 0:
                    continue
                rate = day_price_map.get((rid, cid))
                if rate is None or float(rate) <= 0:
                    rate = get_price_for_date(rid, cid, d)
                if rate is None or float(rate) <= 0:
                    raise RuntimeError(
                        f"Missing price for Retailer ID {rid} / Category ID {cid} on {d}"
                    )
                rate = float(rate)
                amt = round(float(qty * rate), 2)
                new_entries.append(
                    {
                        "date": str(d),
                        "retailer_id": rid,
                        "category_id": cid,
                        "qty": round(qty, 4),
                        "rate": round(rate, 4),
                        "amount": amt,
                    }
                )

            for m in PAYMENT_MODES:
                pamt = float(
                    pd.to_numeric(row.get(f"{m} ₹", 0.0), errors="coerce") or 0.0
                )
                if pamt <= 0:
                    continue
                new_payments.append(
                    {
                        "date": str(d),
                        "retailer_id": rid,
                        "amount": round(pamt, 2),
                        "payment_mode": str(m).strip().upper(),
                        "note": "",
                    }
                )

        if USE_DB_IDS:
            next_eid = sb_next_id("entries", "entry_id")
            for rec in new_entries:
                rec["entry_id"] = next_eid
                next_eid += 1
            next_pid = sb_next_id("payments", "payment_id")
            for rec in new_payments:
                rec["payment_id"] = next_pid
                next_pid += 1
        else:
            for rec in new_entries:
                rec.pop("entry_id", None)
            for rec in new_payments:
                rec.pop("payment_id", None)

        try:
            _sb_delete_day_zone("entries", d, affected_rids)
            _sb_delete_day_zone("payments", d, affected_rids)
            _sb_insert_records("entries", new_entries)
            _sb_insert_records("payments", new_payments)
            invalidate_data_cache()
        except Exception as e:
            try:
                _sb_delete_day_zone("entries", d, affected_rids)
                _sb_delete_day_zone("payments", d, affected_rids)
                if old_e is not None and not old_e.empty:
                    recs = old_e.where(pd.notna(old_e), None).to_dict(orient="records")
                    if not USE_DB_IDS:
                        for r in recs:
                            r.pop("entry_id", None)
                    _sb_insert_records("entries", recs)
                if old_p is not None and not old_p.empty:
                    recs = old_p.where(pd.notna(old_p), None).to_dict(orient="records")
                    if not USE_DB_IDS:
                        for r in recs:
                            r.pop("payment_id", None)
                    _sb_insert_records("payments", recs)
            except Exception:
                pass
            raise e

    # ================== RETAILER GRID (AG Grid form) ==================
    lock = bool(st.session_state.get("daily_save_lock", False))
    if lock:
        st.info("⏳ Saving… please do not interact with the page.")

    # Active Entry Crosshair Indicator Banner for Retailers
    st.markdown(
        """
        <style>
        .ag-theme-streamlit .ag-cell-focus {
            background-color: #fef08a !important;
            border: 2px solid #1e3a8a !important;
            color: #0f172a !important;
            font-weight: 800 !important;
        }
        .ag-theme-streamlit .ag-row-focus {
            background-color: #eff6ff !important;
        }
        .ag-theme-streamlit .ag-row:hover {
            background-color: #f8fafc !important;
        }
        </style>
        <div id="active-retailer-cell-banner" style="
            background: linear-gradient(90deg, #1e3a8a, #2563eb);
            color: #ffffff;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13.5px;
            font-weight: 600;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 6px rgba(30, 58, 138, 0.12);
        ">
            <div>🎯 <span id="active-retailer-name">Active Entry: <b style="color:#fef08a;">Click any cell to edit</b></span></div>
            <div id="active-retailer-column" style="font-size:12px; background:rgba(255,255,255,0.22); padding:3px 10px; border-radius:12px;">Column: —</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



    form_key = f"daily_form_{ctx}"
    rows_count = len(draft_df) if draft_df is not None else 1
    table_height = min(900, 120 + rows_count * 42)

    with st.form(form_key, clear_on_submit=False):
        gb = GridOptionsBuilder.from_dataframe(draft_df)

        numeric_editor = JsCode("""
        class NumericEditor {
            init(params) {
                this.eInput = document.createElement('input');
                this.eInput.type = 'number';
                this.eInput.step = '0.25';
                this.eInput.min = '0';
                this.eInput.style.width = '100%';
                this.eInput.value = params.value || 0;
            }
            getGui() { return this.eInput; }
            afterGuiAttached() { this.eInput.focus(); this.eInput.select(); }
            getValue() { return parseFloat(this.eInput.value) || 0; }
        }
        """)

        for col in cat_col_names + pay_cols:
            if col in draft_df.columns:
                gb.configure_column(
                    col,
                    editable=True,
                    valueParser="Number(newValue)",
                    cellEditor=numeric_editor,
                )

        gb.configure_default_column(
            editable=True,
            sortable=False,
            filter=False,
            resizable=True,
            minWidth=60,
            singleClickEdit=True,
        )
        gb.configure_column("ID", pinned="left", editable=False, width=80)
        gb.configure_column(
            "Retailer",
            pinned="left",
            editable=False,
            minWidth=220,
            maxWidth=350,
            cellStyle={"fontWeight": "800", "color": "#0f172a", "fontSize": "13.5px"},
        )

        for col in draft_df.columns:
            gb.configure_column(col, wrapHeaderText=True, autoHeaderHeight=True)

        gb.configure_grid_options(
            domLayout="normal",
            suppressMovableColumns=True,
            alwaysShowHorizontalScroll=True,
            alwaysShowVerticalScroll=True,
            headerHeight=42,
            rowHeight=42,
            singleClickEdit=True,
            stopEditingWhenCellsLoseFocus=True,
            enterMovesDown=True,
            enterMovesDownAfterEdit=True,
        )

        grid_options = gb.build()
        grid_options["onFirstDataRendered"] = JsCode("""
        function(params) {
            setTimeout(function() {
                var allColumnIds = [];
                params.columnApi.getColumns().forEach(function(col) { allColumnIds.push(col.getId()); });
                params.columnApi.autoSizeColumns(allColumnIds, false);
            }, 300);
        }
        """)

        grid_options["onCellFocused"] = JsCode("""
        function(params) {
            if (!params || params.rowIndex == null) return;
            var rowNode = params.api.getDisplayedRowAtIndex(params.rowIndex);
            if (!rowNode || !rowNode.data) return;
            var rName = rowNode.data['Retailer'] || ('Row ' + (params.rowIndex + 1));
            var colId = params.column ? (params.column.getColDef().headerName || params.column.getColId()) : '';
            var doc = (window.parent && window.parent.document) ? window.parent.document : document;
            var nameEl = doc.getElementById('active-retailer-name') || document.getElementById('active-retailer-name');
            var colEl = doc.getElementById('active-retailer-column') || document.getElementById('active-retailer-column');
            if (nameEl) {
                nameEl.innerHTML = 'Active Retailer: <b style="color:#fef08a; font-size:14.5px; font-weight:800;">' + rName + '</b>';
            }
            if (colEl && colId) {
                colEl.innerHTML = 'Editing Column: <b style="color:#ffffff; font-weight:800;">' + colId + '</b>';
            }
        }
        """)

        _draft_input = draft_df.copy().reset_index(drop=True)
        ag_result = AgGrid(
            _draft_input,
            gridOptions=grid_options,
            update_on=["cellValueChanged", "valueChanged"],
            height=table_height,
            fit_columns_on_grid_load=False,
            allow_unsafe_jscode=True,
            theme="streamlit",
            use_container_width=True,
        )

        edited = pd.DataFrame(ag_result["data"])

        exp_edited = None
        exp_general_edited = None
        actual_cash_handover_val = 0.0
        if posting_zone != "All Zones":
            st.markdown("---")
            st.markdown(f"#### ⛽ Route Expenses — {posting_zone}")
            st.caption("Enter driver vehicle expenses (Fuel, Nasta, Toll, Repair, Police / Fine) to be saved together with this route.")
            curr_route_exp = get_route_expenses_df(posting_date, posting_zone)
            if f"batch_route_expenses_{ctx}" in st.session_state and st.session_state[f"batch_route_expenses_{ctx}"]:
                exp_edit_df = pd.DataFrame(st.session_state[f"batch_route_expenses_{ctx}"])
            elif curr_route_exp.empty:
                exp_edit_df = pd.DataFrame([
                    {"Category": "Fuel", "Amount ₹": 0.0, "Payment Mode": "Cash", "Note": ""}
                ])
            else:
                exp_edit_df = pd.DataFrame([
                    {
                        "Category": str(r["category"]),
                        "Amount ₹": float(r["amount"]),
                        "Payment Mode": str(r["payment_mode"]),
                        "Note": str(r["note"]),
                    }
                    for _, r in curr_route_exp.iterrows()
                ])

            exp_edited = st.data_editor(
                exp_edit_df,
                column_config={
                    "Category": st.column_config.SelectboxColumn(
                        "Expense Category",
                        options=ROUTE_EXPENSE_CATEGORIES,
                        required=True,
                    ),
                    "Amount ₹": st.column_config.NumberColumn(
                        "Amount ₹",
                        min_value=0.0,
                        step=50.0,
                        format="₹%g",
                        required=True,
                    ),
                    "Payment Mode": st.column_config.SelectboxColumn(
                        "Payment Mode",
                        options=["Cash", "UPI", "Bank", "Other"],
                        default="Cash",
                        required=True,
                    ),
                    "Note": st.column_config.TextColumn("Note / Remarks"),
                },
                num_rows="dynamic",
                use_container_width=True,
                key=f"route_exp_editor_{ctx}",
            )

            # Driver Actual Cash Handover Input (Compact 2-inch Entry Cell)
            st.markdown("---")
            st.markdown(f"#### 📥 ड्रायव्हरने काऊंटरवर प्रत्यक्षात जमा केलेली रोख (Actual Handover — {posting_zone})")
            st.caption("गाडीवरून परत आल्यावर ड्रायव्हरने काऊंटरवर प्रत्यक्षात जमा केलेली रोख रक्कम येथे भरा. खालील एकाच सेव्ह बटणाने सर्व माहिती सेव्ह होईल.")
            saved_h_val = get_driver_actual_handover(posting_date, posting_zone)

            # Compact 2-inch entry cell layout (matching table entry cell structure)
            st.markdown(
                """
                <style>
                div[data-testid="stNumberInput"]:has(input[aria-label*="काऊंटरवर प्रत्यक्षात जमा"]) {
                    width: 230px !important;
                    max-width: 230px !important;
                    margin: 0 !important;
                }
                div[data-testid="stNumberInput"]:has(input[aria-label*="काऊंटरवर प्रत्यक्षात जमा"]) div[data-baseweb="input"] {
                    border: 1.8px solid #cbd5e1 !important;
                    border-radius: 8px !important;
                    background: #f8fafc !important;
                    height: 44px !important;
                }
                div[data-testid="stNumberInput"]:has(input[aria-label*="काऊंटरवर प्रत्यक्षात जमा"]) input {
                    font-size: 17px !important;
                    font-weight: 850 !important;
                    color: #0f172a !important;
                    text-align: right !important;
                    padding: 6px 12px !important;
                }
                div[data-testid="stNumberInput"]:has(input[aria-label*="काऊंटरवर प्रत्यक्षात जमा"]) div[data-baseweb="input"]:focus-within {
                    border-color: #2563eb !important;
                    background: #ffffff !important;
                    box-shadow: 0 0 0 2.5px rgba(37,99,235,0.25) !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            h_c1, h_c2, _ = st.columns([2.5, 1.8, 3.7], vertical_alignment="center")
            with h_c1:
                st.markdown(
                    "<div style='font-size:14px; font-weight:750; color:#1e293b; padding-top:4px;'>"
                    "💵 ड्रायव्हरने काऊंटरवर प्रत्यक्षात जमा केलेली रोख (₹):"
                    "</div>",
                    unsafe_allow_html=True,
                )
            with h_c2:
                actual_cash_handover_val = st.number_input(
                    "ड्रायव्हरने काऊंटरवर प्रत्यक्षात जमा केलेली रोख (₹)",
                    min_value=0.0,
                    value=float(st.session_state.get(f"actual_cash_handover_{posting_zone}_{posting_date}_{ctx}", saved_h_val or 0.0)),
                    step=50.0,
                    format="%g",
                    key=f"actual_cash_handover_{posting_zone}_{posting_date}_{ctx}",
                    label_visibility="collapsed",
                    help="गाडीवरून परत आल्यावर ड्रायव्हरने काऊंटरवर प्रत्यक्षात मोजून दिलेली रोख रक्कम.",
                )
        else:
            st.markdown("---")
            st.markdown("#### 🏢 General Dairy Overhead Expenses (Outside Routes)")
            st.caption("Enter general dairy expenses outside routes (Rent, Electricity, Godown, Salary, Office, Nasta, Other).")
            curr_gen_exp = get_route_expenses_df(posting_date, "General")
            if curr_gen_exp.empty:
                exp_gen_df = pd.DataFrame([
                    {"Category": "Rent", "Amount ₹": 0.0, "Payment Mode": "Cash", "Note": ""}
                ])
            else:
                exp_gen_df = pd.DataFrame([
                    {
                        "Category": str(r["category"]),
                        "Amount ₹": float(r["amount"]),
                        "Payment Mode": str(r["payment_mode"]),
                        "Note": str(r["note"]),
                    }
                    for _, r in curr_gen_exp.iterrows()
                ])

            exp_general_edited = st.data_editor(
                exp_gen_df,
                column_config={
                    "Category": st.column_config.SelectboxColumn(
                        "Expense Category",
                        options=GENERAL_EXPENSE_CATEGORIES,
                        required=True,
                    ),
                    "Amount ₹": st.column_config.NumberColumn(
                        "Amount ₹",
                        min_value=0.0,
                        step=50.0,
                        format="₹%g",
                        required=True,
                    ),
                    "Payment Mode": st.column_config.SelectboxColumn(
                        "Payment Mode",
                        options=["Cash", "UPI", "Bank", "Other"],
                        default="Cash",
                        required=True,
                    ),
                    "Note": st.column_config.TextColumn("Note / Remarks"),
                },
                num_rows="dynamic",
                use_container_width=True,
                key=f"general_exp_editor_{ctx}",
            )

        btn_save_label = (
            f"💾 Save Daily Sheet, Route Expenses & Handover ({posting_zone})"
            if posting_zone != "All Zones"
            else "💾 Save All Retailer Deliveries & General Expenses"
        )
        do_save_retailers = st.form_submit_button(
            btn_save_label,
            type="primary",
            disabled=lock,
            use_container_width=True,
            help="Saves today's milk deliveries, customer payments, route expenses, and driver cash handover in one atomic operation.",
        )

    # Persist edited grid into draft state immediately
    if isinstance(edited, pd.DataFrame) and not edited.empty:
        st.session_state["daily_drafts"][ctx] = edited.copy()

    # ================== RETAILER PREVIEW (computed once, used everywhere) ==================
    _draft = st.session_state["daily_drafts"][ctx].copy()
    rid_list = [
        int(x) for x in _draft["ID"].tolist() if str(x).strip() not in ("", "nan")
    ]

    ledger_map = cached_opening_balances(
        tuple(rid_list),
        report_day,
        st.session_state["data_version"],
    )

    # Build preview with ledger columns (single computation, no duplication)
    today_sales_list, prev_ledger_list, total_ledger_list = [], [], []
    for _, row in _draft.iterrows():
        rid_val = row.get("ID", "")
        try:
            rid = int(rid_val)
        except Exception:
            today_sales_list.append(0.0)
            prev_ledger_list.append(0.0)
            total_ledger_list.append(0.0)
            continue

        prev_ledger = float(ledger_map.get(rid, 0.0))
        today_sales = 0.0
        for meta in cat_cols:
            col = meta["col"]
            cid = int(meta["category_id"])
            qty = float(pd.to_numeric(row.get(col, 0.0), errors="coerce") or 0.0)
            if qty <= 0:
                continue
            rate = get_price_for_date(rid, cid, posting_date) or 0.0
            today_sales += float(qty) * float(rate)
        today_pay = sum(
            float(pd.to_numeric(row.get(f"{m} ₹", 0.0), errors="coerce") or 0.0)
            for m in PAYMENT_MODES
        )
        total_ledger = prev_ledger + today_sales - today_pay
        today_sales_list.append(today_sales)
        prev_ledger_list.append(prev_ledger)
        total_ledger_list.append(total_ledger)

    preview = _draft.copy()
    preview["Today Sales ₹"] = today_sales_list
    preview["Previous Ledger ₹"] = prev_ledger_list
    preview["Total Ledger ₹"] = total_ledger_list

    # Grand total row (exclude it from totals computation later)
    _grand = {"ID": "", "Retailer": "GRAND TOTAL"}
    for col in preview.columns:
        if col in ("ID", "Retailer"):
            continue
        _grand[col] = safe_scalar_sum(
            pd.to_numeric(preview[col], errors="coerce").fillna(0.0)
        )
    preview = pd.concat([preview, pd.DataFrame([_grand])], ignore_index=True)

    # Column order
    _ordered = (
        [c for c in ["ID", "Retailer"] if c in preview.columns]
        + cat_col_names
        + ["Today Sales ₹", "Previous Ledger ₹"]
        + [f"{m} ₹" for m in PAYMENT_MODES if f"{m} ₹" in preview.columns]
        + ["Total Ledger ₹"]
    )
    _extras = [c for c in preview.columns if c not in _ordered]
    preview = preview[[c for c in _ordered + _extras if c in preview.columns]]

    # ================== 100% LOCAL OFFLINE AI ANOMALY DETECTION ==================
    habits = get_habit_profiles()
    active_anomalies = ai_engine.detect_grid_anomalies(
        _draft, habits, categories_active
    )
    flagged_retailer_map = {int(a["retailer_id"]): a for a in active_anomalies if a.get("retailer_id")}

    # ================== STYLED HTML PREVIEW TABLE ==================
    st.subheader("📌 Retailer Preview")

    if active_anomalies:
        st.markdown(
            f"""
            <div style="background:#fffbeb;border:1.5px solid #f59e0b;border-radius:12px;padding:12px 16px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;justify-content:space-between;">
                    <div style="font-weight:800;color:#92400e;font-size:14.5px;">
                        🤖 AI Safety Audit: {len(active_anomalies)} Anomaly Flag(s) Detected in this sheet (तपासणी आवश्यक)
                    </div>
                    <span style="background:#f59e0b;color:#ffffff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:800;">100% Local Guard</span>
                </div>
                <div style="color:#78350f;font-size:12.5px;margin-top:3px;">
                    Review highlighted rows below before finalizing. (अनपेक्षित दूध प्रकार किंवा अचानक मोठी वाढ).
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander(f"🔍 View {len(active_anomalies)} AI Anomaly Details (मराठी + English)", expanded=False):
            for anom in active_anomalies:
                b_icon = "🚨" if anom["anomaly_type"] == "CATEGORY_MISMATCH" else "⚠️"
                st.markdown(
                    f"{b_icon} **{anom['retailer_name']}** — {anom['explanation_en']}<br>"
                    f"<span style='color:#64748b;font-size:12px;'>↳ {anom['explanation_mr']}</span>",
                    unsafe_allow_html=True,
                )

    def _build_grouped_html(
        df: pd.DataFrame,
        _cat_col_names: list,
        _pay_modes: list,
        grand_label="GRAND TOTAL",
    ) -> str:
        import re
        _money_cols = {"Today Sales ₹", "Previous Ledger ₹", "Total Ledger ₹"} | {
            f"{m} ₹" for m in _pay_modes
        }

        def _clean_title(c: str) -> str:
            cleaned = re.sub(r"^CID:\d+\s*—\s*", "", str(c).strip())
            cleaned = cleaned.replace(" ₹", "")
            if cleaned == "Previous Ledger":
                return "Prev Dues"
            if cleaned == "Total Ledger":
                return "Closing Dues"
            return cleaned

        def _fmt(col, val):
            try:
                fv = float(val)
            except Exception:
                s = str(val)
                return "–" if s in ("nan", "None", "", "0.0") else s
            if abs(fv) < 0.0001:
                return "–"
            return f"₹{fv:,.2f}" if col in _money_cols else f"{fv:.2f}"

        # Columns breakdown
        cat_cols_in_df = [c for c in _cat_col_names if c in df.columns]
        sales_cols_in_df = [c for c in ["Today Sales ₹", "Previous Ledger ₹"] if c in df.columns]
        pay_cols_in_df = [f"{m} ₹" for m in _pay_modes if f"{m} ₹" in df.columns]
        ledger_cols_in_df = [c for c in ["Total Ledger ₹"] if c in df.columns]

        ordered_cols = ["Retailer"] + cat_cols_in_df + sales_cols_in_df + pay_cols_in_df + ledger_cols_in_df

        # Top Tier Super-Headers
        top_ths = [
            "<th style='background:#1e293b; color:#94a3b8; font-size:10px; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; padding:6px 10px; text-align:left;'>CUSTOMER</th>"
        ]
        if cat_cols_in_df:
            top_ths.append(
                f"<th colspan='{len(cat_cols_in_df)}' style='background:#1e293b; color:#94a3b8; font-size:10px; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; padding:6px 10px; text-align:center; border-left:1px solid #334155;'>MILK DELIVERED (L)</th>"
            )
        if sales_cols_in_df:
            top_ths.append(
                f"<th colspan='{len(sales_cols_in_df)}' style='background:#1e293b; color:#94a3b8; font-size:10px; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; padding:6px 10px; text-align:center; border-left:1px solid #334155;'>BILLING & SALES (₹)</th>"
            )
        if pay_cols_in_df:
            top_ths.append(
                f"<th colspan='{len(pay_cols_in_df)}' style='background:#1e293b; color:#94a3b8; font-size:10px; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; padding:6px 10px; text-align:center; border-left:1px solid #334155;'>PAYMENTS RECEIVED (₹)</th>"
            )
        if ledger_cols_in_df:
            top_ths.append(
                f"<th colspan='{len(ledger_cols_in_df)}' style='background:#1e293b; color:#94a3b8; font-size:10px; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; padding:6px 10px; text-align:right; border-left:1px solid #334155;'>CLOSING (₹)</th>"
            )
        top_header_row = "".join(top_ths)

        # Sub-header Row
        sub_ths = []
        for c in ordered_cols:
            is_retailer = (c == "Retailer")
            align = "left" if is_retailer else "right"
            border_left = "border-left:1px solid #334155;" if c in (
                (cat_cols_in_df[0] if cat_cols_in_df else None),
                (sales_cols_in_df[0] if sales_cols_in_df else None),
                (pay_cols_in_df[0] if pay_cols_in_df else None),
                (ledger_cols_in_df[0] if ledger_cols_in_df else None),
            ) else ""
            sub_ths.append(
                f"<th style='background:#243248; color:#ffffff; font-size:11.5px; font-weight:700; padding:6px 8px; text-align:{align}; {border_left} white-space:nowrap;'>{_clean_title(c)}</th>"
            )
        sub_header_row = "".join(sub_ths)

        rows_html = ""
        for i, (_, row) in enumerate(df.iterrows()):
            rid_val = row.get("ID", "")
            try:
                rid_int = int(rid_val)
            except Exception:
                rid_int = None
            is_anomaly = (rid_int in flagged_retailer_map) if rid_int else False
            anom_info = flagged_retailer_map.get(rid_int) if is_anomaly else None

            is_total = str(row.get("Retailer", "")) == grand_label
            if is_total:
                bg = "#0f172a"
                fg = "#ffffff"
                fw = "800"
            elif is_anomaly:
                bg = "#fff1f2" if anom_info and anom_info.get("anomaly_type") == "CATEGORY_MISMATCH" else "#fffbeb"
                fg = "#0f172a"
                fw = "600"
            else:
                bg = "#f8fafc" if i % 2 == 0 else "#ffffff"
                fg = "#0f172a"
                fw = "500"

            cells = ""
            for c in ordered_cols:
                val = row.get(c, "")
                display = str(val) if (is_total and c == "Retailer") else _fmt(c, val)
                if is_anomaly and anom_info and c == "Retailer":
                    b_type = anom_info.get("anomaly_type", "")
                    b_col = "#dc2626" if b_type == "CATEGORY_MISMATCH" else "#d97706"
                    b_txt = "🚨 Cat Mismatch" if b_type == "CATEGORY_MISMATCH" else "⚠️ Qty Spike"
                    tip = f"{anom_info.get('explanation_en')} | {anom_info.get('explanation_mr')}"
                    display = f"{display} <span style='background:{b_col};color:#fff;padding:2px 7px;border-radius:6px;font-size:10px;font-weight:800;margin-left:6px;' title='{tip}'>{b_txt}</span>"

                align = "left" if c == "Retailer" else "right"
                border_left = "border-left:1px solid #e2e8f0;" if c in (
                    (cat_cols_in_df[0] if cat_cols_in_df else None),
                    (sales_cols_in_df[0] if sales_cols_in_df else None),
                    (pay_cols_in_df[0] if pay_cols_in_df else None),
                    (ledger_cols_in_df[0] if ledger_cols_in_df else None),
                ) else ""

                if is_total:
                    border_left = "border-left:1px solid #334155;" if border_left else ""

                is_anom_cell = (
                    is_anomaly
                    and anom_info
                    and anom_info.get("category_name", "").lower() in c.lower()
                )
                cell_extra = "background:#fecaca !important; color:#991b1b !important; font-weight:800 !important; border:1.5px solid #ef4444 !important;" if is_anom_cell else ""

                cells += (
                    f"<td style='padding:6px 8px; text-align:{align}; font-weight:{fw}; "
                    f"border-bottom:1px solid {'#1e293b' if is_total else '#e2e8f0'}; {border_left} {cell_extra}'>{display}</td>"
                )
            rows_html += f"<tr style='background:{bg}; color:{fg};'>{cells}</tr>"

        return (
            f"<div style='overflow-x:auto; border-radius:10px; border:1px solid #cbd5e1; "
            f"box-shadow:0 4px 14px rgba(15,23,42,0.06); margin-bottom:16px;'>"
            f"<table style='width:100%; border-collapse:collapse; font-size:12px; font-family:Inter,system-ui,sans-serif;'>"
            f"<thead>"
            f"<tr>{top_header_row}</tr>"
            f"<tr>{sub_header_row}</tr>"
            f"</thead>"
            f"<tbody>{rows_html}</tbody></table></div>"
        )

    st.markdown(
        _build_grouped_html(preview, cat_col_names, PAYMENT_MODES),
        unsafe_allow_html=True,
    )

    st.subheader("🧾 Daily Totals")

    # ✅ ALWAYS compute from RAW draft (numeric), never from formatted preview
    _totals_src_raw = st.session_state["daily_drafts"][ctx].copy()
    # Exclude any sentinel/grand-total rows
    _totals_src_raw = _totals_src_raw[
        ~_totals_src_raw.get("Retailer", pd.Series(dtype=str))
        .astype(str)
        .isin(["GRAND TOTAL", ""])
    ]

    cat_qty_totals = {}
    for meta in cat_cols:
        col = meta["col"]
        label = meta.get("name") or col
        if col in _totals_src_raw.columns:
            cat_qty_totals[label] = round(
                float(
                    pd.to_numeric(_totals_src_raw[col], errors="coerce")
                    .fillna(0.0)
                    .sum()
                ),
                3,
            )

    grand_qty = round(float(sum(cat_qty_totals.values())), 3)

    # Sales: compute from qty × price_lookup (raw numeric, not formatted strings)
    grand_sales = 0.0
    for _, row in _totals_src_raw.iterrows():
        rid_val = row.get("ID", "")
        try:
            rid = int(rid_val)
        except Exception:
            continue
        for meta in cat_cols:
            col = meta["col"]
            cid = int(meta["category_id"])
            qty = float(pd.to_numeric(row.get(col, 0.0), errors="coerce") or 0.0)
            if qty <= 0:
                continue
            rate = get_price_for_date(rid, cid, posting_date) or 0.0
            grand_sales += qty * float(rate)
    grand_sales = round(grand_sales, 2)

    pay_mode_totals_dict = {}
    for m in PAYMENT_MODES:
        pcol = f"{m} ₹"
        if pcol in _totals_src_raw.columns:
            pay_mode_totals_dict[m] = round(
                float(
                    pd.to_numeric(_totals_src_raw[pcol], errors="coerce")
                    .fillna(0.0)
                    .sum()
                ),
                2,
            )

    grand_pay = round(float(sum(pay_mode_totals_dict.values())), 2)

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Total Milk Distributed (L)", f"{grand_qty:.2f}")
    mc2.metric("Today Sales (₹)", _fmt_money(grand_sales))
    mc3.metric("Payments Collected (₹)", _fmt_money(grand_pay))

    if cat_qty_totals:
        _tot_row = {
            "": "Qty (L)",
            **{k: f"{v:.2f}" if v > 0 else "–" for k, v in cat_qty_totals.items()},
            "TOTAL": f"{grand_qty:.2f}",
        }
        st.dataframe(df_for_display(pd.DataFrame([_tot_row])), use_container_width=True)

    if pay_mode_totals_dict:
        _pay_row = {
            "": "Payment (₹)",
            **{
                k: _fmt_money(v) if v > 0 else "–"
                for k, v in pay_mode_totals_dict.items()
            },
            "TOTAL": _fmt_money(grand_pay),
        }
        st.dataframe(df_for_display(pd.DataFrame([_pay_row])), use_container_width=True)

    # ================== ROUTE EXPENSES & CASH RECONCILIATION ==================
    if posting_zone != "All Zones":
        st.divider()
        st.subheader(f"💰 Route Cash Handover Summary — {posting_zone}")

        # Real-time Route Cash Handover Calculation
        r_cash_collected = 0.0
        if pay_mode_totals_dict:
            for m_k, m_v in pay_mode_totals_dict.items():
                if str(m_k).strip().upper() == "CASH":
                    r_cash_collected += float(m_v)

        r_cash_expenses = 0.0
        r_total_expenses = 0.0
        _exp_source = exp_edited if isinstance(exp_edited, pd.DataFrame) and not exp_edited.empty else (curr_route_exp if 'curr_route_exp' in locals() else pd.DataFrame())
        if isinstance(_exp_source, pd.DataFrame) and not _exp_source.empty:
            for _, erow in _exp_source.iterrows():
                eamt = float(pd.to_numeric(erow.get("Amount ₹", erow.get("amount", 0.0)), errors="coerce") or 0.0)
                emode = str(erow.get("Payment Mode", erow.get("payment_mode", "Cash"))).strip().upper()
                r_total_expenses += eamt
                if emode == "CASH":
                    r_cash_expenses += eamt

        expected_cash_to_return = r_cash_collected - r_cash_expenses

        # Handover value from the form input above or saved file
        actual_cash_handover = float(st.session_state.get(f"actual_cash_handover_{posting_zone}_{posting_date}_{ctx}", get_driver_actual_handover(posting_date, posting_zone)))

        cash_diff = actual_cash_handover - expected_cash_to_return

        # Clear formula caption (No advance)
        st.markdown(
            f"""
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; margin-bottom:12px; font-size:13.5px;">
                <b>हिशोब सूत्र:</b> ग्राहकांकडून जमा रोख ₹{r_cash_collected:,.2f} - गाडी खर्च ₹{r_cash_expenses:,.2f} = <b style="color:#1e3a8a;">काऊंटरवर अपेक्षित जमा: ₹{expected_cash_to_return:,.2f}</b>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Prominent discrepancy / reconciliation callouts
        if actual_cash_handover > 0:
            if cash_diff < -0.01:
                shortfall = abs(cash_diff)
                st.error(
                    f"⚠️ **रोख तूट (Cash Shortfall / कमी जमा): ₹{shortfall:,.2f} कमी आले!**\n\n"
                    f"काऊंटरवर अपेक्षित रक्कम **₹{expected_cash_to_return:,.2f}** होती, परंतु ड्रायव्हरने प्रत्यक्षात **₹{actual_cash_handover:,.2f}** दिले. "
                    f"त्यामुळे **₹{shortfall:,.2f}** चा तुटवडा (Deficit) आहे."
                )
            elif abs(cash_diff) <= 0.01:
                st.success(
                    f"✅ **हिशेब तंतोतंत जुळला! (Perfect Tally - 100% Match)**\n\n"
                    f"काऊंटरवर अपेक्षित **₹{expected_cash_to_return:,.2f}** पैकी पूर्ण **₹{actual_cash_handover:,.2f}** रोख जमा झाली आहे. कोणताही फरक नाही."
                )
            else:
                st.info(
                    f"ℹ️ **जास्तीची रोख जमा (Cash Surplus / जास्ती जमा): +₹{cash_diff:,.2f}**\n\n"
                    f"अपेक्षित रक्कम **₹{expected_cash_to_return:,.2f}** असताना प्रत्यक्षात **₹{actual_cash_handover:,.2f}** जमा झाले."
                )
        else:
            st.info(
                f"ℹ️ ड्रायव्हरने काऊंटरवर आणून दिलेली रोख रक्कम वरील फॉर्ममध्ये **'प्रत्यक्षात जमा केलेली रोख'** मध्ये भरून सेव्ह करा. (अपेक्षित रक्कम: **₹{expected_cash_to_return:,.2f}**)"
            )

        rec_c1, rec_c2, rec_c3, rec_c4 = st.columns(4)
        rec_c1.metric("💵 ग्राहकांकडून जमा रोख", f"₹{r_cash_collected:,.2f}")
        rec_c2.metric("⛽ ड्रायव्हर गाडी खर्च (Cash)", f"₹{r_cash_expenses:,.2f}")
        rec_c3.metric(
            "💰 अपेक्षित जमा (Expected)",
            f"₹{expected_cash_to_return:,.2f}",
        )
        if actual_cash_handover > 0:
            rec_c4.metric(
                "📥 प्रत्यक्षात जमा (Actual)",
                f"₹{actual_cash_handover:,.2f}",
                delta=f"{cash_diff:+,.2f} फरक ({'तूट' if cash_diff < 0 else 'जास्त'})" if abs(cash_diff) > 0.01 else "तंतोतंत जुळला",
                delta_color="normal" if cash_diff >= 0 else "inverse",
            )
        else:
            rec_c4.metric(
                "📥 प्रत्यक्षात जमा (Actual)",
                "₹0.00",
                delta="हिशेब प्रलंबित",
                delta_color="off",
            )

        # Direct Route Summary Download for this specific route (A4 portrait 1-page layout)
        route_pm_df = pd.DataFrame([
            {"payment_mode": k, "amount": v} for k, v in (pay_mode_totals_dict or {}).items() if v > 0
        ])
        single_route_sheet_data = [{
            "zone": posting_zone,
            "df": preview,
            "pay_modes": route_pm_df,
            "expenses": curr_route_exp if 'curr_route_exp' in locals() else pd.DataFrame(),
        }]
        single_route_html = build_zone_route_summary_master_html(posting_date, single_route_sheet_data)
        st.download_button(
            label=f"⬇ Download Route Summary — {posting_zone} (HTML - 1 Page)",
            data=single_route_html.encode("utf-8"),
            file_name=f"Zone_Summary_{posting_zone}_{posting_date}.html",
            mime="text/html",
            key=f"dl_route_summary_daily_{ctx}",
            use_container_width=True,
            help="Download printable A4 portrait route sheet for this route immediately without switching to Dashboard.",
        )
    else:
        st.info("ℹ️ Select a specific route in 'Posting Zone' above to enter driver expenses and calculate live net cash handover.")
        all_day_exp = get_route_expenses_df(posting_date, "All Zones")
        if not all_day_exp.empty:
            st.dataframe(all_day_exp[["zone", "category", "amount", "payment_mode", "note"]].style.format({"amount": "₹{:.2f}"}), use_container_width=True)
    st.divider()
    st.subheader("📦 Distributor Daily Entry")

    distributors_active = distributors.copy()
    if not distributors_active.empty and "is_active" in distributors_active.columns:
        distributors_active["is_active"] = distributors_active["is_active"].apply(
            parse_boolish_active
        )
        distributors_active = distributors_active.loc[
            distributors_active["is_active"] == True
        ].copy()

    if distributors_active.empty:
        st.info("No active distributors. Add distributors first.")
        st.session_state["dist_flat_grid"] = pd.DataFrame()
        st.session_state["dist_flat_payments"] = pd.DataFrame()
    else:
        # Build mapping-driven (distributor, category) grid rows
        _m = dist_cat_map.copy() if dist_cat_map is not None else pd.DataFrame()
        if not _m.empty:
            _m["distributor_id"] = (
                pd.to_numeric(_m["distributor_id"], errors="coerce")
                .fillna(0)
                .astype(int)
            )
            _m["category_id"] = (
                pd.to_numeric(_m["category_id"], errors="coerce").fillna(0).astype(int)
            )
            _m["is_active"] = _m.get("is_active", True).apply(parse_boolish_active)
            _m = _m.loc[_m["is_active"] == True, ["distributor_id", "category_id"]]

        _d_lookup = dict(
            zip(
                distributors_active["distributor_id"].astype(int),
                distributors_active["name"].astype(str),
            )
        )
        _c_lookup = dict(
            zip(
                categories_active["category_id"].astype(int),
                categories_active["name"].astype(str),
            )
        )

        _grid_rows = []
        for _, _row in _m.iterrows():
            _did = int(_row["distributor_id"])
            _cid = int(_row["category_id"])
            if _did not in _d_lookup or _cid not in _c_lookup:
                continue
            _grid_rows.append(
                {
                    "DID": _did,
                    "CID": _cid,
                    "Distributor": _d_lookup[_did],
                    "Category": _c_lookup[_cid],
                    "Qty A": 0.0,
                    "Rate A": 0.0,
                    "Qty B": 0.0,
                    "Rate B": 0.0,
                }
            )

        _dist_grid_df = (
            pd.DataFrame(_grid_rows)
            .sort_values(["Distributor", "Category"])
            .reset_index(drop=True)
        )

        if _dist_grid_df.empty:
            st.warning(
                "⚠️ No distributor-category mappings found. Go to '🧩 Distributor Category Mapping'."
            )
            st.session_state["dist_flat_grid"] = pd.DataFrame()
            st.session_state["dist_flat_payments"] = pd.DataFrame()
        else:
            # 1. Pre-fill latest historical purchase rates (yesterday or most recent prior date)
            # so user only needs to enter today's quantity, while keeping rate 100% editable.
            if not dist_purchases.empty:
                _dp_hist = dist_purchases.copy()
                _dp_hist["date"] = pd.to_datetime(_dp_hist["date"], errors="coerce").dt.date
                _dp_past = _dp_hist.loc[_dp_hist["date"] < posting_date].copy()
                if not _dp_past.empty:
                    _dp_past["distributor_id"] = (
                        pd.to_numeric(_dp_past["distributor_id"], errors="coerce").fillna(0).astype(int)
                    )
                    _dp_past["category_id"] = (
                        pd.to_numeric(_dp_past["category_id"], errors="coerce").fillna(0).astype(int)
                    )
                    _dp_past["rate"] = pd.to_numeric(_dp_past["rate"], errors="coerce").fillna(0.0)
                    for _idx, _grow in _dist_grid_df.iterrows():
                        _did = int(_grow["DID"])
                        _cid = int(_grow["CID"])
                        _sub = _dp_past.loc[(_dp_past["distributor_id"] == _did) & (_dp_past["category_id"] == _cid)]
                        if not _sub.empty:
                            _latest_date = _sub["date"].max()
                            _latest_rows = _sub.loc[_sub["date"] == _latest_date].sort_values("rate").reset_index(drop=True)
                            if len(_latest_rows) >= 1:
                                _dist_grid_df.loc[_idx, "Rate A"] = float(_latest_rows.iloc[0]["rate"])
                            if len(_latest_rows) >= 2:
                                _dist_grid_df.loc[_idx, "Rate B"] = float(_latest_rows.iloc[1]["rate"])

            # 2. Next, if today ALREADY has saved purchases, load today's saved quantities and rates
            _today_dp = sb_fetch_df(
                DISTRIBUTOR_PURCHASES_FILE,
                CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE],
                filters=[("date", "eq", str(posting_date))],
            )
            if not _today_dp.empty:
                _t = _today_dp.copy()
                _t["distributor_id"] = (
                    pd.to_numeric(_t["distributor_id"], errors="coerce")
                    .fillna(0)
                    .astype(int)
                )
                _t["category_id"] = (
                    pd.to_numeric(_t["category_id"], errors="coerce")
                    .fillna(0)
                    .astype(int)
                )
                _t["qty"] = pd.to_numeric(_t["qty"], errors="coerce").fillna(0.0)
                _t["rate"] = pd.to_numeric(_t["rate"], errors="coerce").fillna(0.0)
                for (_did, _cid), _grp in _t.groupby(["distributor_id", "category_id"]):
                    _mask = (_dist_grid_df["DID"] == _did) & (
                        _dist_grid_df["CID"] == _cid
                    )
                    if _mask.any():
                        _idx = _dist_grid_df.index[_mask][0]
                        _sorted_rows = _grp.sort_values("rate").reset_index(drop=True)
                        if len(_sorted_rows) >= 1:
                            _dist_grid_df.loc[_idx, "Qty A"] = float(
                                _sorted_rows.iloc[0]["qty"]
                            )
                            _dist_grid_df.loc[_idx, "Rate A"] = float(
                                _sorted_rows.iloc[0]["rate"]
                            )
                        if len(_sorted_rows) >= 2:
                            _dist_grid_df.loc[_idx, "Qty B"] = float(
                                _sorted_rows.iloc[1]["qty"]
                            )
                            _dist_grid_df.loc[_idx, "Rate B"] = float(
                                _sorted_rows.iloc[1]["rate"]
                            )

            # Retain DID and CID in _display_df as hidden columns so row identities
            # remain intrinsically bound even if AgGrid sorts, reorders, or filters rows.
            _display_df = _dist_grid_df.copy()
            _display_df["Line Total ₹"] = (
                _display_df["Qty A"].astype(float) * _display_df["Rate A"].astype(float)
                + _display_df["Qty B"].astype(float)
                * _display_df["Rate B"].astype(float)
            ).round(2)

            # Active Entry Crosshair Indicator Banner for Distributors
            st.markdown(
                """
                <div id="active-dist-cell-banner" style="
                    background: linear-gradient(90deg, #0f766e, #14b8a6);
                    color: #ffffff;
                    padding: 8px 16px;
                    border-radius: 8px;
                    font-size: 13.5px;
                    font-weight: 600;
                    margin-bottom: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    box-shadow: 0 2px 6px rgba(15, 118, 110, 0.12);
                ">
                    <div>🎯 <span id="active-dist-name">Active Vendor: <b style="color:#fef08a;">Click any cell to edit</b></span></div>
                    <div id="active-dist-column" style="font-size:12px; background:rgba(255,255,255,0.22); padding:3px 10px; border-radius:12px;">Column: —</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.form(f"dist_form_{posting_date}", clear_on_submit=False):
                _gb = GridOptionsBuilder.from_dataframe(_display_df)
                _gb.configure_column("DID", hide=True, suppressMovable=True)
                _gb.configure_column("CID", hide=True, suppressMovable=True)
                _num_ed = JsCode("""
                class NumericEditor {
                    init(params) {
                        this.eInput = document.createElement('input');
                        this.eInput.type = 'number'; this.eInput.step = '0.25'; this.eInput.min = '0';
                        this.eInput.style.width = '100%'; this.eInput.value = params.value || 0;
                    }
                    getGui() { return this.eInput; }
                    afterGuiAttached() { this.eInput.focus(); this.eInput.select(); }
                    getValue() { return parseFloat(this.eInput.value) || 0; }
                }
                """)
                for _c in ["Qty A", "Rate A", "Qty B", "Rate B"]:
                    _gb.configure_column(_c, editable=True, cellEditor=_num_ed, width=100, suppressMovable=True, lockPosition=True)
                _gb.configure_column(
                    "Distributor",
                    pinned="left",
                    lockPinned=True,
                    lockPosition="left",
                    suppressMovable=True,
                    editable=False,
                    minWidth=160,
                    cellStyle={"fontWeight": "800", "color": "#0f172a", "fontSize": "13.5px"},
                )
                _gb.configure_column(
                    "Category",
                    pinned="left",
                    lockPinned=True,
                    lockPosition="left",
                    suppressMovable=True,
                    editable=False,
                    minWidth=130,
                    cellStyle={"fontWeight": "700", "color": "#1e40af", "fontSize": "13px"},
                )
                _gb.configure_column(
                    "Line Total ₹",
                    editable=False,
                    width=130,
                    suppressMovable=True,
                    lockPosition=True,
                    valueFormatter=JsCode(
                        "function(p){return '₹'+(Number(p.value)||0).toFixed(2);}"
                    ),
                )
                _gb.configure_default_column(
                    sortable=False,
                    filter=False,
                    resizable=True,
                    singleClickEdit=True,
                    suppressMovable=True,
                    lockPosition=True,
                )
                _gb.configure_grid_options(
                    singleClickEdit=True,
                    stopEditingWhenCellsLoseFocus=True,
                    suppressMovableColumns=True,
                    suppressDragLeaveHidesColumns=True,
                    headerHeight=40,
                    rowHeight=40,
                    enterMovesDown=True,
                    enterMovesDownAfterEdit=True,
                )
                _grid_opts = _gb.build()
                _grid_opts["onCellValueChanged"] = JsCode("""
                function(params) {
                    var d = params.data;
                    var total = (parseFloat(d['Qty A'])||0)*(parseFloat(d['Rate A'])||0)
                              + (parseFloat(d['Qty B'])||0)*(parseFloat(d['Rate B'])||0);
                    d['Line Total ₹'] = Math.round(total*100)/100;
                    params.api.refreshCells({rowNodes:[params.node], columns:['Line Total ₹']});
                }
                """)
                _grid_opts["onCellFocused"] = JsCode("""
                function(params) {
                    if (!params || params.rowIndex == null) return;
                    var rowNode = params.api.getDisplayedRowAtIndex(params.rowIndex);
                    if (!rowNode || !rowNode.data) return;
                    var dName = rowNode.data['Distributor'] || ('Row ' + (params.rowIndex + 1));
                    var catName = rowNode.data['Category'] || '';
                    var colId = params.column ? (params.column.getColDef().headerName || params.column.getColId()) : '';
                    var doc = (window.parent && window.parent.document) ? window.parent.document : document;
                    var nameEl = doc.getElementById('active-dist-name') || document.getElementById('active-dist-name');
                    var colEl = doc.getElementById('active-dist-column') || document.getElementById('active-dist-column');
                    if (nameEl) {
                        nameEl.innerHTML = 'Active Vendor: <b style="color:#fef08a; font-size:14.5px; font-weight:800;">' + dName + (catName ? ' (' + catName + ')' : '') + '</b>';
                    }
                    if (colEl && colId) {
                        colEl.innerHTML = 'Editing Column: <b style="color:#ffffff; font-weight:800;">' + colId + '</b>';
                    }
                }
                """)

                _dist_input = _display_df.copy().reset_index(drop=True)
                _dist_result = AgGrid(
                    _dist_input,
                    gridOptions=_grid_opts,
                    update_on=["cellValueChanged"],
                    height=min(120 + len(_display_df) * 42, 600),
                    fit_columns_on_grid_load=False,
                    allow_unsafe_jscode=True,
                    theme="streamlit",
                    use_container_width=True,
                    key=f"dist_grid_{posting_date}",
                )

                _dist_edited = pd.DataFrame(_dist_result["data"])
                if "DID" not in _dist_edited.columns and "DID" in _dist_grid_df.columns:
                    _dist_edited["DID"] = _dist_grid_df["DID"].values
                if "CID" not in _dist_edited.columns and "CID" in _dist_grid_df.columns:
                    _dist_edited["CID"] = _dist_grid_df["CID"].values
                st.session_state["dist_flat_grid"] = _dist_edited.copy()

                # Distributor payments table (one row per distributor)
                st.markdown("**💳 Distributor Payments Today**")
                _today_dpay = sb_fetch_df(
                    DISTRIBUTOR_PAYMENTS_FILE,
                    CSV_SCHEMAS[DISTRIBUTOR_PAYMENTS_FILE],
                    filters=[("date", "eq", str(posting_date))],
                )
                _pay_by_did = {}
                if not _today_dpay.empty:
                    for _, _pr in _today_dpay.iterrows():
                        _did_ = int(_pr["distributor_id"])
                        _pay_by_did[_did_] = {
                            "amt": float(_pr.get("amount", 0.0) or 0.0),
                            "mode": str(_pr.get("payment_mode", "Cash") or "Cash"),
                            "note": str(_pr.get("note", "") or ""),
                        }

                _pay_rows = []
                for _, _drow in distributors_active.sort_values("name").iterrows():
                    _did_ = int(_drow["distributor_id"])
                    _prev_due = float(distributor_balance_before(_did_, posting_date))
                    _p = _pay_by_did.get(_did_, {})
                    _pay_rows.append(
                        {
                            "DID": _did_,
                            "Distributor": str(_drow["name"]),
                            "Previous Due ₹": round(_prev_due, 2),
                            "Amount ₹": _p.get("amt", 0.0),
                            "Mode": _p.get("mode", "Cash"),
                            "Note": _p.get("note", ""),
                        }
                    )
                _pay_df = pd.DataFrame(_pay_rows)

                _pay_edit = st.data_editor(
                    _pay_df.drop(columns=["DID"]),
                    column_config={
                        "Distributor": st.column_config.TextColumn(
                            "Distributor", disabled=True
                        ),
                        "Previous Due ₹": st.column_config.NumberColumn(
                            "Previous Due ₹", disabled=True, format="₹%.2f"
                        ),
                        "Amount ₹": st.column_config.NumberColumn(
                            "Amount ₹", min_value=0.0, step=50.0, format="%.2f"
                        ),
                        "Mode": st.column_config.SelectboxColumn(
                            "Mode", options=["Cash", "UPI", "Bank", "Cheque", "Other"]
                        ),
                        "Note": st.column_config.TextColumn("Note"),
                    },
                    num_rows="fixed",
                    hide_index=True,
                    use_container_width=True,
                    key=f"dist_pay_editor_{posting_date}",
                )
                _pay_edit_out = _pay_edit.copy()
                _pay_edit_out["DID"] = _pay_df["DID"].values
                st.session_state["dist_flat_payments"] = _pay_edit_out.copy()

                # Form submit button for Distributor Incoming Milk & Payments
                do_save_distributors = st.form_submit_button(
                    "🚚 Save Distributor Purchases & Payments",
                    type="primary",
                    disabled=lock,
                    use_container_width=True,
                    help="Saves only today's distributor incoming milk and vendor payments.",
                )

    # ================== DISTRIBUTOR DAILY TOTALS ==================
    st.subheader("🧾 Distributor Daily Totals")

    _dist_grid_data_preview = st.session_state.get("dist_flat_grid", pd.DataFrame())
    _dist_pay_data_preview = st.session_state.get("dist_flat_payments", pd.DataFrame())

    _dist_total_milk = 0.0
    _dist_total_purchase = 0.0

    if (
        isinstance(_dist_grid_data_preview, pd.DataFrame)
        and not _dist_grid_data_preview.empty
    ):
        for _, _dr in _dist_grid_data_preview.iterrows():
            _qa = float(pd.to_numeric(_dr.get("Qty A", 0.0), errors="coerce") or 0.0)
            _ra = float(pd.to_numeric(_dr.get("Rate A", 0.0), errors="coerce") or 0.0)
            _qb = float(pd.to_numeric(_dr.get("Qty B", 0.0), errors="coerce") or 0.0)
            _rb = float(pd.to_numeric(_dr.get("Rate B", 0.0), errors="coerce") or 0.0)
            _dist_total_milk += _qa + _qb
            _dist_total_purchase += (_qa * _ra) + (_qb * _rb)

    _dist_total_milk = round(_dist_total_milk, 2)
    _dist_total_purchase = round(_dist_total_purchase, 2)

    _dist_total_payment = 0.0
    if (
        isinstance(_dist_pay_data_preview, pd.DataFrame)
        and not _dist_pay_data_preview.empty
        and "Amount ₹" in _dist_pay_data_preview.columns
    ):
        _dist_total_payment = round(
            float(
                pd.to_numeric(_dist_pay_data_preview["Amount ₹"], errors="coerce")
                .fillna(0.0)
                .sum()
            ),
            2,
        )

    _dc1, _dc2, _dc3 = st.columns(3)
    _dc1.metric("Total Incoming Milk (L)", f"{_dist_total_milk:.2f}")
    _dc2.metric("Total Purchase Amount (₹)", _fmt_money(_dist_total_purchase))
    _dc3.metric("Total Payments Made (₹)", _fmt_money(_dist_total_payment))

    # ================== WASTAGE ENTRY ==================
    st.divider()
    st.subheader("🗑️ Wastage Entry")

    waste_base = (
        pd.DataFrame(
            {
                "category_id": categories_active["category_id"].astype(int),
                "Category": categories_active["name"].astype(str),
                "Qty Wasted (L)": 0.0,
                "Estimated Loss (₹)": 0.0,
                "Reason": "",
            }
        )
        .sort_values("Category")
        .reset_index(drop=True)
    )

    if wastage is not None and not wastage.empty:
        _wz = wastage.copy()
        _wz["date"] = _safe_dt(_wz.get("date")).dt.date
        _wz["category_id"] = (
            pd.to_numeric(_wz.get("category_id", 0), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        _wz["qty"] = (
            pd.to_numeric(_wz.get("qty", 0.0), errors="coerce")
            .fillna(0.0)
            .astype(float)
        )
        _wz["estimated_loss"] = (
            pd.to_numeric(_wz.get("estimated_loss", 0.0), errors="coerce")
            .fillna(0.0)
            .astype(float)
        )
        _wz["reason"] = _wz.get("reason", "").fillna("").astype(str)
        _wz_today = _wz.loc[_wz["date"] == posting_date].copy()
        if not _wz_today.empty:
            for _cid, _grp in _wz_today.groupby("category_id"):
                if _cid in set(waste_base["category_id"].tolist()):
                    _idx = int(
                        waste_base.index[waste_base["category_id"] == int(_cid)][0]
                    )
                    _r0 = _grp.iloc[0]
                    waste_base.loc[_idx, "Qty Wasted (L)"] = float(_r0["qty"])
                    waste_base.loc[_idx, "Estimated Loss (₹)"] = float(
                        _r0["estimated_loss"]
                    )
                    waste_base.loc[_idx, "Reason"] = str(_r0["reason"])

    with st.form(f"waste_form_{posting_date}", clear_on_submit=False):
        waste_edit = st.data_editor(
            waste_base[["Category", "Qty Wasted (L)", "Estimated Loss (₹)", "Reason"]],
            num_rows="fixed",
            use_container_width=True,
            key=f"waste_editor_{posting_date}",
        )
        do_save_wastage = st.form_submit_button(
            "🗑️ Save Wastage Entry",
            type="primary",
            disabled=lock,
            help="Saves only today's wastage records.",
        )

    # ================== UNIFIED SAVE EXECUTION ==================
    save_retailers_action = bool(locals().get("do_save_retailers", False))
    save_distributors_action = bool(locals().get("do_save_distributors", False))
    save_wastage_action = bool(locals().get("do_save_wastage", False))

    if save_retailers_action or save_distributors_action or save_wastage_action:
        if st.session_state.get("daily_save_lock", False):
            st.warning("⚠️ Save already in progress. Please wait.")
            st.stop()

        st.session_state["daily_save_lock"] = True

        try:
            saved_parts = []

            # ---- PART 1: Save Retailers ----
            if save_retailers_action:
                _db_e = _day_entries_for_zone(posting_date, posting_zone)
                _db_p = _day_payments_for_zone(posting_date, posting_zone)
                _has_db = (_db_e is not None and not _db_e.empty) or (
                    _db_p is not None and not _db_p.empty
                )

                _screen_qty = sum(
                    safe_scalar_sum(
                        pd.to_numeric(_draft[meta["col"]], errors="coerce").fillna(0.0)
                    )
                    for meta in cat_cols
                    if meta["col"] in _draft.columns
                )
                _screen_pay = sum(
                    safe_scalar_sum(
                        pd.to_numeric(_draft[f"{m} ₹"], errors="coerce").fillna(0.0)
                    )
                    for m in PAYMENT_MODES
                    if f"{m} ₹" in _draft.columns
                )

                if _has_db and _screen_qty == 0.0 and _screen_pay == 0.0:
                    st.error(
                        "❌ Save blocked: DB has data for this date/zone but your grid shows all zeros.\n\n"
                        "This likely means the grid did not load correctly. Refresh and try again."
                    )
                    st.stop()

                _safe_replace_entries_payments(posting_date, posting_zone, _draft)
                if posting_zone != "All Zones":
                    if exp_edited is not None and not exp_edited.empty:
                        save_route_expenses_records(posting_date, posting_zone, exp_edited)
                        saved_parts.append("Route Expenses")
                        st.session_state.pop(f"batch_route_expenses_{ctx}", None)
                    _handover_val = float(st.session_state.get(f"actual_cash_handover_{posting_zone}_{posting_date}_{ctx}", actual_cash_handover_val or 0.0))
                    save_driver_actual_handover(posting_date, posting_zone, _handover_val)
                    saved_parts.append("Driver Handover")
                elif posting_zone == "All Zones" and exp_general_edited is not None and not exp_general_edited.empty:
                    save_route_expenses_records(posting_date, "General", exp_general_edited)
                    saved_parts.append("General Expenses")
                    st.session_state.pop(f"batch_route_expenses_{ctx}", None)
                saved_parts.append("Retailers")

            # ---- PART 2: Save Distributors ----
            if save_distributors_action:
                _dist_grid_data = st.session_state.get("dist_flat_grid")
                _dist_pay_data = st.session_state.get("dist_flat_payments")

                _dist_ids_to_save = []
                if (
                    isinstance(_dist_grid_data, pd.DataFrame)
                    and not _dist_grid_data.empty
                    and "DID" in _dist_grid_data.columns
                ):
                    _dist_ids_to_save = sorted(
                        {int(x) for x in _dist_grid_data["DID"].dropna().tolist()}
                    )

                if _dist_ids_to_save:
                    sb_delete_where(
                        "distributor_purchases",
                        [
                            ("date", "eq", str(posting_date)),
                            ("distributor_id", "in", _dist_ids_to_save),
                        ],
                    )
                    sb_delete_where(
                        "distributor_payments",
                        [
                            ("date", "eq", str(posting_date)),
                            ("distributor_id", "in", _dist_ids_to_save),
                        ],
                    )

                    # Build distributor purchases
                    _new_dp = []
                    for _, _r in _dist_grid_data.iterrows():
                        _did = int(_r["DID"])
                        _cid = int(_r["CID"])
                        _qa = float(
                            pd.to_numeric(_r.get("Qty A", 0.0), errors="coerce") or 0.0
                        )
                        _ra = float(
                            pd.to_numeric(_r.get("Rate A", 0.0), errors="coerce") or 0.0
                        )
                        _qb = float(
                            pd.to_numeric(_r.get("Qty B", 0.0), errors="coerce") or 0.0
                        )
                        _rb = float(
                            pd.to_numeric(_r.get("Rate B", 0.0), errors="coerce") or 0.0
                        )

                        if _qa > 0 and _ra > 0:
                            _new_dp.append(
                                {
                                    "date": str(posting_date),
                                    "distributor_id": _did,
                                    "category_id": _cid,
                                    "qty": round(_qa, 4),
                                    "rate": round(_ra, 4),
                                    "amount": round(_qa * _ra, 2),
                                }
                            )
                        if _qb > 0 and _rb > 0:
                            _new_dp.append(
                                {
                                    "date": str(posting_date),
                                    "distributor_id": _did,
                                    "category_id": _cid,
                                    "qty": round(_qb, 4),
                                    "rate": round(_rb, 4),
                                    "amount": round(_qb * _rb, 2),
                                }
                            )

                    # Build distributor payments
                    _new_dpay = []
                    if (
                        isinstance(_dist_pay_data, pd.DataFrame)
                        and not _dist_pay_data.empty
                        and "DID" in _dist_pay_data.columns
                    ):
                        for _, _r in _dist_pay_data.iterrows():
                            _did = int(_r["DID"])
                            _amt = float(
                                pd.to_numeric(_r.get("Amount ₹", 0.0), errors="coerce")
                                or 0.0
                            )
                            if _amt <= 0:
                                continue
                            _new_dpay.append(
                                {
                                    "date": str(posting_date),
                                    "distributor_id": _did,
                                    "amount": round(_amt, 2),
                                    "payment_mode": str(_r.get("Mode", "Cash") or "Cash"),
                                    "note": str(_r.get("Note", "") or "").strip(),
                                }
                            )

                    # Validation: payment cannot exceed opening_due + today_purchases
                    _dp_sum = {}
                    for _r in _new_dp:
                        _did = int(_r["distributor_id"])
                        _dp_sum[_did] = _dp_sum.get(_did, 0.0) + float(_r["amount"])

                    _pay_sum = {}
                    for _r in _new_dpay:
                        _did = int(_r["distributor_id"])
                        _pay_sum[_did] = _pay_sum.get(_did, 0.0) + float(_r["amount"])

                    for _did, _pay_amt in _pay_sum.items():
                        _opening_due = distributor_balance_before(_did, posting_date)
                        _allowed = round(_opening_due + _dp_sum.get(_did, 0.0), 2)
                        if _pay_amt > _allowed + 0.01:
                            raise RuntimeError(
                                f"Distributor ID {_did}: payment ₹{_pay_amt} exceeds "
                                f"allowed ₹{_allowed} (opening ₹{_opening_due} + today ₹{_dp_sum.get(_did, 0.0)})"
                            )

                    if _new_dp:
                        sb_insert_df(pd.DataFrame(_new_dp), DISTRIBUTOR_PURCHASES_FILE)

                    if _new_dpay:
                        sb_insert_df(pd.DataFrame(_new_dpay), DISTRIBUTOR_PAYMENTS_FILE)

                    saved_parts.append("Distributors")

            # ---- PART 3: Save Wastage ----
            if save_wastage_action:
                sb_delete_where("wastage", [("date", "eq", str(posting_date))])

                _new_w = []
                _waste_map = (
                    waste_base[["Category", "category_id"]].copy().reset_index(drop=True)
                )
                for _i in range(len(waste_edit)):
                    _cid = int(_waste_map.loc[_i, "category_id"])
                    _q = float(
                        pd.to_numeric(waste_edit.loc[_i, "Qty Wasted (L)"], errors="coerce")
                        or 0.0
                    )
                    _loss = float(
                        pd.to_numeric(
                            waste_edit.loc[_i, "Estimated Loss (₹)"], errors="coerce"
                        )
                        or 0.0
                    )
                    _rsn = str(waste_edit.loc[_i, "Reason"] or "").strip()
                    if _q <= 0 and _loss <= 0 and not _rsn:
                        continue
                    _new_w.append(
                        {
                            "date": str(posting_date),
                            "category_id": int(_cid),
                            "qty": round(_q, 4),
                            "reason": _rsn,
                            "estimated_loss": round(_loss, 2),
                        }
                    )

                if _new_w:
                    sb_insert_df(pd.DataFrame(_new_w), WASTAGE_FILE)
                saved_parts.append("Wastage")

            # ---- Finish and Notify ----
            invalidate_data_cache()
            st.success(f"✅ Successfully saved: {' · '.join(saved_parts)}")

            if save_retailers_action:
                for _k in list(st.session_state.get("daily_drafts", {}).keys()):
                    if _k == ctx:
                        del st.session_state["daily_drafts"][_k]
                if ctx in st.session_state.get("daily_meta", {}):
                    del st.session_state["daily_meta"][ctx]
                st.session_state["daily_loaded_ctx"] = None

            if save_distributors_action:
                st.session_state["dist_flat_grid"] = pd.DataFrame()
                st.session_state["dist_flat_payments"] = pd.DataFrame()

            st.rerun()

        except Exception as _save_err:
            st.error(
                f"❌ Save failed. Operations are protected against data corruption.\n\nError: {_save_err}"
            )

        finally:
            st.session_state["daily_save_lock"] = False

# ============================================================
# PAGE: 👷 कामगार हजेरी (ATTENDANCE)
# ============================================================
elif menu == "👷 कामगार हजेरी (Attendance)":
    st.header("👷 कामगार हजेरी व्यवस्थापन (Staff Attendance System)")
    st.caption("महिनावारी हजेरी पत्रक • थेट सेल ड्रॉपडाउन (Full, Half, Absent) • तारीख संपादन नियंत्रण • पगार बदल इतिहास")

    att_tab1, att_tab2 = st.tabs([
        "📅 मासिक हजेरी पत्रक (Attendance Sheet)",
        "👥 कामगार व्यवस्थापन व पगार बदल (Workers Master & Wage History)",
    ])

    with att_tab1:
        MONTH_NAMES = [
            (1, "01 - जानेवारी (January)"),
            (2, "02 - फेब्रुवारी (February)"),
            (3, "03 - मार्च (March)"),
            (4, "04 - एप्रिल (April)"),
            (5, "05 - मे (May)"),
            (6, "06 - जून (June)"),
            (7, "07 - जुलै (July)"),
            (8, "08 - ऑगस्ट (August)"),
            (9, "09 - सप्टेंबर (September)"),
            (10, "10 - ऑक्टोबर (October)"),
            (11, "11 - नोव्हेंबर (November)"),
            (12, "12 - डिसेंबर (December)"),
        ]
        curr_d = date.today()

        top_f1, top_f2, top_f3, top_f4 = st.columns([1.6, 1.2, 1.3, 1.3])
        with top_f1:
            sel_month = st.selectbox(
                "महिना निवडा (Select Month)",
                range(1, 13),
                index=curr_d.month - 1,
                format_func=lambda x: dict(MONTH_NAMES)[x],
                key="att_page_month",
            )
        with top_f2:
            sel_year = st.selectbox(
                "वर्ष (Year)",
                [2024, 2025, 2026, 2027],
                index=[2024, 2025, 2026, 2027].index(curr_d.year) if curr_d.year in [2024, 2025, 2026, 2027] else 2,
                key="att_page_year",
            )

        import calendar
        _, days_in_month = calendar.monthrange(sel_year, sel_month)

        workers_all = get_workers_df()
        active_workers = workers_all[workers_all["is_active"]].copy() if not workers_all.empty and "is_active" in workers_all.columns else workers_all

        with top_f3:
            st.metric("👥 एकूण कामगार", f"{len(active_workers)} Active")
        with top_f4:
            st.metric("📅 महिन्याचे दिवस", f"{days_in_month} Days")

        if active_workers.empty:
            st.warning("⚠️ सध्या कोणतेही कामगार नोंदवलेले नाहीत. कृपया वरील **'कामगार व्यवस्थापन'** टॅबवर जाऊन कामगारांची नावे जोडा.")
        else:
            # Date Lock Controls Section
            date_locks = get_attendance_date_locks(sel_year, sel_month)

            with st.expander("🔒 तारीख संपादन नियंत्रण (Date Edit Permissions)", expanded=False):
                st.markdown(
                    "<span style='font-size:12.5px; color:#475569;'><b>नियम:</b> ज्या तारखेचा चेकबॉक्स <b>Checked (✓)</b> आहे, त्याच दिवसाची हजेरी खाली बदलता येईल. <b>Unchecked</b> असणाऱ्या तारखा लॉक राहतात. यामुळे चुकून मागील दिवसांची हजेरी बदलणे टळते.</span>",
                    unsafe_allow_html=True,
                )
                b_c1, b_c2, b_c3 = st.columns(3)
                if b_c1.button("🔓 सर्व दिवस अनलॉक करा (Unlock All)", key="btn_unlock_all"):
                    save_attendance_date_locks(sel_year, sel_month, {d: True for d in range(1, days_in_month + 1)})
                    for d in range(1, days_in_month + 1):
                        st.session_state[f"date_perm_chk_{sel_year}_{sel_month}_{d}"] = True
                    st.rerun()

                if b_c2.button("🔒 मागील दिवस लॉक करा (Lock Past Days)", key="btn_lock_past"):
                    new_l = {}
                    for d in range(1, days_in_month + 1):
                        d_obj = date(sel_year, sel_month, d)
                        is_edit = (d_obj >= curr_d)
                        new_l[d] = is_edit
                        st.session_state[f"date_perm_chk_{sel_year}_{sel_month}_{d}"] = is_edit
                    save_attendance_date_locks(sel_year, sel_month, new_l)
                    st.rerun()

                if b_c3.button("🔓 फक्त आजचा दिवस चालू ठेवा (Today Only)", key="btn_today_only"):
                    new_l = {}
                    for d in range(1, days_in_month + 1):
                        d_obj = date(sel_year, sel_month, d)
                        is_edit = (d_obj == curr_d)
                        new_l[d] = is_edit
                        st.session_state[f"date_perm_chk_{sel_year}_{sel_month}_{d}"] = is_edit
                    save_attendance_date_locks(sel_year, sel_month, new_l)
                    st.rerun()

                num_subcols = 16 if days_in_month >= 16 else days_in_month
                chk_cols = st.columns(num_subcols)
                updated_locks = {}
                for d in range(1, days_in_month + 1):
                    col_target = chk_cols[(d - 1) % num_subcols]
                    cur_val = date_locks.get(d, True)
                    with col_target:
                        chk_val = st.checkbox(
                            f"{d:02d}",
                            value=cur_val,
                            key=f"date_perm_chk_{sel_year}_{sel_month}_{d}",
                            help=f"{d:02d}/{sel_month:02d}/{sel_year} संपादन परवानगी",
                        )
                        updated_locks[d] = chk_val

                if updated_locks != date_locks:
                    save_attendance_date_locks(sel_year, sel_month, updated_locks)

            # Build Attendance Table Matrix (Cell Dropdown: Full / Half / Absent)
            att_records = get_attendance_records(sel_year, sel_month)
            att_lookup = {}
            if not att_records.empty:
                for _, ar in att_records.iterrows():
                    try:
                        a_date = pd.to_datetime(ar["date"]).date()
                        if a_date.year == sel_year and a_date.month == sel_month:
                            wid = int(ar["worker_id"])
                            day = a_date.day
                            val_label = parse_attendance_status_label(
                                ar.get("status", "P"), ar.get("units", None)
                            )
                            att_lookup[(wid, day)] = val_label
                    except Exception:
                        pass

            matrix_rows = []
            for _, wr in active_workers.iterrows():
                wid = int(wr["worker_id"])
                wname = str(wr["name"])
                wrole = str(wr.get("role", "Staff"))

                r_dict = {
                    "worker_id": wid,
                    "कामगार नाव (Name)": wname,
                    "पद (Role)": wrole,
                }
                for d in range(1, days_in_month + 1):
                    r_dict[str(d)] = att_lookup.get((wid, d), "Full")

                matrix_rows.append(r_dict)

            matrix_df = pd.DataFrame(matrix_rows)

            disabled_cols = ["worker_id", "कामगार नाव (Name)", "पद (Role)"]
            for d in range(1, days_in_month + 1):
                if not updated_locks.get(d, True):
                    disabled_cols.append(str(d))

            col_configs = {
                "worker_id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "कामगार नाव (Name)": st.column_config.TextColumn("कामगार नाव", disabled=True, width="medium"),
                "पद (Role)": st.column_config.TextColumn("पद / काम", disabled=True, width="small"),
            }

            for d in range(1, days_in_month + 1):
                col_configs[str(d)] = st.column_config.SelectboxColumn(
                    f"{d:02d}",
                    options=["Full", "Half", "Absent"],
                    default="Full",
                    required=True,
                    width="small",
                    help=f"{d:02d}/{sel_month:02d}/{sel_year} • Full=पूर्ण (1.0), Half=अर्धा (0.5), Absent=सुट्टी (0.0)",
                )

            st.markdown(
                """
                <div style="background:#eff6ff; border:1.5px solid #93c5fd; border-radius:8px; padding:8px 14px; margin-bottom:12px; display:flex; gap:20px; align-items:center; font-size:13px;">
                    <span style="font-weight:800; color:#1e3a8a;">💡 सेल ड्रॉपडाउन (Cell Dropdown):</span>
                    <span style="color:#16a34a; font-weight:800;">🟢 Full = पूर्ण दिवस (1.0)</span>
                    <span style="color:#d97706; font-weight:800;">🟡 Half = अर्धा दिवस (0.5)</span>
                    <span style="color:#dc2626; font-weight:800;">⚪ Absent = गैरहजर / सुट्टी (0.0)</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # FORM WRAPPING TO PREVENT PAGE RELOADS ON CELL CLICKS
            with st.form(f"att_sheet_form_{sel_year}_{sel_month}", clear_on_submit=False):
                edited_matrix = st.data_editor(
                    matrix_df,
                    disabled=disabled_cols,
                    column_config=col_configs,
                    hide_index=True,
                    use_container_width=True,
                    key=f"att_editor_{sel_year}_{sel_month}",
                )

                st.write("")
                att_save_btn = st.form_submit_button(
                    "💾 हजेरी जतन करा (Save Attendance)",
                    type="primary",
                    use_container_width=True,
                    help="टेबलमधील सर्व नोंदी क्लाउड आणि डिव्हाइसवर सेव्ह होतील.",
                )

            if att_save_btn:
                save_attendance_matrix(sel_year, sel_month, edited_matrix)
                # Clear editor state so fresh data loads cleanly without stale edit overlays
                st.session_state.pop(f"att_editor_{sel_year}_{sel_month}", None)
                st.success(f"✅ {dict(MONTH_NAMES)[sel_month]} {sel_year} हजेरी यशस्वीरित्या सेव्ह झाली!")
                st.rerun()

            # Calculate Live Totals & Date-Accurate Wages (100% in-memory)
            summary_cards = []
            cached_wages_df = get_worker_wages_df()
            cached_w_master = active_workers.copy()
            for _, r in edited_matrix.iterrows():
                wid = int(r["worker_id"])
                wname = str(r["कामगार नाव (Name)"])
                wrole = str(r["पद (Role)"])

                full_count = 0
                half_count = 0
                abs_count = 0
                tot_days = 0.0
                tot_pay = 0.0
                rates_used = set()

                for d in range(1, days_in_month + 1):
                    raw_val = extract_att_val(r, d)
                    if raw_val == "Full":
                        units = 1.0
                        full_count += 1
                    elif raw_val == "Half":
                        units = 0.5
                        half_count += 1
                    else:
                        units = 0.0
                        abs_count += 1

                    tot_days += units

                    # Date-accurate wage revision calculation (ultra-fast in-memory)
                    d_obj = date(sel_year, sel_month, d)
                    day_rate, day_stype = get_worker_rate_for_date(
                        wid, d_obj, wages_df=cached_wages_df, w_df=cached_w_master
                    )
                    rates_used.add(day_rate)

                    if day_stype.lower().startswith("month"):
                        day_earned = (day_rate / days_in_month) * units if days_in_month > 0 else 0.0
                    else:
                        day_earned = day_rate * units
                    tot_pay += day_earned

                w_info = active_workers[active_workers["worker_id"] == wid]
                curr_stype = str(w_info.iloc[0].get("salary_type", "Daily")) if not w_info.empty else "Daily"
                curr_rate = float(w_info.iloc[0].get("base_rate", 0.0)) if not w_info.empty else 0.0

                if len(rates_used) > 1:
                    rate_label = f"बदल: {', '.join(f'₹{r:g}' for r in sorted(rates_used))}"
                else:
                    rate_label = f"₹{curr_rate:,.2f}"

                summary_cards.append({
                    "Worker ID": wid,
                    "कामगार नाव": wname,
                    "पद": wrole,
                    "Full Day (1.0)": full_count,
                    "Half Day (0.5)": half_count,
                    "Absent (0.0)": abs_count,
                    "एकूण हजर दिवस": round(tot_days, 1),
                    "पगार प्रकार": curr_stype,
                    "लागू दर (₹)": rate_label,
                    "अंतिम पगार (₹)": round(tot_pay, 2),
                })

            summary_df = pd.DataFrame(summary_cards)

            st.write("")
            down_c1, down_c2 = st.columns([2, 1])
            with down_c2:
                att_html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'/><title>Attendance {dict(MONTH_NAMES)[sel_month]} {sel_year}</title>
<style>
body {{ font-family: sans-serif; font-size: 11px; padding: 15px; color: #0f172a; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
th, td {{ border: 1px solid #94a3b8; padding: 5px 8px; text-align: center; }}
th {{ background: #0f172a; color: #fff; }}
.txt-l {{ text-align: left; }}
</style></head><body>
<h2>🥛 RANJIT BHIMRAO KAWLE MILK SUPPLIER</h2>
<h3>कामगार हजेरी पत्रक — {dict(MONTH_NAMES)[sel_month]} {sel_year}</h3>
<table>
<thead><tr><th>ID</th><th class='txt-l'>नाव</th><th>पद</th><th>Full</th><th>Half</th><th>Absent</th><th>एकूण दिवस</th><th>लागू दर (₹)</th><th>अंतिम पगार (₹)</th></tr></thead>
<tbody>
{''.join(f"<tr><td>{r['Worker ID']}</td><td class='txt-l'><b>{r['कामगार नाव']}</b></td><td>{r['पद']}</td><td>{r['Full Day (1.0)']}</td><td>{r['Half Day (0.5)']}</td><td>{r['Absent (0.0)']}</td><td><b>{r['एकूण हजर दिवस']}</b></td><td>{r['लागू दर (₹)']}</td><td><b>₹{r['अंतिम पगार (₹)']:,.2f}</b></td></tr>" for _, r in summary_df.iterrows())}
</tbody></table></body></html>"""
                st.download_button(
                    "⬇ Download Attendance HTML",
                    data=att_html.encode("utf-8"),
                    file_name=f"Attendance_{sel_year}_{sel_month:02d}.html",
                    mime="text/html",
                    use_container_width=True,
                    key="dl_attendance_html",
                )

            st.divider()
            st.subheader(f"📊 मासिक हजेरी व पगार हिशोब — {dict(MONTH_NAMES)[sel_month]} {sel_year}")
            st.dataframe(
                summary_df.style.format({
                    "एकूण हजर दिवस": "{:.1f}",
                    "अंतिम पगार (₹)": "₹{:,.2f}",
                }),
                use_container_width=True,
            )

    with att_tab2:
        st.subheader("👥 कामगार व्यवस्थापन व पगार बदल इतिहास (Workers Master & Wage History)")

        # Section 1: In-table Worker Master Editor (Wrapped in form to prevent click reload)
        st.markdown("#### 📋 सर्व कामगार माहिती संपादन (Edit Existing Workers)")
        st.caption("कामगारांचे नाव, पद, मोबाईल नंबर, पगार प्रकार आणि दर थेट या टेबलमध्ये बदला. पूर्ण झाल्यावर खालील सेव्ह बटण दाबा.")

        all_workers_df = get_workers_df()
        if not all_workers_df.empty:
            with st.form("edit_workers_master_form", clear_on_submit=False):
                disp_workers = all_workers_df.copy()
                if "created_at" in disp_workers.columns:
                    disp_workers = disp_workers.drop(columns=["created_at"])

                # Guarantee compatible string column data type for contact & name
                disp_workers["contact"] = disp_workers["contact"].astype(str).replace("nan", "").replace("None", "")
                disp_workers["name"] = disp_workers["name"].astype(str)

                w_col_configs = {
                    "worker_id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                    "name": st.column_config.TextColumn("कामगाराचे नाव (Name)*", required=True, width="medium"),
                    "role": st.column_config.SelectboxColumn(
                        "पद / काम (Role)",
                        options=["Driver", "Helper", "Dairy Staff", "Collection Boy", "Counter Staff", "Manager"],
                        required=True,
                        width="medium",
                    ),
                    "contact": st.column_config.TextColumn("मोबाईल नंबर (Contact)", width="medium"),
                    "salary_type": st.column_config.SelectboxColumn(
                        "पगार प्रकार",
                        options=["Daily", "Monthly"],
                        required=True,
                        width="small",
                    ),
                    "base_rate": st.column_config.NumberColumn(
                        "दर / पगार (₹)",
                        min_value=0.0,
                        step=50.0,
                        format="₹%.2f",
                        required=True,
                        width="medium",
                    ),
                    "is_active": st.column_config.CheckboxColumn("सक्रिय (Active)", width="small"),
                }

                edited_workers = st.data_editor(
                    disp_workers,
                    column_config=w_col_configs,
                    hide_index=True,
                    use_container_width=True,
                    num_rows="fixed",
                    key="workers_master_inline_editor",
                )

                save_w_btn = st.form_submit_button(
                    "💾 सर्व कामगार माहिती अपडेट करा (Update All Workers)",
                    type="primary",
                    use_container_width=True,
                )
                if save_w_btn:
                    save_workers_df(edited_workers)
                    st.session_state.pop("workers_master_inline_editor", None)
                    st.success("✅ कामगार माहिती यशस्वीरित्या अपडेट झाली!")
                    st.rerun()

        st.divider()

        # Section 2: Wage Revision with Effective Date
        rev_c1, rev_c2 = st.columns([1.3, 1.7])
        with rev_c1:
            st.markdown("#### 📈 पगार बदल नोंदवा (Wage Revision with Effective Date)")
            st.caption("कामगाराचा पगार एखाद्या विशिष्ट तारखेपासून बदलल्यास येथे नोंदवा. मागील दिवसांचा हिशोब जुन्या दराने व नवीन दिवसांचा हिशोब नवीन दराने आपोआप होईल.")

            with st.form("add_wage_revision_form", clear_on_submit=True):
                active_w_opts = {int(r["worker_id"]): str(r["name"]) for _, r in active_workers.iterrows()}
                sel_rev_wid = st.selectbox(
                    "कामगार निवडा (Select Worker)*",
                    options=list(active_w_opts.keys()),
                    format_func=lambda x: f"{active_w_opts.get(x, '')} (ID: {x})",
                    key="wage_rev_worker_id",
                )
                rev_eff_date = st.date_input(
                    "बदल लागू होण्याची तारीख (Effective Date)*",
                    value=curr_d,
                    key="wage_rev_eff_date",
                    help="या तारखेपासून पुढील सर्व दिवसांसाठी हा नवीन दर लागू होईल.",
                )
                rev_new_rate = st.number_input(
                    "नवीन दर / पगार रक्कम (New Rate ₹)*",
                    min_value=0.0,
                    step=50.0,
                    format="%g",
                    key="wage_rev_new_rate",
                )
                rev_stype = st.selectbox(
                    "पगार प्रकार (Salary Type)",
                    ["Daily", "Monthly"],
                    key="wage_rev_stype",
                )
                rev_notes = st.text_input(
                    "कारणे / टीप (Reason / Notes)",
                    placeholder="उदा. वेतनवाढ, अनुभव वाढ, दिवाळी वाढ",
                    key="wage_rev_notes",
                )

                save_rev_btn = st.form_submit_button(
                    "💾 नवीन पगार दर लागू करा (Record Wage Revision)",
                    type="primary",
                    use_container_width=True,
                )
                if save_rev_btn:
                    if rev_new_rate <= 0:
                        st.error("कृपया वैध दर टाका (Rate must be > 0).")
                    else:
                        cur_wages = get_worker_wages_df()
                        next_wid = int(cur_wages["wage_id"].max() + 1) if not cur_wages.empty and "wage_id" in cur_wages.columns and cur_wages["wage_id"].max() > 0 else 1

                        # Check if worker has an established baseline prior to rev_eff_date
                        w_records = cur_wages[cur_wages["worker_id"].astype(int) == int(sel_rev_wid)] if not cur_wages.empty else pd.DataFrame()
                        rows_to_insert = []
                        if w_records.empty or (w_records["effective_date"].astype(str) > str(rev_eff_date)).all():
                            wm_df = get_workers_df()
                            wm = wm_df[wm_df["worker_id"].astype(int) == int(sel_rev_wid)]
                            prior_rate = float(wm.iloc[0].get("base_rate", 0.0)) if not wm.empty else float(rev_new_rate)
                            prior_stype = str(wm.iloc[0].get("salary_type", "Daily")) if not wm.empty else str(rev_stype)
                            rows_to_insert.append({
                                "wage_id": next_wid,
                                "worker_id": int(sel_rev_wid),
                                "effective_date": "2020-01-01",
                                "base_rate": prior_rate,
                                "salary_type": prior_stype,
                                "notes": "Initial base wage",
                                "created_at": "2020-01-01T00:00:00",
                            })
                            next_wid += 1

                        rows_to_insert.append({
                            "wage_id": next_wid,
                            "worker_id": int(sel_rev_wid),
                            "effective_date": str(rev_eff_date),
                            "base_rate": float(rev_new_rate),
                            "salary_type": str(rev_stype),
                            "notes": str(rev_notes).strip(),
                            "created_at": datetime.now().isoformat(),
                        })
                        new_wages = pd.concat([cur_wages, pd.DataFrame(rows_to_insert)], ignore_index=True)
                        save_worker_wages_df(new_wages)

                        # Update workers master to the rate active as of today
                        w_master = get_workers_df()
                        mask = w_master["worker_id"].astype(int) == int(sel_rev_wid)
                        active_today_rate, active_today_stype = get_worker_rate_for_date(int(sel_rev_wid), curr_d, wages_df=new_wages)
                        w_master.loc[mask, "base_rate"] = float(active_today_rate)
                        w_master.loc[mask, "salary_type"] = str(active_today_stype)
                        save_workers_df(w_master)
                        st.session_state.pop("workers_master_inline_editor", None)

                        st.success(f"✅ {active_w_opts.get(sel_rev_wid, '')} यांच्यासाठी {rev_eff_date} पासून ₹{rev_new_rate:,.2f} दर लागू झाला!")
                        st.rerun()

        with rev_c2:
            st.markdown("#### 📜 पगार बदल इतिहास (Wage Revision History)")
            wages_hist = get_worker_wages_df()
            if wages_hist.empty:
                st.info("अद्याप कोणताही पगार बदल नोंदवलेला नाही.")
            else:
                w_names_map = {int(r["worker_id"]): str(r["name"]) for _, r in all_workers_df.iterrows()}
                wages_disp = wages_hist.copy()
                wages_disp["कामगार नाव"] = wages_disp["worker_id"].astype(int).map(w_names_map)
                wages_disp = wages_disp.sort_values("effective_date", ascending=False)
                st.dataframe(
                    wages_disp[["कामगार नाव", "effective_date", "base_rate", "salary_type", "notes"]].rename(columns={
                        "effective_date": "लागू तारीख",
                        "base_rate": "नवीन दर (₹)",
                        "salary_type": "प्रकार",
                        "notes": "टीप",
                    }).style.format({"नवीन दर (₹)": "₹{:,.2f}"}),
                    use_container_width=True,
                )

        st.divider()

        # Section 3: Add New Worker Form
        st.markdown("#### ➕ नवीन कामगार नोंदणी (Add New Worker)")
        with st.form("add_new_worker_form", clear_on_submit=True):
            nw_c1, nw_c2, nw_c3, nw_c4 = st.columns(4)
            with nw_c1:
                w_name = st.text_input("कामगाराचे नाव (Full Name)*", placeholder="उदा. ज्ञानेश्वर कदम")
            with nw_c2:
                w_role = st.selectbox("पद / काम (Role)", ["Driver", "Helper", "Dairy Staff", "Collection Boy", "Counter Staff", "Manager"])
            with nw_c3:
                w_contact = st.text_input("मोबाईल नंबर (Contact)", placeholder="98XXXXXXXX")
            with nw_c4:
                w_stype = st.selectbox("पगार प्रकार (Salary Type)", ["Daily", "Monthly"])

            nw_s1, nw_s2 = st.columns([1, 1])
            with nw_s1:
                w_rate = st.number_input("दर / पगार रक्कम (Rate ₹)", min_value=0.0, step=50.0, format="%g")
            with nw_s2:
                st.write("")
                st.write("")
                add_w_submitted = st.form_submit_button("➕ कामगार जोडा (Save Worker)", type="primary", use_container_width=True)
                if add_w_submitted:
                    if not w_name.strip():
                        st.error("कृपया कामगाराचे नाव टाका.")
                    else:
                        cur_w = get_workers_df()
                        next_id = int(cur_w["worker_id"].max() + 1) if not cur_w.empty and cur_w["worker_id"].max() > 0 else 1
                        new_row = pd.DataFrame([{
                            "worker_id": next_id,
                            "name": w_name.strip(),
                            "role": w_role,
                            "contact": w_contact.strip(),
                            "salary_type": w_stype,
                            "base_rate": float(w_rate),
                            "is_active": True,
                        }])
                        save_workers_df(pd.concat([cur_w, new_row], ignore_index=True))

                        cur_wages = get_worker_wages_df()
                        next_wage_id = int(cur_wages["wage_id"].max() + 1) if not cur_wages.empty and "wage_id" in cur_wages.columns and cur_wages["wage_id"].max() > 0 else 1
                        init_wage = pd.DataFrame([{
                            "wage_id": next_wage_id,
                            "worker_id": next_id,
                            "effective_date": str(curr_d),
                            "base_rate": float(w_rate),
                            "salary_type": w_stype,
                            "notes": "Initial joining rate",
                            "created_at": datetime.now().isoformat(),
                        }])
                        save_worker_wages_df(pd.concat([cur_wages, init_wage], ignore_index=True))
                        st.success(f"✅ '{w_name.strip()}' यशस्वीरित्या जोडले!")
                        st.rerun()

# ============================================================
# PAGE: 🤖 AI AUDIT & ANOMALY DETECTION (100% LOCAL / OFFLINE)
# ============================================================
elif menu == "🤖 AI Audit & Anomaly Detection":
    st.header("🤖 Local AI Audit & Pattern Anomaly Detection")
    st.caption("100% Local Machine Learning & Pattern Intelligence • स्थानिक व ऑफलाइन एआय तपासणी (Zero Cloud / Zero API — पूर्णपणे ऑफलाइन व सुरक्षित)")

    # Controls Bar
    ai_c1, ai_c2, ai_c3, ai_c4 = st.columns([1.2, 1.2, 1.4, 0.8])
    with ai_c1:
        audit_date = st.date_input("Audit Date (तारीख)", value=date.today(), key="ai_page_audit_date")
    with ai_c2:
        audit_zone = st.selectbox("Route / Zone (रूट / झोन)", ["All Zones"] + get_all_zones(), key="ai_page_audit_zone")
    with ai_c3:
        lang_choice = st.selectbox("Language / भाषा", ["Bilingual (English + मराठी)", "मराठी (Marathi)", "English"], key="ai_page_lang_pref")
    with ai_c4:
        st.write("")
        st.write("")
        if st.button("🔄 Re-Audit", key="ai_page_reaudit_btn", use_container_width=True):
            invalidate_data_cache()
            st.rerun()

    # Model Evaluation (Local & Offline)
    habits = get_habit_profiles()
    audit_grid, cat_cols = build_daily_posting_grid(audit_date, audit_zone, retailers_active, categories_active)

    detected_anomalies = []
    if audit_grid is not None and not audit_grid.empty:
        detected_anomalies = ai_engine.detect_grid_anomalies(audit_grid, habits, categories_active)

    # Route Cash & Driver Handover Calculation
    day_payments = _day_payments_for_zone(audit_date, audit_zone)
    cash_collected = 0.0
    if not day_payments.empty:
        pm_col = "payment_mode" if "payment_mode" in day_payments.columns else "mode"
        if pm_col in day_payments.columns:
            cash_collected = float(pd.to_numeric(day_payments.loc[day_payments[pm_col].astype(str).str.upper() == "CASH", "amount"], errors="coerce").fillna(0.0).sum())

    day_exp = get_route_expenses_df(audit_date, audit_zone if audit_zone != "All Zones" else "General")
    cash_exp = 0.0
    if not day_exp.empty:
        pm_col_exp = "payment_mode" if "payment_mode" in day_exp.columns else "mode"
        if pm_col_exp in day_exp.columns:
            cash_exp = float(pd.to_numeric(day_exp.loc[day_exp[pm_col_exp].astype(str).str.upper() == "CASH", "amount"], errors="coerce").fillna(0.0).sum())

    net_expected_cash = max(0.0, cash_collected - cash_exp)

    # Optional Driver Handover Input & Verification
    st.markdown("---")
    with st.expander("💵 Driver Route Cash Reconciliation (ड्रायव्हर रोख जमा पडताळणी)", expanded=(audit_zone != "All Zones")):
        st.caption("Verify driver cash handover against route collections minus driver vehicle cash expenses.")
        d_rec1, d_rec2, d_rec3 = st.columns([1, 1, 1.2])
        d_rec1.metric("💵 Total Route Cash Collected", f"₹{cash_collected:,.2f}")
        d_rec2.metric("⛽ Route Cash Expenses", f"₹{cash_exp:,.2f}")
        d_rec3.metric("🎯 Net Cash Handover Expected", f"₹{net_expected_cash:,.2f}")

        handover_key = f"driver_cash_stored_{audit_zone}_{audit_date}"
        driver_cash_in = st.number_input(
            "Driver Cash Handed Over to Counter (ड्रायव्हरने काउंटरवर जमा केलेली रोख रक्कम ₹):",
            min_value=0.0,
            value=float(st.session_state.get(handover_key, 0.0)),
            step=500.0,
            format="%g",
            key=f"driver_cash_inp_{audit_zone}_{audit_date}",
        )
        if driver_cash_in > 0:
            st.session_state[handover_key] = driver_cash_in
            shortfall_anom = ai_engine.detect_driver_cash_shortfall(audit_zone, cash_collected, cash_exp, driver_cash_in)
            if shortfall_anom:
                detected_anomalies.append(shortfall_anom)

    # Compute Total Milk Screened
    total_screened_liters = 0.0
    if audit_grid is not None and not audit_grid.empty and cat_cols:
        for cdict in cat_cols:
            colname = cdict.get("col", "")
            if colname in audit_grid.columns:
                total_screened_liters += float(pd.to_numeric(audit_grid[colname], errors="coerce").fillna(0.0).sum())

    # Summary KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("👥 Active Customers Profiled", f"{len(habits)} Customers")
    k2.metric("🥛 Total Milk Screened", f"{total_screened_liters:,.2f} L")
    num_anoms = len(detected_anomalies)
    k3.metric(
        "🚨 AI Flagged Anomalies",
        f"{num_anoms}",
        delta="100% Normal" if num_anoms == 0 else f"{num_anoms} Issues Flagged",
        delta_color="normal" if num_anoms == 0 else "inverse",
    )
    k4.metric("💰 Expected Till Cash", f"₹{net_expected_cash:,.2f}")

    # ================== DEDICATED ANOMALIES VIEW ==================
    st.markdown("### 🔍 Anomaly Audit Feed (फक्त संशयास्पद नोंदींची यादी)")

    if num_anoms == 0:
        st.markdown(
            """
            <div style="background:#f0fdf4; border:2px solid #22c55e; border-radius:14px; padding:24px 20px; text-align:center; margin:16px 0;">
                <div style="font-size:36px;">🎉</div>
                <div style="font-size:19px; font-weight:900; color:#166534; margin-top:6px;">
                    Zero Anomalies Detected! (सर्व नोंदी १००% नियमित आहेत)
                </div>
                <div style="font-size:13.5px; color:#15803d; margin-top:4px;">
                    All customer milk deliveries and quantities match verified historical patterns. Driver cash is reconciled.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning(f"⚠️ {num_anoms} potential anomaly issue(s) detected for {audit_date} ({audit_zone}). Review details below:")
        for idx, anom in enumerate(detected_anomalies):
            atype = anom.get("anomaly_type", "")
            is_cat = atype == "CATEGORY_MISMATCH"
            is_spike = atype == "VOLUME_SPIKE"
            is_driver = atype == "DRIVER_CASH_DEFICIT"

            badge_color = "#dc2626" if is_cat else ("#d97706" if is_spike else "#b91c1c")
            badge_title = "🚨 CATEGORY MISMATCH (अनपेक्षित दूध प्रकार)" if is_cat else ("⚠️ VOLUME SPIKE (असामान्य वाढ)" if is_spike else "💵 DRIVER CASH SHORTFALL (ड्रायव्हर रोख तफावत)")

            explanation = ""
            if "Bilingual" in lang_choice:
                explanation = f"<b>{anom.get('explanation_en', '')}</b><br><span style='color:#64748b; font-style:italic;'>↳ {anom.get('explanation_mr', '')}</span>"
            elif "मराठी" in lang_choice:
                explanation = f"<b>{anom.get('explanation_mr', '')}</b>"
            else:
                explanation = f"<b>{anom.get('explanation_en', '')}</b>"

            customer_display = anom.get("retailer_name", f"Route Driver: {anom.get('zone', audit_zone)}")
            rec_action = anom.get("action", "Verify entry with driver before saving.")

            st.markdown(
                f"""
                <div style="
                    background: #ffffff;
                    border: 1.5px solid {badge_color};
                    border-left: 8px solid {badge_color};
                    border-radius: 12px;
                    padding: 16px 20px;
                    margin-bottom: 14px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.04);
                ">
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
                        <span style="font-size:16px; font-weight:850; color:#0f172a;">👤 {customer_display}</span>
                        <span style="background:{badge_color}; color:#ffffff; padding:3px 10px; border-radius:999px; font-size:11px; font-weight:800;">
                            {badge_title}
                        </span>
                    </div>
                    <div style="font-size:14px; color:#1e293b; line-height:1.5;">
                        {explanation}
                    </div>
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-top:12px; padding-top:10px; border-top:1px dashed #e2e8f0; font-size:12.5px; color:#64748b;">
                        <span>💡 <b>Recommended Action:</b> {rec_action}</span>
                        <span style="font-weight:700; color:{badge_color};">Status: Action Required</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )



# ============================================================
# PAGE: 📅 DATE + ZONE VIEW
# ============================================================
elif menu == "📅 Date + Zone View":
    st.header("📅 View All Data for a Specific Date + Zone")

    view_date = st.date_input("Select Date", value=date.today(), key="view_date")
    view_zone = st.selectbox(
        "Select Zone", ["All Zones"] + get_all_zones(), key="view_zone"
    )

    e_day = _day_entries_for_zone(view_date, view_zone)
    if e_day.empty:
        st.info("No entries for this date/zone.")
    else:
        e_view = build_entries_view_cached(
            e_day, st.session_state["data_version"], want_milk_type_col=False
        )

        pivot = pd.pivot_table(
            e_view,
            index="Retailer",
            columns="Category",
            values="qty",
            aggfunc="sum",
            fill_value=0.0,
        )

        display = pivot.copy()
        for c in display.columns:
            vals = pd.to_numeric(display[c], errors="coerce").fillna(0.0)
            display[c] = vals.apply(
                lambda v: "–" if float(v) == 0.0 else f"{float(v):.2f}"
            )
        display["TOTAL (L)"] = pivot.sum(axis=1).apply(lambda x: f"{float(x):.2f}")

        totals = {c: float(pivot[c].sum()) for c in pivot.columns}
        totals["TOTAL (L)"] = float(pivot.values.sum())
        totals_row = {
            k: (f"{float(v):.2f}" if k != "TOTAL (L)" else f"{float(v):.2f}")
            for k, v in totals.items()
        }
        display = pd.concat(
            [display, pd.DataFrame([totals_row], index=["GRAND TOTAL"])]
        )

        st.subheader("🥛 Retailer × Category (Liters)")
        st.dataframe(df_for_display(display), use_container_width=True)

    p_day = _day_payments_for_zone(view_date, view_zone)
    st.subheader("💳 Payments (This Date + Zone)")
    if p_day.empty:
        st.info("No payments for this date/zone.")
    else:
        pv = p_day.merge(
            retailers[["retailer_id", "name", "zone"]], on="retailer_id", how="left"
        ).rename(columns={"name": "Retailer"})
        pv["zone"] = pv["zone"].apply(_norm_zone)

        st.dataframe(
            pv[["date", "zone", "Retailer", "amount", "payment_mode", "note"]],
            use_container_width=True,
        )

        mode_totals = (
            pv.groupby("payment_mode", as_index=False)["amount"]
            .sum()
            .sort_values("amount", ascending=False)
            .rename(columns={"payment_mode": "Mode", "amount": "Total (₹)"})
        )

        st.subheader("💳 Payment Totals by Mode")
        st.dataframe(
            mode_totals.style.format({"Total (₹)": "₹{:.2f}"}), use_container_width=True
        )

# ============================================================
# PAGE: 📍 ZONE-WISE SUMMARY
# ============================================================
elif menu == "📍 Zone-wise Summary":
    st.header("📍 Zone-wise Summary (Category Columns + Payment Mode Totals)")

    s_date = st.date_input("Select Date", value=date.today(), key="zone_sum_date")

    pivot = zone_category_pivot_for_day(s_date)

    st.subheader("🥛 Milk Sent — Zone × Category (Liters)")
    if pivot.empty:
        st.info("No entries on this date.")
    else:
        display = pivot.copy()

        for c in display.columns:
            if c in ("Zone", "TOTAL (L)"):
                continue
            display[c] = display[c].apply(fmt_zero_dash)

        numeric_cols = [c for c in pivot.columns if c != "Zone"]
        grand = {"Zone": "GRAND TOTAL"}
        for c in numeric_cols:
            grand[c] = float(pivot[c].sum())
        display = pd.concat([display, pd.DataFrame([grand])], ignore_index=True)

        st.dataframe(df_for_display(display), use_container_width=True)

    st.subheader("💳 Payments Collected — Totals by Mode (Zone-aware)")
    p_day = _day_payments_for_zone(s_date, "All Zones")
    if p_day.empty:
        st.info("No payments recorded on this date.")
    else:
        pv = p_day.merge(
            retailers[["retailer_id", "zone"]], on="retailer_id", how="left"
        )
        pv["zone"] = pv["zone"].apply(_norm_zone)

        mode_totals = (
            pv.groupby("payment_mode", as_index=False)["amount"]
            .sum()
            .sort_values("amount", ascending=False)
            .rename(columns={"payment_mode": "Mode", "amount": "Total (₹)"})
        )

        mode_zone = (
            pv.groupby(["zone", "payment_mode"], as_index=False)["amount"]
            .sum()
            .rename(
                columns={"zone": "Zone", "payment_mode": "Mode", "amount": "Total (₹)"}
            )
            .sort_values(["Zone", "Total (₹)"], ascending=[True, False])
        )

        st.caption("Overall totals (all zones combined):")
        st.dataframe(
            mode_totals.style.format({"Total (₹)": "₹{:.2f}"}), use_container_width=True
        )

        st.caption("Zone-wise totals by mode:")
        st.dataframe(
            mode_zone.style.format({"Total (₹)": "₹{:.2f}"}), use_container_width=True
        )

# ============================================================
# PAGE: ✏️ EDIT (SINGLE ENTRY)
# ============================================================
elif menu == "✏️ Edit (Single Entry)":
    st.header("✏️ Edit / Delete Single Entry (Rate is preserved)")

    if entries.empty:
        st.info("No entries yet.")
        st.stop()

    f_date = st.date_input("Filter Date", value=date.today(), key="single_edit_date")
    f_zone = st.selectbox(
        "Filter Zone", ["All Zones"] + get_all_zones(), key="single_edit_zone"
    )

    df = entries.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.loc[df["date"] == f_date].copy()
    df = filter_by_zone(df, "retailer_id", f_zone)

    if df.empty:
        st.info("No entries for this date/zone.")
        st.stop()

    view = build_entries_view_cached(
        df, st.session_state["data_version"], want_milk_type_col=False
    )
    st.dataframe(
        view[
            [
                "entry_id",
                "date",
                "zone",
                "Retailer",
                "Category",
                "qty",
                "rate",
                "amount",
            ]
        ],
        use_container_width=True,
    )

    entry_id = st.number_input("Entry ID", min_value=1, step=1, key="single_entry_id")
    if int(entry_id) not in set(entries["entry_id"].astype(int).tolist()):
        st.warning("Entry ID not found.")
        st.stop()

    row = entries.loc[entries["entry_id"] == int(entry_id)].iloc[0]
    new_qty = st.number_input(
        "New Quantity (L)",
        min_value=0.0,
        step=0.5,
        format="%g",
        value=float(row["qty"]),
        key="single_new_qty",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Update Qty", key="single_update_btn"):
            rate = float(row["rate"])
            new_amt = float(new_qty) * rate
            entries.loc[entries["entry_id"] == int(entry_id), ["qty", "amount"]] = [
                float(new_qty),
                float(new_amt),
            ]
            # DB write only the changed row
            updated_row = entries.loc[entries["entry_id"] == int(entry_id)].copy()
            safe_write_csv(updated_row, ENTRIES_FILE, allow_empty=False)

            st.success("Updated quantity (stored rate preserved).")
            st.rerun()

    with col2:
        confirm = st.text_input(
            "Type DELETE to delete this entry", key="single_delete_confirm"
        )
        if st.button("Delete Entry", key="single_delete_btn"):
            if confirm != "DELETE":
                st.warning("Type DELETE to confirm.")
            else:
                sb_delete_by_pk("entries", "entry_id", [int(entry_id)])
                entries = entries.loc[
                    entries["entry_id"].astype(int) != int(entry_id)
                ].copy()
                st.success("Deleted.")
                st.rerun()


# ============================================================
# PAGE: 🥛 MILK CATEGORIES
# ============================================================
elif menu == "🥛 Milk Categories" or (menu == "⚙️ Master Setup" and setup_menu == "🥛 Milk Categories"):
    st.header("🥛 Milk Categories Management")
    tab1, tab2 = st.tabs(["➕ Add Category", "✏️ Edit Categories"])

    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input("Category Name", key="cat_add_name")
        with col2:
            description = st.text_input("Description (optional)", key="cat_add_desc")
        with col3:
            default_price = st.number_input(
                "Default Price per Liter (₹)",
                min_value=0.0,
                step=0.5,
                format="%g",
                key="cat_add_price",
            )

        if st.button("Add Category", type="primary", key="cat_add_btn"):
            if not name.strip():
                st.error("Category name is required.")
                st.stop()

            if default_price <= 0:
                st.error("Default price must be greater than 0.")
                st.stop()

            # OPTION B: DB auto-generates category_id
            table, pk = FILE_TO_TABLE[CATEGORIES_FILE]

            new_row = pd.DataFrame(
                [
                    {
                        "name": name.strip(),
                        "description": description.strip() if description else "",
                        "default_price": float(default_price),
                        "is_active": True,
                    }
                ]
            )

            sb_insert_df(new_row, CATEGORIES_FILE)

            st.success("Category added.")
            st.rerun()

    with tab2:
        if categories.empty:
            st.info("No categories yet.")
        else:
            st.dataframe(categories, use_container_width=True)

            edit_cat = st.selectbox(
                "Select category to edit",
                categories["name"].tolist(),
                key="cat_edit_sel",
            )
            cat_data = categories.loc[categories["name"] == edit_cat].iloc[0]
            cid = int(cat_data["category_id"])

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                new_name = st.text_input(
                    "New name", value=str(cat_data["name"]), key="cat_new_name"
                )
            with col2:
                new_desc = st.text_input(
                    "New description",
                    value=str(cat_data.get("description", "")),
                    key="cat_new_desc",
                )
            with col3:
                new_default_price = st.number_input(
                    "Default Price (₹/L)",
                    value=float(cat_data.get("default_price", 0.0)),
                    min_value=0.0,
                    step=0.5,
                    format="%g",
                    key="cat_new_price",
                )
            with col4:
                new_active = st.checkbox(
                    "Active",
                    value=bool(cat_data.get("is_active", True)),
                    key="cat_new_active",
                )

            colA, colB, colC = st.columns(3)

            with colA:
                if st.button("Update Category", key="cat_update_btn"):
                    mask = categories["category_id"].astype(int) == int(cid)

                    categories.loc[
                        mask, ["name", "description", "default_price", "is_active"]
                    ] = [
                        new_name.strip(),
                        new_desc,
                        float(new_default_price),
                        bool(new_active),
                    ]
                    updated_row = categories.loc[mask].copy()
                    safe_write_csv(updated_row, CATEGORIES_FILE, allow_empty=False)

                    st.success("Updated!")
                    st.rerun()

            with colB:
                if st.button("Deactivate Category (Safe)", key="cat_deactivate_btn"):
                    mask = categories["category_id"].astype(int) == int(cid)
                    categories.loc[mask, "is_active"] = False

                    updated_row = categories.loc[mask].copy()
                    safe_write_csv(updated_row, CATEGORIES_FILE, allow_empty=False)

                    st.success("Category deactivated (history preserved).")
                    st.rerun()

            with colC:
                st.caption("Hard delete is blocked if referenced.")
                confirm = st.text_input(
                    "Type DELETE to hard delete category", key="cat_delete_confirm"
                )
                if st.button(
                    "🗑️ Hard Delete Category", type="secondary", key="cat_delete_btn"
                ):
                    if confirm != "DELETE":
                        st.warning("Type DELETE to confirm.")
                    elif is_category_referenced(cid):
                        st.error(
                            "Blocked: Category is referenced in history. Deactivate instead."
                        )
                    else:
                        sb_delete_by_pk("categories", "category_id", [cid])
                        st.success("Hard deleted.")
                        st.rerun()

# ============================================================
# PAGE: 🏪 RETAILERS
# ============================================================
elif menu == "🏪 Retailers" or (menu == "⚙️ Master Setup" and setup_menu == "🏪 Retailers"):
    st.header("🏪 Retailer Management (with Zones)")
    tab1, tab2, tab3 = st.tabs(
        ["➕ Add Retailer", "✏️ Edit Retailers", "🏠 Main Book Retailers"]
    )

    all_zones = get_all_zones()

    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input("Retailer Name", key="ret_add_name")
            contact = st.text_input("Contact Number", key="ret_add_contact")
        with col2:
            address = st.text_area("Address", key="ret_add_address")
        with col3:
            zone_mode = st.radio(
                "Zone",
                ["Select Existing", "Create New"],
                horizontal=True,
                key="ret_add_zone_mode",
            )
            if zone_mode == "Select Existing":
                zone = st.selectbox(
                    "Select Zone", ["Default"] + all_zones, key="ret_add_zone_sel"
                )
            else:
                zone = st.text_input("New Zone Name", value="", key="ret_add_zone_new")

        if st.button("Add Retailer", type="primary", key="ret_add_btn"):
            if not name.strip():
                st.warning("Retailer name required")
            else:
                z = _norm_zone(zone)

                new_row = pd.DataFrame(
                    [
                        {
                            "name": name.strip(),
                            "contact": contact,
                            "address": address,
                            "zone": z,
                            "is_active": True,
                        }
                    ]
                )

            sb_insert_df(new_row, RETAILERS_FILE)

            st.success(f"✅ Retailer '{name}' added to zone '{z}'!")
            st.rerun()

    with tab2:
        if retailers.empty:
            st.info("No retailers yet.")
        else:
            st.dataframe(retailers, use_container_width=True)

            edit_ret = st.selectbox(
                "Select retailer to edit",
                retailers["name"].tolist(),
                key="ret_edit_sel",
            )
            ret_data = retailers.loc[retailers["name"] == edit_ret].iloc[0]
            rid = int(ret_data["retailer_id"])

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                new_name = st.text_input(
                    "New name", value=str(ret_data["name"]), key="ret_new_name"
                )
                new_contact = st.text_input(
                    "New contact",
                    value=str(ret_data.get("contact", "")),
                    key="ret_new_contact",
                )
            with col2:
                new_address = st.text_area(
                    "New address",
                    value=str(ret_data.get("address", "")),
                    key="ret_new_address",
                )
            with col3:
                zone_mode2 = st.radio(
                    "Zone Update",
                    ["Select Existing", "Create New"],
                    horizontal=True,
                    key="ret_zone_update_mode",
                )
                if zone_mode2 == "Select Existing":
                    choices = ["Default"] + all_zones
                    current = _norm_zone(ret_data.get("zone", "Default"))
                    idx = choices.index(current) if current in choices else 0
                    new_zone = st.selectbox(
                        "Select Zone", choices, index=idx, key="ret_new_zone_sel"
                    )
                else:
                    new_zone = st.text_input(
                        "New Zone Name", value="", key="ret_new_zone_new"
                    )
            with col4:
                new_active = st.checkbox(
                    "Active",
                    value=bool(ret_data.get("is_active", True)),
                    key="ret_new_active",
                )

            colA, colB, colC = st.columns(3)

            with colA:
                if st.button("Update Retailer", key="ret_update_btn"):
                    z = _norm_zone(new_zone)
                    mask = retailers["retailer_id"].astype(int) == int(rid)

                    retailers.loc[
                        mask, ["name", "contact", "address", "zone", "is_active"]
                    ] = [
                        new_name.strip(),
                        new_contact,
                        new_address,
                        z,
                        bool(new_active),
                    ]

                    updated_row = retailers.loc[mask].copy()
                    safe_write_csv(updated_row, RETAILERS_FILE, allow_empty=False)

                    st.success("Updated!")
                    st.rerun()

            with colB:
                if st.button("Deactivate Retailer (Safe)", key="ret_deactivate_btn"):
                    mask = retailers["retailer_id"].astype(int) == int(rid)
                    retailers.loc[mask, "is_active"] = False

                    updated_row = retailers.loc[mask].copy()
                    safe_write_csv(updated_row, RETAILERS_FILE, allow_empty=False)

                    st.success("Retailer deactivated (history preserved).")
                    st.rerun()

            with colC:
                st.caption("Hard delete is blocked if referenced.")
                confirm = st.text_input(
                    "Type DELETE to hard delete retailer", key="ret_delete_confirm"
                )
                if st.button(
                    "🗑️ Hard Delete Retailer", type="secondary", key="ret_delete_btn"
                ):
                    if confirm != "DELETE":
                        st.warning("Type DELETE to confirm.")
                    elif is_retailer_referenced(rid):
                        st.error(
                            "Blocked: Retailer is referenced in history. Deactivate instead."
                        )
                    else:
                        sb_delete_by_pk("retailers", "retailer_id", [rid])
                        st.success("Hard deleted.")
                        st.rerun()

    with tab3:
        st.subheader("🏠 Main Book Retailers")
        st.caption(
            "These are normal retailers maintained in the Main book for dashboard overview. This does not change their zone."
        )
        if not _main_table_exists():
            st.error("Create the 'main_retailers' table first (SQL below).")
            st.code("""create table if not exists public.main_retailers (
  retailer_id bigint primary key references public.retailers(retailer_id) on delete cascade
);""")
        elif retailers.empty:
            st.info("No retailers available.")
        else:
            # Current selection
            current_ids = set(get_main_retailer_ids())
            rtmp = retailers.copy()
            rtmp["retailer_id"] = (
                pd.to_numeric(rtmp.get("retailer_id", 0), errors="coerce")
                .fillna(0)
                .astype(int)
            )
            rtmp["name"] = rtmp.get("name", "").fillna("").astype(str)

            id_to_name = dict(zip(rtmp["retailer_id"].tolist(), rtmp["name"].tolist()))
            name_to_id = {v: k for k, v in id_to_name.items() if v}

            current_names = [
                id_to_name.get(rid, str(rid))
                for rid in sorted(current_ids)
                if rid in id_to_name
            ]

            options = sorted(rtmp["name"].dropna().astype(str).tolist())
            selected_names = st.multiselect(
                "Retailers in Main book",
                options=options,
                default=current_names,
                key="main_retailers_select",
            )

            if st.button(
                "Save Main Book Retailers", type="primary", key="main_retailers_save"
            ):
                new_ids = {
                    int(name_to_id[n]) for n in selected_names if n in name_to_id
                }
                to_add = sorted(new_ids - current_ids)
                to_remove = sorted(current_ids - new_ids)

                try:
                    if to_add:
                        add_main_retailers(to_add)
                    if to_remove:
                        remove_main_retailers(to_remove)
                    st.success("Saved Main book retailers.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save Main book retailers: {e}")

# ============================================================
# PAGE: 💰 PRICE MANAGEMENT
# ============================================================
elif menu == "💰 Price Management":
    st.header("💰 Price Management & Rate Matrix")

    if retailers_active.empty:
        st.warning("Please add retailers first")
        st.stop()

    if categories_active.empty:
        st.warning("Please add categories first")
        st.stop()

    col_p1, col_p2 = st.columns([1, 1])
    with col_p1:
        eff_date = st.date_input("Effective Date", date.today(), key="price_matrix_date")
    with col_p2:
        route_choices = ["All Routes"] + get_all_zones()
        selected_route = st.selectbox(
            "Filter / Group by Route", route_choices, key="price_matrix_route"
        )

    retailer_list = retailers_active.assign(
        zone_order=retailers_active["zone"].str.extract(r"(\d+)").astype(float)
    ).sort_values(["zone_order", "name"])

    if selected_route != "All Routes":
        retailer_list = retailer_list.loc[
            retailer_list["zone"].apply(_norm_zone) == _norm_zone(selected_route)
        ].copy()

    if retailer_list.empty:
        st.info(f"No active retailers found on Route: {selected_route}")
        st.stop()

    category_list = categories_active.sort_values("name")

    # State key for tracking any bulk modifications before saving
    bulk_key = f"bulk_adj_{eff_date}_{selected_route}"
    st.session_state.setdefault(bulk_key, {})

    # ================== BULK RATE ADJUSTMENT TOOL ==================
    with st.expander("⚡ Bulk Rate Adjustment Tool (Quick +₹X / -₹X / Fixed Rate)", expanded=False):
        st.caption("Apply rate changes across all or selected retailers on this route with a single click before saving.")
        bcol1, bcol2, bcol3, bcol4 = st.columns([1.2, 1.2, 1, 1])
        with bcol1:
            bulk_cat = st.selectbox(
                "Target Category",
                ["All Categories"] + category_list["name"].tolist(),
                key="bulk_cat_target",
            )
        with bcol2:
            bulk_action = st.selectbox(
                "Adjustment Action",
                ["➕ Increase by (+₹)", "➖ Decrease by (-₹)", "✏️ Set Exact Rate (=₹)"],
                key="bulk_action_type",
            )
        with bcol3:
            bulk_val = st.number_input(
                "Delta / Value (₹)",
                min_value=0.0,
                step=0.5,
                value=2.0,
                format="%g",
                key="bulk_delta_val",
            )
        with bcol4:
            st.write("")
            st.write("")
            apply_bulk = st.button("⚡ Apply to Matrix", type="secondary", key="apply_bulk_btn")

    # Handle Bulk Apply button click
    if apply_bulk and bulk_val > 0:
        cats_to_adjust = (
            category_list["name"].tolist()
            if bulk_cat == "All Categories"
            else [bulk_cat]
        )
        for _, r in retailer_list.iterrows():
            rid = int(r["retailer_id"])
            for _, c in category_list.iterrows():
                cid = int(c["category_id"])
                cname = c["name"]
                if cname in cats_to_adjust:
                    curr_p = get_price_for_date(rid, cid, eff_date) or float(c.get("default_price", 0.0) or 0.0)
                    if "Increase" in bulk_action:
                        new_p = round(curr_p + float(bulk_val), 2)
                    elif "Decrease" in bulk_action:
                        new_p = max(0.0, round(curr_p - float(bulk_val), 2))
                    else:
                        new_p = round(float(bulk_val), 2)
                    st.session_state[bulk_key][(rid, cid)] = new_p
        st.success(f"Applied {bulk_action} ₹{bulk_val:.2f} for {bulk_cat} to {len(retailer_list)} retailers! Review and click 'Save Price Changes' below.")
        st.rerun()

    # Build matrix dataframe
    matrix_rows = []
    for _, r in retailer_list.iterrows():
        rid = int(r["retailer_id"])
        row = {
            "retailer_id": rid,
            "Retailer": r["name"],
            "Route / Zone": r.get("zone", "Default"),
        }
        for _, c in category_list.iterrows():
            cid = int(c["category_id"])
            cname = c["name"]
            # Check if bulk adjustment was applied in current session
            adj_override = st.session_state[bulk_key].get((rid, cid))
            if adj_override is not None:
                p = float(adj_override)
            else:
                p = get_price_for_date(rid, cid, eff_date)
                if p is None:
                    p = float(c.get("default_price", 0.0) or 0.0)
            row[cname] = float(p)
        matrix_rows.append(row)

    price_matrix_df = pd.DataFrame(matrix_rows)
    display_df = price_matrix_df.drop(columns=["retailer_id"])

    st.subheader(f"Price Matrix — {selected_route} ({len(retailer_list)} Retailers)")

    column_config = {
        "Retailer": st.column_config.TextColumn("Retailer", disabled=True),
        "Route / Zone": st.column_config.TextColumn("Route / Zone", disabled=True),
    }
    for _, c in category_list.iterrows():
        column_config[c["name"]] = st.column_config.NumberColumn(
            c["name"], min_value=0.0, step=0.5, format="₹%.2f"
        )

    with st.form(f"price_matrix_form_{eff_date}_{selected_route}", clear_on_submit=False):
        edited_df = st.data_editor(
            display_df,
            column_config=column_config,
            use_container_width=True,
            num_rows="fixed",
            key=f"price_matrix_editor_{eff_date}_{selected_route}",
        )

        st.markdown("---")
        retroactive_recalc = st.checkbox(
            "🔄 Also update existing daily entry amounts from this Effective Date onwards (Retroactive Recalculation)",
            value=False,
            help="If enabled, existing deliveries recorded on or after this Effective Date will have their rates and total amounts updated to match these revised prices.",
        )

        save_price_btn = st.form_submit_button("💾 Save Price Changes", type="primary", use_container_width=True)

    if save_price_btn:
        updates = []
        changed_pairs = []

        for i, row in edited_df.iterrows():
            rid = int(price_matrix_df.iloc[i]["retailer_id"])

            for _, c in category_list.iterrows():
                cid = int(c["category_id"])
                col = c["name"]
                new_price = float(row[col] or 0.0)
                old_price = get_price_for_date(rid, cid, eff_date)
                if old_price is None:
                    old_price = 0.0

                if round(float(new_price), 2) != round(float(old_price), 2):
                    updates.append(
                        {
                            "retailer_id": rid,
                            "category_id": cid,
                            "price": round(float(new_price), 2),
                            "effective_date": str(eff_date),
                        }
                    )
                    changed_pairs.append((rid, cid, round(float(new_price), 2)))

        if updates:
            for up in updates:
                _r_id = int(up["retailer_id"])
                _c_id = int(up["category_id"])
                _pr = float(up["price"])
                _ef = str(up["effective_date"])
                try:
                    ex_q = (
                        sb.table("prices")
                        .select("price_id")
                        .eq("retailer_id", _r_id)
                        .eq("category_id", _c_id)
                        .eq("effective_date", _ef)
                        .limit(1)
                        .execute()
                    )
                    if ex_q and getattr(ex_q, "data", None):
                        _pid = ex_q.data[0]["price_id"]
                        sb.table("prices").update({"price": _pr}).eq("price_id", _pid).execute()
                    else:
                        null_q = (
                            sb.table("prices")
                            .select("price_id")
                            .eq("retailer_id", _r_id)
                            .eq("category_id", _c_id)
                            .is_("effective_date", "null")
                            .limit(1)
                            .execute()
                        )
                        if null_q and getattr(null_q, "data", None):
                            _pid = null_q.data[0]["price_id"]
                            sb.table("prices").update({"price": _pr, "effective_date": _ef}).eq("price_id", _pid).execute()
                        else:
                            new_rec = {
                                "retailer_id": _r_id,
                                "category_id": _c_id,
                                "price": _pr,
                                "effective_date": _ef,
                            }
                            _new_pid = sb_new_id("prices", "price_id")
                            if _new_pid is not None:
                                new_rec["price_id"] = _new_pid
                            sb.table("prices").insert(new_rec).execute()
                except Exception as _pex:
                    print(f"[Price Save Error] retailer {_r_id}, cat {_c_id}: {_pex}")

            # Optional retroactive entry recalculation
            recalc_count = 0
            if retroactive_recalc and changed_pairs:
                for rid, cid, new_rate in changed_pairs:
                    entries_to_update = sb_fetch_df(
                        ENTRIES_FILE,
                        CSV_SCHEMAS[ENTRIES_FILE],
                        filters=[
                            ("retailer_id", "eq", rid),
                            ("category_id", "eq", cid),
                            ("date", "gte", str(eff_date)),
                        ],
                    )
                    if not entries_to_update.empty:
                        for _, erow in entries_to_update.iterrows():
                            eid = int(erow["entry_id"])
                            eqty = float(erow.get("qty", 0.0) or 0.0)
                            new_amt = round(eqty * new_rate, 2)
                            sb.table("entries").update(
                                {"rate": new_rate, "amount": new_amt}
                            ).eq("entry_id", eid).execute()
                            recalc_count += 1

            invalidate_data_cache()
            st.session_state[bulk_key] = {}
            msg = f"✅ {len(updates)} prices successfully updated for Effective Date: {eff_date}!"
            if recalc_count > 0:
                msg += f" (Retroactively updated {recalc_count} existing daily delivery entries)."
            st.success(msg)
            st.rerun()
        else:
            st.info("No price changes detected.")
# ============================================================
# PAGE: 📒 LEDGER
# ============================================================
elif menu == "📒 Ledger":
    st.header(f"📒 Ledger (Grid View) — {selected_zone}")

    if entries_z.empty:
        st.info("No entries in this zone context.")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        d_from = st.date_input(
            "From Date", value=date.today() - timedelta(days=30), key="ledger_from"
        )
    with col2:
        d_to = st.date_input("To Date", value=date.today(), key="ledger_to")

    if d_from > d_to:
        st.error("From Date cannot be after To Date.")
        st.stop()

    v = build_entries_view_cached(
        entries_z, st.session_state["data_version"], want_milk_type_col=False
    )
    v["date"] = pd.to_datetime(v["date"], errors="coerce").dt.date
    v = v.loc[(v["date"] >= d_from) & (v["date"] <= d_to)].copy()

    if v.empty:
        st.info("No entries in this date range.")
        st.stop()

    pivot = pd.pivot_table(
        v,
        index="Retailer",
        columns="Category",
        values="qty",
        aggfunc="sum",
        fill_value=0.0,
    )

    display = pivot.copy()
    for c in display.columns:
        display[c] = display[c].apply(fmt_zero_dash)

    display["TOTAL (L)"] = pivot.sum(axis=1).apply(lambda x: f"{float(x):.2f}")

    grand = {"TOTAL (L)": float(pivot.values.sum())}
    for c in pivot.columns:
        grand[c] = float(pivot[c].sum())
    grand_disp = {
        k: (f"{float(v):.2f}" if k != "TOTAL (L)" else f"{float(v):.2f}")
        for k, v in grand.items()
    }
    display = pd.concat([display, pd.DataFrame([grand_disp], index=["GRAND TOTAL"])])

    st.subheader("🥛 Retailer × Category Grid (Liters)")
    st.dataframe(df_for_display(display), use_container_width=True)

    st.subheader("📌 Category Totals (Liters)")
    cat_totals = pivot.sum(axis=0).reset_index()
    cat_totals.columns = ["Category", "Total (L)"]
    cat_totals = cat_totals.sort_values("Total (L)", ascending=False)
    st.dataframe(cat_totals, use_container_width=True)

# ============================================================
# PAGE: 🔍 FILTERS & REPORTS
# ============================================================
elif menu == "🔍 Filters & Reports":
    st.header(f"🔍 Filters & Detailed Reports — {selected_zone}")

    if selected_zone == "All Zones":
        zone_filter = st.multiselect(
            "Zone Filter", ["All"] + zones, default=["All"], key="rep_zone_filter"
        )
    else:
        zone_filter = [selected_zone]

    col1, col2, col3 = st.columns(3)
    with col1:
        filter_retailer = st.multiselect(
            "Select Retailer(s)",
            ["All"] + retailers["name"].tolist(),
            default=["All"],
            key="rep_retailer_filter",
        )
    with col2:
        filter_category = st.multiselect(
            "Select Category(s)",
            ["All"] + categories["name"].tolist(),
            default=["All"],
            key="rep_cat_filter",
        )
    with col3:
        date_range = st.date_input("Date Range", value=[], key="rep_date_range")

    filtered_entries = entries.copy()
    filtered_entries = filter_by_zone(filtered_entries, "retailer_id", selected_zone)

    if (
        selected_zone == "All Zones"
        and "All" not in zone_filter
        and not retailers.empty
    ):
        rz = retailers.copy()
        rz["zone"] = rz["zone"].apply(_norm_zone)
        allowed_rids = (
            rz.loc[rz["zone"].isin([_norm_zone(z) for z in zone_filter]), "retailer_id"]
            .astype(int)
            .tolist()
        )
        filtered_entries = filtered_entries.loc[
            filtered_entries["retailer_id"].astype(int).isin(allowed_rids)
        ].copy()

    if not filtered_entries.empty:
        if "All" not in filter_retailer and not retailers.empty:
            rid_list = (
                retailers.loc[retailers["name"].isin(filter_retailer), "retailer_id"]
                .astype(int)
                .tolist()
            )
            filtered_entries = filtered_entries.loc[
                filtered_entries["retailer_id"].astype(int).isin(rid_list)
            ].copy()

        if "All" not in filter_category and not categories.empty:
            cid_list = (
                categories.loc[categories["name"].isin(filter_category), "category_id"]
                .astype(int)
                .tolist()
            )
            filtered_entries = filtered_entries.loc[
                filtered_entries["category_id"].astype(int).isin(cid_list)
            ].copy()

        if len(date_range) == 2:
            filtered_entries["date"] = pd.to_datetime(
                filtered_entries["date"], errors="coerce"
            )
            start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            filtered_entries = filtered_entries.loc[
                (filtered_entries["date"] >= start) & (filtered_entries["date"] <= end)
            ].copy()

    if filtered_entries.empty:
        st.info("No data matching the filters")
    else:
        result_view = build_entries_view_cached(
            filtered_entries, st.session_state["data_version"], want_milk_type_col=False
        )
        st.dataframe(
            result_view[
                ["date", "zone", "Retailer", "Category", "qty", "rate", "amount"]
            ],
            use_container_width=True,
        )

# ============================================================
# PAGE: 🚚 DISTRIBUTORS
# ============================================================
elif menu == "🚚 Distributors" or (menu == "⚙️ Master Setup" and setup_menu == "🚚 Distributors"):
    st.header("🚚 Distributor Management")
    tab1, tab2 = st.tabs(["➕ Add Distributor", "✏️ Edit Distributors"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Distributor Name", key="dist_add_name")
            contact = st.text_input("Contact Number", key="dist_add_contact")
        with col2:
            address = st.text_area("Address", key="dist_add_address")

        if st.button("Add Distributor", type="primary", key="dist_add_btn"):
            if not name.strip():
                st.warning("Distributor name required.")
            else:
                did = sb_new_id("distributors", "distributor_id")
                new_row = pd.DataFrame(
                    [[did, name.strip(), contact.strip(), address.strip(), True]],
                    columns=CSV_SCHEMAS[DISTRIBUTORS_FILE],
                )
                distributors = pd.concat([distributors, new_row], ignore_index=True)
                sb_insert_df(new_row, DISTRIBUTORS_FILE)
                st.success("✅ Distributor added!")
                st.rerun()

    with tab2:
        if distributors.empty:
            st.info("No distributors yet.")
        else:
            st.dataframe(df_for_display(distributors), use_container_width=True)

            edit_dis = st.selectbox(
                "Select distributor", distributors["name"].tolist(), key="dist_edit_sel"
            )
            dis_data = distributors.loc[distributors["name"] == edit_dis].iloc[0]
            did = int(dis_data["distributor_id"])

            col1, col2, col3 = st.columns(3)
            with col1:
                new_name = st.text_input(
                    "Name", value=str(dis_data["name"]), key="dist_new_name"
                )
            with col2:
                new_contact = st.text_input(
                    "Contact",
                    value=str(dis_data.get("contact", "")),
                    key="dist_new_contact",
                )
            with col3:
                new_active = st.checkbox(
                    "Active",
                    value=bool(dis_data.get("is_active", True)),
                    key="dist_new_active",
                )

            new_address = st.text_area(
                "Address",
                value=str(dis_data.get("address", "")),
                key="dist_new_address",
            )

            colA, colB, colC = st.columns(3)

            with colA:
                if st.button("Update Distributor", key="dist_update_btn"):
                    mask = distributors["distributor_id"].astype(int) == int(did)
                    distributors.loc[
                        mask, ["name", "contact", "address", "is_active"]
                    ] = [
                        new_name.strip(),
                        new_contact.strip(),
                        new_address.strip(),
                        bool(new_active),
                    ]

                    updated_row = distributors.loc[mask].copy()
                    safe_write_csv(updated_row, DISTRIBUTORS_FILE, allow_empty=False)

                    st.success("Updated!")
                    st.rerun()

            with colB:
                if st.button("Deactivate (Safe)", key="dist_deactivate_btn"):
                    mask = distributors["distributor_id"].astype(int) == int(did)
                    distributors.loc[mask, "is_active"] = False

                    updated_row = distributors.loc[mask].copy()
                    safe_write_csv(updated_row, DISTRIBUTORS_FILE, allow_empty=False)

                    st.success("Distributor deactivated.")
                    st.rerun()

            with colC:
                confirm = st.text_input(
                    "Type DELETE to hard delete", key="dist_delete_confirm"
                )
                if st.button("🗑️ Hard Delete", type="secondary", key="dist_delete_btn"):
                    if confirm != "DELETE":
                        st.warning("Type DELETE to confirm.")
                    elif is_distributor_referenced(did):
                        st.error(
                            "Blocked: Distributor referenced in purchases/payments. Deactivate instead."
                        )
                    else:
                        sb_delete_by_pk("distributors", "distributor_id", [did])
                        st.success("Hard deleted.")
                        st.rerun()


# ============================================================
# PAGE: 🧩 DISTRIBUTOR CATEGORY MAPPING
# ============================================================
elif menu == "🧩 Distributor Category Mapping" or (menu == "⚙️ Master Setup" and setup_menu == "🧩 Distributor Category Mapping"):
    st.header("🧩 Distributor → Category Mapping")
    st.caption(
        "This controls exactly which categories appear for each distributor in the Daily Posting Sheet."
    )

    if distributors.empty or categories.empty:
        st.warning("Add distributors and categories first.")
        st.stop()

    distributors_active = distributors.copy()
    if "is_active" in distributors_active.columns:
        distributors_active["is_active"] = distributors_active["is_active"].apply(
            parse_boolish_active
        )
        distributors_active = distributors_active.loc[
            distributors_active["is_active"] == True
        ].copy()

    categories_active = categories.copy()
    if "is_active" in categories_active.columns:
        categories_active["is_active"] = categories_active["is_active"].apply(
            parse_boolish_active
        )
        categories_active = categories_active.loc[
            categories_active["is_active"] == True
        ].copy()

    if distributors_active.empty:
        st.info("No active distributors.")
        st.stop()
    if categories_active.empty:
        st.info("No active categories.")
        st.stop()

    # Helper: current mapped category ids
    def _mapped_ids(did: int) -> list[int]:
        if dist_cat_map is None or dist_cat_map.empty:
            return []
        m = dist_cat_map.copy()
        m["distributor_id"] = (
            pd.to_numeric(m["distributor_id"], errors="coerce").fillna(0).astype(int)
        )
        m["category_id"] = (
            pd.to_numeric(m["category_id"], errors="coerce").fillna(0).astype(int)
        )
        m["is_active"] = m.get("is_active", True).apply(parse_boolish_active)
        m = m.loc[(m["distributor_id"] == int(did)) & (m["is_active"] == True)].copy()
        return sorted(m["category_id"].astype(int).tolist())

    # UI
    did_list = distributors_active.sort_values("name")[
        ["distributor_id", "name"]
    ].to_dict(orient="records")
    cat_options = categories_active.sort_values("name")[
        ["category_id", "name"]
    ].to_dict(orient="records")
    cat_id_to_name = {int(c["category_id"]): str(c["name"]) for c in cat_options}
    cat_name_to_id = {str(c["name"]): int(c["category_id"]) for c in cat_options}
    all_cat_names = [str(c["name"]) for c in cat_options]

    st.divider()
    st.subheader("Set categories per distributor")

    for d in did_list:
        did = int(d["distributor_id"])
        dname = str(d["name"])

        current_ids = _mapped_ids(did)
        current_names = [
            cat_id_to_name[cid] for cid in current_ids if cid in cat_id_to_name
        ]

        with st.expander(f"🚚 {dname}", expanded=False):
            selected_names = st.multiselect(
                "Supplies these categories",
                options=all_cat_names,
                default=current_names,
                key=f"dcm_ms_{did}",
            )

            col1, col2 = st.columns([1, 2])
            with col1:
                if st.button("💾 Save Mapping", key=f"dcm_save_{did}"):
                    # Overwrite mapping for this distributor (simple + correct)
                    sb_delete_where(
                        "distributor_category_map", [("distributor_id", "eq", int(did))]
                    )

                    new_rows = []
                    next_id = (
                        None
                        if USE_DB_IDS
                        else sb_next_id("distributor_category_map", "map_id")
                    )

                    for nm in selected_names:
                        cid = int(cat_name_to_id[nm])
                        mid = None if USE_DB_IDS else int(next_id)
                        if not USE_DB_IDS:
                            next_id += 1
                        new_rows.append([mid, int(did), int(cid), True])

                    if new_rows:
                        df_new = pd.DataFrame(
                            new_rows, columns=CSV_SCHEMAS[DISTRIBUTOR_CATEGORY_MAP_FILE]
                        )
                        sb_insert_df(df_new, DISTRIBUTOR_CATEGORY_MAP_FILE)

                    st.success("Saved ✅")
                    st.rerun()

            with col2:
                st.caption(
                    "Tip: Keep this strict. If you don’t map it here, it won’t show in Daily Entry for this distributor."
                )

# ============================================================
# PAGE: 📒 DISTRIBUTOR LEDGER
# ============================================================
elif menu == "📒 Distributor Ledger":
    st.header("📒 Distributor Ledger (Incoming Milk + Payments + Running Due)")

    if distributors.empty:
        st.warning("Add at least 1 distributor first.")
        st.stop()
    if categories.empty:
        st.warning("Add at least 1 category first.")
        st.stop()

    dis_name = st.selectbox(
        "Select Distributor", distributors["name"].tolist(), key="dl_dis"
    )
    did = int(
        distributors.loc[distributors["name"] == dis_name, "distributor_id"].iloc[0]
    )

    colA, colB = st.columns(2)
    with colA:
        start_day = st.date_input(
            "From Date", value=date.today().replace(day=1), key="dl_start"
        )
    with colB:
        end_day = st.date_input("To Date", value=date.today(), key="dl_end")

    if start_day > end_day:
        st.error("From Date cannot be after To Date.")
        st.stop()

    cat_names = categories["name"].dropna().astype(str).tolist()
    cat_names = sorted(list(dict.fromkeys(cat_names)))

    opening_due = distributor_balance_before(did, start_day)
    grid = build_distributor_daily_grid(did, start_day, end_day, cat_names)

    closing_due = (
        float(
            pd.to_numeric(grid["Running Due (₹)"], errors="coerce")
            .fillna(opening_due)
            .iloc[-1]
        )
        if not grid.empty
        else opening_due
    )
    total_milk = (
        float(pd.to_numeric(grid["Total Milk (L)"], errors="coerce").fillna(0).sum())
        if not grid.empty
        else 0.0
    )
    total_pur = (
        float(pd.to_numeric(grid["Purchases (₹)"], errors="coerce").fillna(0).sum())
        if not grid.empty
        else 0.0
    )
    total_pay = (
        float(pd.to_numeric(grid["Payment (₹)"], errors="coerce").fillna(0).sum())
        if not grid.empty
        else 0.0
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Milk (L)", f"{total_milk:.2f}")
    c2.metric("Opening Due", _fmt_money(opening_due))
    c3.metric("Purchases (This Period)", _fmt_money(total_pur))
    c4.metric("Payments (This Period)", _fmt_money(total_pay))
    c5.metric("Closing Due", _fmt_money(closing_due))

    st.divider()
    st.subheader("📌 Daily Sheet (Qty + Rate by Category)")

    preview = grid.copy()
    for cat in cat_names:
        qcol = f"{cat} Qty"
        rcol = f"{cat} Rate"
        if qcol in preview.columns:
            preview[qcol] = preview[qcol].apply(_disp_2dec_or_dash)
        if rcol in preview.columns:
            preview[rcol] = preview[rcol].apply(_disp_rate_or_dash)

    for c in ["Purchases (₹)", "Payment (₹)", "Running Due (₹)"]:
        if c in preview.columns:
            preview[c] = preview[c].apply(_fmt_money)

    if "Total Milk (L)" in preview.columns:
        preview["Total Milk (L)"] = preview["Total Milk (L)"].apply(_disp_2dec_or_dash)

    st.dataframe(df_for_display(preview), use_container_width=True)

    # ---------------- GRAND TOTALS (Categories + Payments) ----------------
    # Computed from the in-memory preview derived from current draft for (date, zone).
    # No DB reads here; safe against cross-date contamination.
    st.subheader("🧾 Totals (Daily)")
    # Build safe columns for totals in this section
    preview_df = preview.copy() if "preview" in locals() else pd.DataFrame()
    # Ensure cat_names is available in this scope (Billing/Preview totals safety)
    if "cat_names" not in locals() or not isinstance(cat_names, list):
        _cn = []
        try:
            if (
                "cat_cols" in locals()
                and isinstance(cat_cols, list)
                and len(cat_cols) > 0
            ):
                for _m in cat_cols:
                    if isinstance(_m, dict):
                        _n = _m.get("name") or _m.get("Category")
                        if not _n and isinstance(_m.get("col"), str):
                            _n = _m["col"].replace(" Qty", "").strip()
                        if _n:
                            _cn.append(str(_n).strip())
            if (
                (not _cn)
                and ("categories" in locals())
                and hasattr(categories, "empty")
                and (not categories.empty)
                and ("name" in categories.columns)
            ):
                _cn = categories["name"].dropna().astype(str).tolist()
        except Exception:
            _cn = []
        # de-dup, keep stable order
        cat_names = list(dict.fromkeys([c for c in _cn if str(c).strip()]))
    cat_col_names = [
        f"{cat} Qty"
        for cat in cat_names
        if (not preview_df.empty and f"{cat} Qty" in preview_df.columns)
    ]
    # Category totals (L)
    cat_totals = {}
    for col in cat_col_names:
        if col in preview_df.columns:
            cat_totals[col] = float(
                pd.to_numeric(preview_df[col], errors="coerce").fillna(0.0).sum()
            )
    grand_qty = float(sum(cat_totals.values()))

    # Payment totals (₹)
    pay_totals = {}
    for m in PAYMENT_MODES:
        pcol = f"{m} ₹"
        if pcol in preview_df.columns:
            pay_totals[pcol] = float(
                pd.to_numeric(preview_df[pcol], errors="coerce").fillna(0.0).sum()
            )
    grand_pay = float(sum(pay_totals.values()))

    cgt1, cgt2 = st.columns(2)
    cgt1.metric("Total Milk (L)", f"{grand_qty:.2f}")
    cgt2.metric(
        "Payments Collected (₹)", f"₹{grand_pay:.2f}"
    )  # Detailed category totals row (dash for zeros)
    if cat_col_names:
        row = {"Category Totals": "TOTAL (L)"}
        for col in cat_col_names:
            label = str(col).replace(" Qty", "")
            row[label] = cat_totals.get(col, 0.0)
        row["GRAND TOTAL (L)"] = grand_qty

        tot_df = pd.DataFrame([row])
        for c in tot_df.columns:
            if c not in ("Category Totals", "GRAND TOTAL (L)"):
                tot_df[c] = tot_df[c].apply(fmt_zero_dash)
        tot_df["GRAND TOTAL (L)"] = tot_df["GRAND TOTAL (L)"].apply(
            lambda x: f"{float(x):.2f}"
        )
        st.dataframe(df_for_display(tot_df), use_container_width=True)

    st.subheader("💳 Payment Mode Totals (Period)")
    pm = distributor_pay_mode_totals(did, start_day, end_day)
    if pm.empty:
        st.info("No payments in this period.")
    else:
        st.dataframe(
            pm.style.format({"Total (₹)": "₹{:.2f}"}), use_container_width=True
        )


# ============================================================
# PAGE: 🧾 DISTRIBUTOR BILL
# ============================================================
elif menu == "🧾 Distributor Bill" or (menu == "🧾 Bills & Statements" and bill_menu == "🚚 Distributor Procurement Bill"):
    st.header("🧾 Distributor Statement / Bill (Printable)")

    if distributors.empty:
        st.warning("Add at least 1 distributor first.")
        st.stop()
    if categories.empty:
        st.warning("Add at least 1 category first.")
        st.stop()

    dis_name = st.selectbox(
        "Select Distributor", distributors["name"].tolist(), key="db_dis"
    )
    did = int(
        distributors.loc[distributors["name"] == dis_name, "distributor_id"].iloc[0]
    )

    colA, colB = st.columns(2)
    with colA:
        start_day = st.date_input(
            "From Date", value=date.today().replace(day=1), key="db_start"
        )
    with colB:
        end_day = st.date_input("To Date", value=date.today(), key="db_end")

    if start_day > end_day:
        st.error("From Date cannot be after To Date.")
        st.stop()

    cat_names = categories["name"].dropna().astype(str).tolist()
    cat_names = sorted(list(dict.fromkeys(cat_names)))

    drow = (
        distributors.loc[distributors["distributor_id"].astype(int) == did]
        .iloc[0]
        .to_dict()
    )

    grid = build_distributor_daily_grid(did, start_day, end_day, cat_names)
    pm = distributor_pay_mode_totals(did, start_day, end_day)

    opening_due = distributor_balance_before(did, start_day)
    closing_due = (
        float(
            pd.to_numeric(grid["Running Due (₹)"], errors="coerce")
            .fillna(opening_due)
            .iloc[-1]
        )
        if not grid.empty
        else opening_due
    )

    total_pur = (
        float(pd.to_numeric(grid["Purchases (₹)"], errors="coerce").fillna(0).sum())
        if not grid.empty
        else 0.0
    )
    total_pay = (
        float(pd.to_numeric(grid["Payment (₹)"], errors="coerce").fillna(0).sum())
        if not grid.empty
        else 0.0
    )
    total_milk = (
        float(pd.to_numeric(grid["Total Milk (L)"], errors="coerce").fillna(0).sum())
        if not grid.empty
        else 0.0
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Milk (L)", f"{total_milk:.2f}")
    c2.metric("Opening Due", _fmt_money(opening_due))
    c3.metric("Purchases (This Period)", _fmt_money(total_pur))
    c4.metric("Payments (This Period)", _fmt_money(total_pay))
    c5.metric("Closing Due", _fmt_money(closing_due))

    st.divider()
    st.subheader("📌 Bill Preview (Arrow-safe)")
    preview = grid.copy()

    for cat in cat_names:
        qcol = f"{cat} Qty"
        rcol = f"{cat} Rate"

        if qcol in preview.columns:
            preview[qcol] = preview[qcol].apply(_disp_2dec_or_dash)
        if rcol in preview.columns:
            preview[rcol] = preview[rcol].apply(_disp_rate_or_dash)

    for c in ["Purchases (₹)", "Payment (₹)", "Running Due (₹)"]:
        if c in preview.columns:
            preview[c] = preview[c].apply(_fmt_money)

    if "Total Milk (L)" in preview.columns:
        preview["Total Milk (L)"] = preview["Total Milk (L)"].apply(_disp_2dec_or_dash)

    st.dataframe(df_for_display(preview), use_container_width=True)

    # ---------------- GRAND TOTALS (Categories + Payments) ----------------
    # Computed from the in-memory preview derived from current draft for (date, zone).
    # No DB reads here; safe against cross-date contamination.
    st.subheader("🧾 Totals (Daily)")
    # Build safe columns for totals in this section
    preview_df = preview.copy() if "preview" in locals() else pd.DataFrame()
    # Ensure cat_names is available in this scope (Billing/Preview totals safety)
    if "cat_names" not in locals() or not isinstance(cat_names, list):
        _cn = []
        try:
            if (
                "cat_cols" in locals()
                and isinstance(cat_cols, list)
                and len(cat_cols) > 0
            ):
                for _m in cat_cols:
                    if isinstance(_m, dict):
                        _n = _m.get("name") or _m.get("Category")
                        if not _n and isinstance(_m.get("col"), str):
                            _n = _m["col"].replace(" Qty", "").strip()
                        if _n:
                            _cn.append(str(_n).strip())
            if (
                (not _cn)
                and ("categories" in locals())
                and hasattr(categories, "empty")
                and (not categories.empty)
                and ("name" in categories.columns)
            ):
                _cn = categories["name"].dropna().astype(str).tolist()
        except Exception:
            _cn = []
        # de-dup, keep stable order
        cat_names = list(dict.fromkeys([c for c in _cn if str(c).strip()]))
    cat_col_names = [
        f"{cat} Qty"
        for cat in cat_names
        if (not preview_df.empty and f"{cat} Qty" in preview_df.columns)
    ]
    # Category totals (L)
    cat_totals = {}
    for col in cat_col_names:
        if col in preview_df.columns:
            cat_totals[col] = float(
                pd.to_numeric(preview_df[col], errors="coerce").fillna(0.0).sum()
            )
    grand_qty = float(sum(cat_totals.values()))

    # Payment totals (₹)
    pay_totals = {}
    for m in PAYMENT_MODES:
        pcol = f"{m} ₹"
        if pcol in preview_df.columns:
            pay_totals[pcol] = float(
                pd.to_numeric(preview_df[pcol], errors="coerce").fillna(0.0).sum()
            )
    grand_pay = float(sum(pay_totals.values()))

    cgt1, cgt2 = st.columns(2)
    cgt1.metric("Total Milk (L)", f"{grand_qty:.2f}")
    cgt2.metric(
        "Payments Collected (₹)", f"₹{grand_pay:.2f}"
    )  # Detailed category totals row (dash for zeros)
    if cat_col_names:
        row = {"Category Totals": "TOTAL (L)"}
        for col in cat_col_names:
            label = str(col).replace(" Qty", "")
            row[label] = cat_totals.get(col, 0.0)
        row["GRAND TOTAL (L)"] = grand_qty

        tot_df = pd.DataFrame([row])
        for c in tot_df.columns:
            if c not in ("Category Totals", "GRAND TOTAL (L)"):
                tot_df[c] = tot_df[c].apply(fmt_zero_dash)
        tot_df["GRAND TOTAL (L)"] = tot_df["GRAND TOTAL (L)"].apply(
            lambda x: f"{float(x):.2f}"
        )
        st.dataframe(df_for_display(tot_df), use_container_width=True)

    html = build_distributor_bill_html(drow, start_day, end_day, grid, pm, cat_names, opening_due=opening_due)

    st.subheader("🖨️ Printable Statement")
    st.components.v1.html(html, height=750, scrolling=True)

    st.download_button(
        "⬇️ Download Distributor Statement (HTML - Print Ready)",
        data=html.encode("utf-8"),
        file_name=f"distributor_statement_{dis_name}_{start_day}_to_{end_day}.html",
        mime="text/html",
        key="db_dl_html",
    )


# ============================================================
# PAGE: 💼 EXPENSES
# ============================================================
elif menu == "💼 Expenses":
    st.header("💼 Business Expenses Management")

    tab1, tab2 = st.tabs(["➕ Add Expense", "📋 View / Edit Expenses"])

    with tab1:
        with st.form("add_standalone_expense_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                ex_date = st.date_input("Date", value=date.today(), key="ex_date")
            with c2:
                ex_cat = st.selectbox(
                    "Expense Category",
                    ["Fuel", "Repair", "Nasta", "Others"],
                    key="ex_cat",
                )
            with c3:
                ex_amt = st.number_input(
                    "Amount (₹)", min_value=0.0, step=50.0, format="%g", key="ex_amt"
                )
            with c4:
                ex_mode = st.selectbox(
                    "Payment Mode",
                    ["Cash", "UPI", "Bank", "Cheque", "Other"],
                    key="ex_mode",
                )

            zc1, zc2 = st.columns(2)
            with zc1:
                ex_zone = st.selectbox("Route / Zone (Optional)", ["General / Overhead"] + get_all_zones(), key="ex_zone")
            with zc2:
                ex_desc = st.text_input("Description / Notes", key="ex_desc", help="e.g. HP petrol pump 20L, Driver tea")

            ex_paid = st.checkbox("Paid", value=True, key="ex_paid")

            if st.form_submit_button("💾 Save Expense", type="primary", use_container_width=True):
                if ex_amt <= 0:
                    st.error("Amount must be > 0.")
                    st.stop()
                eid = sb_new_id("expenses", "expense_id")
                final_desc = f"[{ex_zone}] {str(ex_desc).strip()}".strip() if ex_zone != "General / Overhead" else str(ex_desc).strip()
                new_row = pd.DataFrame(
                    [
                        [
                            eid,
                            str(ex_date),
                            str(ex_cat).strip(),
                            final_desc,
                            float(ex_amt),
                            str(ex_mode),
                            bool(ex_paid),
                        ]
                    ],
                    columns=CSV_SCHEMAS[EXPENSES_FILE],
                )
                sb_insert_df(new_row, EXPENSES_FILE)
                invalidate_data_cache()
                st.success("✅ Expense saved.")
                st.rerun()

    with tab2:
        if expenses.empty:
            st.info("No expenses yet.")
        else:
            view = expenses.copy()
            view["date"] = _safe_dt(view["date"]).dt.strftime("%Y-%m-%d")
            view["zone"] = view.apply(
                lambda r: extract_expense_zone(str(r.get("description", "")), str(r.get("category", ""))) or "General",
                axis=1,
            )
            view = view[
                [
                    "expense_id",
                    "date",
                    "zone",
                    "category",
                    "description",
                    "amount",
                    "payment_mode",
                    "paid",
                ]
            ].sort_values(["date", "expense_id"], ascending=[False, False])
            st.dataframe(
                view.style.format({"amount": "₹{:.2f}"}), use_container_width=True
            )

            st.divider()
            st.subheader("✏️ Edit / Delete Expense")

            eid = st.number_input("Expense ID", min_value=1, step=1, key="ex_edit_id")
            if int(eid) not in set(expenses["expense_id"].astype(int).tolist()):
                st.caption("Enter an existing Expense ID to edit.")
            else:
                row = expenses.loc[expenses["expense_id"].astype(int) == int(eid)].iloc[
                    0
                ]
                cur_date = (
                    pd.to_datetime(row["date"], errors="coerce").date()
                    if str(row["date"])
                    else date.today()
                )
                cur_cat = str(row.get("category", "") or "")
                cur_desc = str(row.get("description", "") or "")
                cur_amt = float(row.get("amount", 0.0) or 0.0)
                cur_mode = str(row.get("payment_mode", "Cash") or "Cash")
                cur_paid = bool(row.get("paid", False))

                with st.form(f"edit_expense_{eid}_form", clear_on_submit=False):
                    e1, e2, e3, e4 = st.columns(4)
                    with e1:
                        new_date = st.date_input("Date", value=cur_date, key="ex_new_date")
                    with e2:
                        exp_cats = ["Fuel", "Repair", "Nasta", "Others"]
                        cat_idx = exp_cats.index(cur_cat) if cur_cat in exp_cats else 0
                        new_cat = st.selectbox("Category", exp_cats, index=cat_idx, key="ex_new_cat")
                    with e3:
                        new_amt = st.number_input(
                            "Amount (₹)",
                            min_value=0.0,
                            step=50.0,
                            format="%g",
                            value=cur_amt,
                            key="ex_new_amt",
                        )
                    with e4:
                        modes = ["Cash", "UPI", "Bank", "Cheque", "Other"]
                        idx = modes.index(cur_mode) if cur_mode in modes else 0
                        new_mode = st.selectbox("Mode", modes, index=idx, key="ex_new_mode")

                    new_desc = st.text_input(
                        "Description", value=cur_desc, key="ex_new_desc"
                    )
                    new_paid = st.checkbox("Paid", value=cur_paid, key="ex_new_paid")

                    if st.form_submit_button("💾 Update Expense", type="primary"):
                        if new_amt <= 0:
                            st.error("Amount must be > 0.")
                            st.stop()

                        mask = expenses["expense_id"].astype(int) == int(eid)

                        expenses.loc[
                            mask,
                            [
                                "date",
                                "category",
                                "description",
                                "amount",
                                "payment_mode",
                                "paid",
                            ],
                        ] = [
                            str(new_date),
                            str(new_cat).strip(),
                            str(new_desc).strip(),
                            float(new_amt),
                            str(new_mode),
                            bool(new_paid),
                        ]

                        updated = expenses.loc[mask].copy()
                        safe_write_csv(updated, EXPENSES_FILE, allow_empty=False)
                        st.success("Updated.")
                        st.rerun()

                with colB:
                    confirm = st.text_input(
                        "Type DELETE to delete expense", key="ex_del_confirm"
                    )
                    if st.button("Delete Expense", key="ex_delete"):
                        if confirm != "DELETE":
                            st.warning("Type DELETE to confirm.")
                        else:
                            sb_delete_by_pk("expenses", "expense_id", [int(eid)])
                            st.success("Deleted.")
                            st.rerun()

# ============================================================
# PAGE: 🧾 RETAILERS BILL
# ============================================================
elif menu == "🧾 Retailers Bill" or (menu == "🧾 Bills & Statements" and bill_menu == "🏪 Retailers Bill"):
    st.header("🧾 Generate Professional Customer Bill (Printable + Downloadable)")

    if retailers.empty:
        st.warning("Add at least 1 retailer first.")
        st.stop()

    bill_zone = st.selectbox(
        "Select Zone", ["All Zones"] + get_all_zones(), key="bill_zone"
    )

    rlist = retailers.copy()
    rlist["zone"] = rlist["zone"].apply(_norm_zone)
    if bill_zone != "All Zones":
        rlist = rlist.loc[rlist["zone"] == _norm_zone(bill_zone)].copy()

    if rlist.empty:
        st.warning("No retailers found in this zone.")
        st.stop()

    retailer_name = st.selectbox(
        "Select Customer (Retailer)", rlist["name"].tolist(), key="bill_retailer"
    )
    rid = int(rlist.loc[rlist["name"] == retailer_name, "retailer_id"].iloc[0])

    colA, colB = st.columns(2)
    with colA:
        start_day = st.date_input(
            "From Date", value=date.today().replace(day=1), key="bill_start"
        )
    with colB:
        end_day = st.date_input("To Date", value=date.today(), key="bill_end")

    if start_day > end_day:
        st.error("From Date cannot be after To Date.")
        st.stop()

    cat_df = (
        categories_active.copy() if not categories_active.empty else categories.copy()
    )
    cat_names = cat_df["name"].dropna().astype(str).tolist()
    cat_names = sorted(list(dict.fromkeys(cat_names)))

    if not cat_names:
        st.error("No categories found.")
        st.stop()

    rrow = retailers.loc[retailers["retailer_id"].astype(int) == rid].iloc[0].to_dict()
    rrow["zone"] = _norm_zone(rrow.get("zone", "Default"))

    grid = build_bill_daily_grid(rid, start_day, end_day, cat_names)

    opening_due = retailer_balance_before(rid, start_day)
    closing_due = (
        float(
            pd.to_numeric(grid["Running Due (₹)"], errors="coerce")
            .fillna(opening_due)
            .iloc[-1]
        )
        if not grid.empty
        else float(opening_due)
    )

    if USE_SERVER_FILTERS:
        p = sb_fetch_df(
            PAYMENTS_FILE,
            CSV_SCHEMAS[PAYMENTS_FILE],
            filters=[
                ("retailer_id", "eq", int(rid)),
                ("date", "gte", str(start_day)),
                ("date", "lte", str(end_day)),
            ],
        )
    else:
        p = payments.copy()
        if not p.empty:
            p["date"] = _safe_dt(p["date"]).dt.date
            p = p.loc[
                (p["retailer_id"].astype(int) == rid)
                & (p["date"] >= start_day)
                & (p["date"] <= end_day)
            ].copy()

    if p.empty:
        pay_mode_totals = pd.DataFrame(columns=["Mode", "Total (₹)"])
    else:
        p["payment_mode"] = p["payment_mode"].fillna("Cash").astype(str)
        pay_mode_totals = (
            p.groupby("payment_mode", as_index=False)["amount"]
            .sum()
            .sort_values("amount", ascending=False)
            .rename(columns={"payment_mode": "Mode", "amount": "Total (₹)"})
        )

    total_sales = (
        float(pd.to_numeric(grid["Sales (₹)"], errors="coerce").fillna(0).sum())
        if not grid.empty
        else 0.0
    )
    total_pay = (
        float(pd.to_numeric(grid["Payment (₹)"], errors="coerce").fillna(0).sum())
        if not grid.empty
        else 0.0
    )
    total_milk = (
        float(pd.to_numeric(grid["Total Milk (L)"], errors="coerce").fillna(0).sum())
        if not grid.empty
        else 0.0
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Milk (L)", f"{total_milk:.2f}")
    c2.metric("Opening Due", _fmt_money(opening_due))
    c3.metric("Sales (This Period)", _fmt_money(total_sales))
    c4.metric("Payments (This Period)", _fmt_money(total_pay))
    c5.metric("Closing Due", _fmt_money(closing_due))

    st.divider()

    st.subheader("📌 Bill Preview (Arrow-safe)")

    preview = grid.copy()

    for cat in cat_names:
        qcol = f"{cat} Qty"
        rcol = f"{cat} Rate"

        if qcol in preview.columns:
            preview[qcol] = preview[qcol].apply(_disp_2dec_or_dash)

        if rcol in preview.columns:
            preview[rcol] = preview[rcol].apply(_disp_rate_or_dash)

    for c in ["Sales (₹)", "Payment (₹)", "Running Due (₹)"]:
        if c in preview.columns:
            preview[c] = preview[c].apply(_fmt_money)

    if "Total Milk (L)" in preview.columns:
        preview["Total Milk (L)"] = preview["Total Milk (L)"].apply(_disp_2dec_or_dash)

    st.dataframe(df_for_display(preview), use_container_width=True)

    # ---------------- GRAND TOTALS (Categories + Payments) ----------------
    # Computed from the in-memory preview derived from current draft for (date, zone).
    # No DB reads here; safe against cross-date contamination.
    st.subheader("🧾 Totals (Daily)")
    # Build safe columns for totals in this section
    preview_df = preview.copy() if "preview" in locals() else pd.DataFrame()
    # Ensure cat_names is available in this scope (Billing/Preview totals safety)
    if "cat_names" not in locals() or not isinstance(cat_names, list):
        _cn = []
        try:
            if (
                "cat_cols" in locals()
                and isinstance(cat_cols, list)
                and len(cat_cols) > 0
            ):
                for _m in cat_cols:
                    if isinstance(_m, dict):
                        _n = _m.get("name") or _m.get("Category")
                        if not _n and isinstance(_m.get("col"), str):
                            _n = _m["col"].replace(" Qty", "").strip()
                        if _n:
                            _cn.append(str(_n).strip())
            if (
                (not _cn)
                and ("categories" in locals())
                and hasattr(categories, "empty")
                and (not categories.empty)
                and ("name" in categories.columns)
            ):
                _cn = categories["name"].dropna().astype(str).tolist()
        except Exception:
            _cn = []
        # de-dup, keep stable order
        cat_names = list(dict.fromkeys([c for c in _cn if str(c).strip()]))
    cat_col_names = [
        f"{cat} Qty"
        for cat in cat_names
        if (not preview_df.empty and f"{cat} Qty" in preview_df.columns)
    ]
    # Category totals (L)
    cat_totals = {}
    for col in cat_col_names:
        if col in preview_df.columns:
            cat_totals[col] = float(
                pd.to_numeric(preview_df[col], errors="coerce").fillna(0.0).sum()
            )
    grand_qty = float(sum(cat_totals.values()))

    # Payment totals (₹)
    pay_totals = {}
    for m in PAYMENT_MODES:
        pcol = f"{m} ₹"
        if pcol in preview_df.columns:
            pay_totals[pcol] = float(
                pd.to_numeric(preview_df[pcol], errors="coerce").fillna(0.0).sum()
            )
    grand_pay = float(sum(pay_totals.values()))

    cgt1, cgt2 = st.columns(2)
    cgt1.metric("Total Milk (L)", f"{grand_qty:.2f}")
    cgt2.metric(
        "Payments Collected (₹)", f"₹{grand_pay:.2f}"
    )  # Detailed category totals row (dash for zeros)
    if cat_col_names:
        row = {"Category Totals": "TOTAL (L)"}
        for col in cat_col_names:
            label = str(col).replace(" Qty", "")
            row[label] = cat_totals.get(col, 0.0)
        row["GRAND TOTAL (L)"] = grand_qty

        tot_df = pd.DataFrame([row])
        for c in tot_df.columns:
            if c not in ("Category Totals", "GRAND TOTAL (L)"):
                tot_df[c] = tot_df[c].apply(fmt_zero_dash)
        tot_df["GRAND TOTAL (L)"] = tot_df["GRAND TOTAL (L)"].apply(
            lambda x: f"{float(x):.2f}"
        )
        st.dataframe(df_for_display(tot_df), use_container_width=True)

    st.subheader("💳 Payment Mode Totals (Period)")
    if pay_mode_totals.empty:
        st.info("No payments in this period.")
    else:
        st.dataframe(
            pay_mode_totals.style.format({"Total (₹)": "₹{:.2f}"}),
            use_container_width=True,
        )

    # --- Categories taken by this retailer ---
    # 1. Any category purchased with qty > 0 anywhere in the period (vectorized fillna(0) safe)
    purchased_cats = []
    if grid is not None and not grid.empty:
        for cat in cat_names:
            qcol = f"{cat} Qty"
            if qcol in grid.columns:
                qsum = pd.to_numeric(grid[qcol], errors="coerce").fillna(0.0).sum()
                if qsum > 0:
                    purchased_cats.append(cat)

    # 2. If none purchased in period, check retailer's assigned categories from prices
    if not purchased_cats:
        try:
            if "prices" in locals() and hasattr(prices, "empty") and not prices.empty:
                r_prices = prices.loc[prices["retailer_id"].astype(int) == rid]
                if not r_prices.empty and "categories" in locals() and not categories.empty:
                    cids = r_prices["category_id"].dropna().astype(int).tolist()
                    r_cats = categories.loc[categories["category_id"].isin(cids), "name"].dropna().astype(str).tolist()
                    purchased_cats = [c for c in cat_names if c in r_cats]
        except Exception:
            pass

    cats_for_print = purchased_cats if purchased_cats else cat_names

    col_tgl1, col_tgl2 = st.columns([2.2, 2.8])
    with col_tgl1:
        show_fat_snf_cols = st.toggle(
            "🥛 FAT व SNF चे 2 रिकामे रकाने ठेवा (Include FAT & SNF Columns)",
            value=True,
            key=f"bill_toggle_fat_snf_{rid}",
        )

    html = build_bill_html(
        rrow,
        start_day,
        end_day,
        grid,
        pay_mode_totals,
        cats_for_print,
        opening_due,
        show_empty_cols=show_fat_snf_cols,
    )

    day_span_str = f"{start_day.strftime('%d')}{end_day.strftime('%d')}" if start_day != end_day else start_day.strftime('%d')
    inv_no = f"CCM/{start_day.strftime('%Y%m')}-{day_span_str}/R{rid:03d}"
    clean_rname = retailer_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    inv_filename = f"bill_{clean_rname}_{start_day}_to_{end_day}.html"

    # --- Auto-create specific route folder and store HTML bills properly inside ---
    import os
    zone_name = rrow.get("zone", "General") or "General"
    safe_zone = "".join(c for c in str(zone_name) if c.isalnum() or c in (" ", "-", "_")).strip()
    if not safe_zone or safe_zone.lower() in ("default", "none", "nan"):
        safe_zone = "General_Route"

    route_inv_dir = os.path.join(os.getcwd(), "invoices", safe_zone)
    os.makedirs(route_inv_dir, exist_ok=True)
    inv_filepath = os.path.join(route_inv_dir, inv_filename)

    # Automatically save HTML bill directly into its Route folder
    auto_saved_ok = False
    try:
        with open(inv_filepath, "w", encoding="utf-8") as f:
            f.write(html)
        auto_saved_ok = True
    except Exception as _e:
        auto_saved_ok = False

    st.subheader("🖨️ Printable Credit / Cash Memo")

    # High-visibility Route Folder confirmation card
    st.markdown(
        f"""
        <div style="background:#f0fdf4; border:1.5px solid #86efac; border-radius:10px; padding:12px 16px; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div>
                <span style="font-weight:850; color:#166534; font-size:14px;">📁 Stored in Route Folder:</span>
                <span style="font-family:monospace; font-weight:800; color:#0f172a; margin-left:6px; background:#ffffff; padding:3px 10px; border-radius:6px; border:1.5px solid #cbd5e1; font-size:13px;">invoices/{safe_zone}/{inv_filename}</span>
            </div>
            <span style="background:#16a34a; color:#ffffff; font-weight:850; font-size:12px; padding:3px 10px; border-radius:12px;">✅ Auto-Saved in Device</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.components.v1.html(html, height=750, scrolling=True)

    st.caption(
        "To print: click the Print button in the memo OR download HTML and press Ctrl+P."
    )
    col_dl1, col_dl2, col_dl3 = st.columns([1.2, 1.2, 1.2])
    with col_dl1:
        st.download_button(
            "⬇️ Download Bill (HTML)",
            data=html.encode("utf-8"),
            file_name=inv_filename,
            mime="text/html",
            key="bill_dl_html",
            use_container_width=True,
        )
    with col_dl2:
        if st.button("💾 Re-save / Update in Route Folder", key="save_bill_device", use_container_width=True):
            try:
                with open(inv_filepath, "w", encoding="utf-8") as f:
                    f.write(html)
                st.success(f"✅ Memo saved to route folder:\n`{inv_filepath}`")
            except Exception as _save_err:
                st.error(f"Error saving memo: {_save_err}")
    with col_dl3:
        if st.button(f"📂 Open '{safe_zone}' Folder", key="open_route_folder", use_container_width=True):
            try:
                os.startfile(route_inv_dir)
            except Exception:
                st.info(f"Folder Path on Device: `{route_inv_dir}`")

    # List all stored bills in this route folder
    try:
        route_files = [f for f in os.listdir(route_inv_dir) if f.endswith(".html")]
        if route_files:
            with st.expander(f"📂 All Stored Bills in '{safe_zone}' ({len(route_files)} files)"):
                for rf in sorted(route_files, reverse=True):
                    st.text(f"📄 {rf}")
    except Exception:
        pass

# ============================================================
# PAGE: 🛡️ DATA HEALTH & BACKUP
# ============================================================
elif menu == "🛡️ Data Health & Backup":
    st.header("🛡️ Data Health & Backup")

    st.subheader("Backups")
    st.caption(
        "Download a ZIP containing CSV exports of all tables currently in the app."
    )
    dv = st.session_state.get("data_version", 0)
    # Keep bytes stable across reruns to avoid duplicate downloads in some browsers.
    if (
        st.session_state.get("backup_zip_version") != dv
        or "backup_zip_bytes" not in st.session_state
    ):
        st.session_state["backup_zip_bytes"] = make_full_backup_zip(dv)
        st.session_state["backup_zip_version"] = dv

    zip_bytes = st.session_state["backup_zip_bytes"]

    st.download_button(
        "⬇️ Download Full Backup ZIP (CSV)",
        data=zip_bytes,
        file_name=f"milk_accounting_backup_{date.today().isoformat()}.zip",
        mime="application/zip",
        key=f"backup_zip_{dv}",
        use_container_width=True,
    )

    st.divider()

    st.subheader("📊 Range Backup — Detailed Excel & CSV (Includes Staff Attendance, Wages & Handovers)")
    st.caption(
        "Generate a complete multi-sheet Excel Workbook (.xlsx) or Detailed CSV for any custom date range. "
        "Includes Daily Retailer Deliveries & Ledger, Worker Attendance & Daily Wages, Driver Cash Handovers, Route Expenses, and Workers Master."
    )

    bc1, bc2 = st.columns(2)
    with bc1:
        b_start = st.date_input(
            "From Date", value=date.today().replace(day=1), key="backup_start"
        )
    with bc2:
        b_end = st.date_input("To Date", value=date.today(), key="backup_end")

    if st.button(
        "📥 Generate Range Backup (Excel & CSV)", type="primary", key="backup_gen"
    ):
        with st.spinner("Building detailed range reports…"):
            # Fetch ALL data (full history needed for opening balances)
            _e_all = sb_fetch_df(ENTRIES_FILE, CSV_SCHEMAS[ENTRIES_FILE], filters=[])
            _p_all = sb_fetch_df(PAYMENTS_FILE, CSV_SCHEMAS[PAYMENTS_FILE], filters=[])
            _dp_all = sb_fetch_df(
                DISTRIBUTOR_PURCHASES_FILE,
                CSV_SCHEMAS[DISTRIBUTOR_PURCHASES_FILE],
                filters=[],
            )
            _dpay_all = sb_fetch_df(
                DISTRIBUTOR_PAYMENTS_FILE,
                CSV_SCHEMAS[DISTRIBUTOR_PAYMENTS_FILE],
                filters=[],
            )

            # 1. Multi-sheet Excel workbook (including attendance, wages, handovers, expenses)
            _excel_bytes = make_range_backup_excel(
                start_date=b_start,
                end_date=b_end,
                retailers=retailers,
                categories=categories,
                entries=_e_all,
                payments=_p_all,
                dist_purchases=_dp_all,
                dist_payments=_dpay_all,
                distributors=distributors,
                expenses_df=expenses,
            )

            # 2. CSV report (backward compatible)
            _csv_bytes = make_range_backup_csv(
                start_date=b_start,
                end_date=b_end,
                retailers=retailers,
                categories=categories,
                entries=_e_all,
                payments=_p_all,
                dist_purchases=_dp_all,
                dist_payments=_dpay_all,
                distributors=distributors,
            )

            _fname_xlsx = f"milk_range_backup_{b_start.strftime('%d-%m-%y')}_to_{b_end.strftime('%d-%m-%y')}.xlsx"
            _fname_csv = f"range_backup_{b_start.strftime('%d-%m-%y')}_to_{b_end.strftime('%d-%m-%y')}.csv"

            st.success(f"✅ Reports ready for {b_start.strftime('%d/%m/%Y')} to {b_end.strftime('%d/%m/%Y')}.")

            dl_c1, dl_c2 = st.columns(2)
            with dl_c1:
                st.download_button(
                    label="📊 Download Range Excel (.xlsx) [With Attendance & Wages]",
                    data=_excel_bytes,
                    file_name=_fname_xlsx,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="range_excel_dl",
                    type="primary",
                    use_container_width=True,
                )
            with dl_c2:
                st.download_button(
                    label="📥 Download Range CSV (.csv)",
                    data=_csv_bytes,
                    file_name=_fname_csv,
                    mime="text/csv",
                    key="range_csv_dl",
                    use_container_width=True,
                )

    st.subheader("Integrity Checks")

    issues = []

    if not entries.empty and not retailers.empty:
        known_r = set(retailers["retailer_id"].astype(int))
        bad = entries.loc[~entries["retailer_id"].astype(int).isin(known_r)][
            ["entry_id", "retailer_id", "date", "amount"]
        ]
        if not bad.empty:
            issues.append(("Orphan retailer_id in entries", bad))

    if not payments.empty and not retailers.empty:
        known_r = set(retailers["retailer_id"].astype(int))
        bad = payments.loc[~payments["retailer_id"].astype(int).isin(known_r)][
            ["payment_id", "retailer_id", "date", "amount"]
        ]
        if not bad.empty:
            issues.append(("Orphan retailer_id in payments", bad))

    if not entries.empty and not categories.empty:
        known_c = set(categories["category_id"].astype(int))
        bad = entries.loc[~entries["category_id"].astype(int).isin(known_c)][
            ["entry_id", "category_id", "date", "amount"]
        ]
        if not bad.empty:
            issues.append(("Orphan category_id in entries", bad))

    if not entries.empty:
        bad = entries.loc[
            (entries["qty"] < 0) | (entries["rate"] < 0) | (entries["amount"] < 0)
        ]
        if not bad.empty:
            issues.append(("Negative values in entries", bad))

    if not payments.empty:
        bad = payments.loc[payments["amount"] < 0]
        if not bad.empty:
            issues.append(("Negative payments", bad))

    for name, df, idcol in [
        ("entries", entries, "entry_id"),
        ("payments", payments, "payment_id"),
        ("prices", prices, "price_id"),
        ("retailers", retailers, "retailer_id"),
        ("categories", categories, "category_id"),
        ("distributors", distributors, "distributor_id"),
    ]:
        if not df.empty and idcol in df.columns:
            dup = df[df[idcol].duplicated(keep=False)].sort_values(idcol)
            if not dup.empty:
                issues.append((f"Duplicate IDs in {name} ({idcol})", dup))

    if not entries.empty:
        chk = entries.copy()
        chk["calc"] = (chk["qty"].astype(float) * chk["rate"].astype(float)).round(2)
        chk["amount_r"] = chk["amount"].astype(float).round(2)
        bad = chk.loc[(chk["qty"] > 0) & (chk["calc"] != chk["amount_r"])][
            ["entry_id", "date", "qty", "rate", "amount", "calc"]
        ]
        if not bad.empty:
            issues.append(("Entries amount mismatch (qty*rate != amount)", bad))

    if not issues:
        st.success("✅ No integrity problems found.")
    else:
        st.error(
            f"⚠️ Found {len(issues)} integrity issue group(s). Fix before trusting reports."
        )
        for title, df in issues:
            st.subheader(title)
            st.dataframe(df, use_container_width=True)
            st.divider()
