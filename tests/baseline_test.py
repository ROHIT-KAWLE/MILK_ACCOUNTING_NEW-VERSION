"""
MILK ACCOUNTING PRO — BASELINE REGRESSION & AUDIT TEST SUITE
============================================================
This script establishes authoritative quantitative baselines for:
1. Database connectivity & row counts across all 12 tables
2. Financial & volume accounting reconciliations
3. Data integrity constraints
4. Core calculation functions
"""

import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
import toml
import pandas as pd

# Configure SSL context for Windows HTTPS compatibility
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import httpx
_orig_init = httpx.Client.__init__
def _unverified_init(self, *args, **kwargs):
    kwargs['verify'] = False
    _orig_init(self, *args, **kwargs)
httpx.Client.__init__ = _unverified_init

from supabase import create_client

def load_secrets():
    path = os.path.join('.streamlit', 'secrets.toml')
    if not os.path.exists(path):
        raise FileNotFoundError("Could not find .streamlit/secrets.toml")
    with open(path, 'r', encoding='utf-8') as f:
        return toml.load(f)

def run_baseline_audit():
    print("=" * 65)
    print("MILK ACCOUNTING PRO — BASELINE TEST & RECONCILIATION SUITE")
    print("=" * 65)

    secrets = load_secrets()
    sb_cfg = secrets["supabase"]
    sb = create_client(sb_cfg["url"], sb_cfg["anon_key"])

    # ---------------------------------------------------------
    # 1. DATABASE CONNECTIVITY & TABLE ROW COUNTS
    # ---------------------------------------------------------
    print("\n[SECTION 1: DATABASE TABLE ROW COUNTS]")
    tables = [
        "retailers",
        "categories",
        "prices",
        "entries",
        "payments",
        "distributors",
        "distributor_purchases",
        "distributor_payments",
        "distributor_category_map",
        "wastage",
        "expenses",
        "main_retailers",
    ]
    
    counts = {}
    for t in tables:
        try:
            resp = sb.table(t).select("*", count="exact").limit(1).execute()
            cnt = resp.count if resp.count is not None else len(resp.data)
            counts[t] = cnt
            print(f"  • Table '{t:25s}': {cnt:>7} records")
        except Exception as e:
            counts[t] = f"ERROR ({e})"
            print(f"  • Table '{t:25s}': FAILED ({e})")

    # ---------------------------------------------------------
    # 2. FETCH ALL DATA IN CHUNKS FOR RECONCILIATION
    # ---------------------------------------------------------
    print("\n[SECTION 2: DATA EXTRACTION & INTEGRITY CHECK]")
    def fetch_all(table, page_size=1000):
        out = []
        offset = 0
        while True:
            resp = sb.table(table).select("*").range(offset, offset + page_size - 1).execute()
            data = resp.data or []
            out.extend(data)
            if len(data) < page_size:
                break
            offset += page_size
        return pd.DataFrame(out)

    df_retailers = fetch_all("retailers")
    df_categories = fetch_all("categories")
    df_prices = fetch_all("prices")
    df_entries = fetch_all("entries")
    df_payments = fetch_all("payments")
    df_distributors = fetch_all("distributors")
    df_purchases = fetch_all("distributor_purchases")
    df_dist_payments = fetch_all("distributor_payments")
    df_wastage = fetch_all("wastage")
    df_expenses = fetch_all("expenses")

    print(f"  Loaded Entries: {len(df_entries)} rows")
    print(f"  Loaded Payments: {len(df_payments)} rows")
    print(f"  Loaded Prices: {len(df_prices)} rows")
    print(f"  Loaded Distributors: {len(df_distributors)} rows")
    print(f"  Loaded Purchases: {len(df_purchases)} rows")
    print(f"  Loaded Distributor Payments: {len(df_dist_payments)} rows")

    # ---------------------------------------------------------
    # 3. ACCOUNTING RECONCILIATIONS
    # ---------------------------------------------------------
    print("\n[SECTION 3: ACCOUNTING RECONCILIATIONS]")
    
    # Retailer side
    sales_total = float(pd.to_numeric(df_entries["amount"], errors="coerce").fillna(0).sum())
    sales_liters = float(pd.to_numeric(df_entries["qty"], errors="coerce").fillna(0).sum())
    payments_total = float(pd.to_numeric(df_payments["amount"], errors="coerce").fillna(0).sum())
    retailer_net_due = sales_total - payments_total

    print(f"  A. Retailer Sales Volume:     {sales_liters:>12,.2f} Liters")
    print(f"  B. Retailer Total Sales:       Rs. {sales_total:>12,.2f}")
    print(f"  C. Retailer Total Payments:    Rs. {payments_total:>12,.2f}")
    print(f"  D. Retailer Net Outstanding:   Rs. {retailer_net_due:>12,.2f}")

    # Distributor side
    purchases_total = float(pd.to_numeric(df_purchases["amount"], errors="coerce").fillna(0).sum())
    purchases_liters = float(pd.to_numeric(df_purchases["qty"], errors="coerce").fillna(0).sum())
    dist_payments_total = float(pd.to_numeric(df_dist_payments["amount"], errors="coerce").fillna(0).sum())
    distributor_net_due = purchases_total - dist_payments_total

    print(f"  E. Distributor Purchase Volume:{purchases_liters:>12,.2f} Liters")
    print(f"  F. Distributor Purchases:      Rs. {purchases_total:>12,.2f}")
    print(f"  G. Distributor Payments:       Rs. {dist_payments_total:>12,.2f}")
    print(f"  H. Distributor Net Payable:    Rs. {distributor_net_due:>12,.2f}")

    # Wastage & Expenses
    waste_liters = float(pd.to_numeric(df_wastage["qty"], errors="coerce").fillna(0).sum()) if not df_wastage.empty else 0.0
    waste_loss = float(pd.to_numeric(df_wastage["estimated_loss"], errors="coerce").fillna(0).sum()) if not df_wastage.empty else 0.0
    expenses_total = float(pd.to_numeric(df_expenses["amount"], errors="coerce").fillna(0).sum()) if not df_expenses.empty else 0.0

    print(f"  I. Total Wastage:              {waste_liters:>12,.2f} Liters (Loss: Rs. {waste_loss:,.2f})")
    print(f"  J. Total Expenses:             Rs. {expenses_total:>12,.2f}")

    # Net Physical Balance
    net_liters = purchases_liters - sales_liters - waste_liters
    print(f"  K. Physical Net Movement:     {net_liters:>12,.2f} Liters (Incoming - Outgoing - Waste)")

    # ---------------------------------------------------------
    # 4. TRANSACTION INTEGRITY AUDIT
    # ---------------------------------------------------------
    print("\n[SECTION 4: TRANSACTION INTEGRITY AUDIT]")
    
    # Check entries qty * rate == amount
    e_calc = (pd.to_numeric(df_entries["qty"], errors="coerce").fillna(0) * pd.to_numeric(df_entries["rate"], errors="coerce").fillna(0)).round(2)
    e_amt = pd.to_numeric(df_entries["amount"], errors="coerce").fillna(0).round(2)
    e_mismatch = (e_calc != e_amt) & (e_amt > 0)
    mismatch_count = int(e_mismatch.sum())
    print(f"  • Entries with Amount Mismatch (qty * rate != amount): {mismatch_count}")

    # Check orphan retailer_ids in entries
    rids = set(df_retailers["retailer_id"].dropna().astype(int))
    e_rids = set(df_entries["retailer_id"].dropna().astype(int))
    orphan_rids_entries = e_rids - rids
    print(f"  • Orphan Retailer IDs in Entries:                      {len(orphan_rids_entries)}")

    # Check orphan category_ids in entries
    cids = set(df_categories["category_id"].dropna().astype(int))
    e_cids = set(df_entries["category_id"].dropna().astype(int))
    orphan_cids_entries = e_cids - cids
    print(f"  • Orphan Category IDs in Entries:                      {len(orphan_cids_entries)}")

    # Check negative values
    e_neg_qty = int((pd.to_numeric(df_entries["qty"], errors="coerce") < 0).sum())
    e_neg_amt = int((pd.to_numeric(df_entries["amount"], errors="coerce") < 0).sum())
    p_neg_amt = int((pd.to_numeric(df_payments["amount"], errors="coerce") < 0).sum())
    print(f"  • Negative Quantities in Entries:                      {e_neg_qty}")
    print(f"  • Negative Amounts in Entries:                         {e_neg_amt}")
    print(f"  • Negative Amounts in Payments:                        {p_neg_amt}")

    print("\n" + "=" * 65)
    print("BASELINE AUDIT EXECUTION COMPLETE")
    print("=" * 65)

if __name__ == "__main__":
    run_baseline_audit()
