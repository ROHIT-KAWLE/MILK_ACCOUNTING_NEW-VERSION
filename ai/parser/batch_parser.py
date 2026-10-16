"""Multi-Transaction Batch Parser for Continuous Speech and Text Stream.

Splits continuous spoken text into individual customer deliveries, payments,
and route expenses, resolving all entities in batch mode without stopping.
"""

import re
import pandas as pd
from dataclasses import dataclass, field
from ai.schemas.command_types import (
    SaleCommand,
    PaymentCommand,
    ExpenseCommand,
    PurchaseCommand,
    ParsedDraft,
)
from ai.parser.command_parser import parse_command
from ai.voice.transcription import normalize_speech_transcript


@dataclass
class BatchParseResult:
    sales: list[SaleCommand] = field(default_factory=list)
    payments: list[PaymentCommand] = field(default_factory=list)
    expenses: list[ExpenseCommand] = field(default_factory=list)
    purchases: list[PurchaseCommand] = field(default_factory=list)
    unmatched_segments: list[str] = field(default_factory=list)
    total_populated: int = 0
    summary_messages: list[str] = field(default_factory=list)


# Words that signify transition between different customer entries
TRANSITION_SPLIT_REGEX = re.compile(
    r"(?:\n+|(?:[\.,;।]+)|(?:\s+(?:आणि|next|त्यानंतर|तसेच|and|then)\s+))",
    re.IGNORECASE
)


def split_continuous_stream(continuous_text: str) -> list[str]:
    """Splits continuous speech or text into candidate single-transaction segments."""
    if not continuous_text or not isinstance(continuous_text, str):
        return []

    # Initial split by punctuation, linebreaks, and conjunctions
    raw_parts = TRANSITION_SPLIT_REGEX.split(continuous_text)
    segments = []
    for part in raw_parts:
        cleaned = part.strip()
        if len(cleaned) >= 2:
            segments.append(cleaned)
    return segments


def parse_continuous_batch(
    continuous_text: str,
    retailers_df: pd.DataFrame,
    categories_df: pd.DataFrame,
    distributors_df: pd.DataFrame = None,
    active_zone: str | None = None,
) -> BatchParseResult:
    """Parses a continuous stream of transactions and groups them into structured batch results."""
    result = BatchParseResult()
    segments = split_continuous_stream(continuous_text)

    if not segments:
        return result

    for seg in segments:
        norm = normalize_speech_transcript(seg)
        if not norm.is_valid:
            continue

        draft: ParsedDraft = parse_command(
            norm.transcript,
            retailers_df=retailers_df,
            categories_df=categories_df,
            distributors_df=distributors_df,
            active_zone=active_zone,
            mode_lock=None,  # Auto-detect intent per segment
        )

        if draft.is_valid_draft and draft.command:
            cmd = draft.command
            if isinstance(cmd, SaleCommand):
                result.sales.append(cmd)
                result.total_populated += 1
            elif isinstance(cmd, PaymentCommand):
                result.payments.append(cmd)
                result.total_populated += 1
            elif isinstance(cmd, ExpenseCommand):
                result.expenses.append(cmd)
                result.total_populated += 1
            elif isinstance(cmd, PurchaseCommand):
                result.purchases.append(cmd)
                result.total_populated += 1
        else:
            result.unmatched_segments.append(seg)

    # Build summary messages
    if result.sales:
        result.summary_messages.append(f"🥛 {len(result.sales)} ग्राहक डिलिव्हरी (Sales)")
    if result.payments:
        result.summary_messages.append(f"💵 {len(result.payments)} स्वतंत्र जमा (Payments)")
    if result.expenses:
        result.summary_messages.append(f"⛽ {len(result.expenses)} गाडी खर्च (Expenses)")
    if result.purchases:
        result.summary_messages.append(f"🏭 {len(result.purchases)} खरेदी (Purchases)")

    return result


def apply_batch_to_daily_grid(
    batch_res: BatchParseResult,
    draft_df: pd.DataFrame,
    cat_cols: list[dict],
) -> tuple[pd.DataFrame, list[int]]:
    """Applies parsed batch sales and collections directly into the Daily Entry DataFrame.
    
    Returns:
      (updated_draft_df, list_of_modified_retailer_ids)
    """
    if draft_df is None or draft_df.empty:
        return draft_df, []

    df = draft_df.copy()
    modified_rids = []

    for sale in batch_res.sales:
        target_rid = int(sale.retailer_id)
        if target_rid <= 0:
            continue

        mask = df["ID"].astype(str) == str(target_rid)
        if not mask.any():
            continue

        row_idx = df.index[mask][0]
        modified_rids.append(target_rid)

        # Apply category quantities
        for itm in sale.items:
            cid = int(itm.category_id)
            qty = float(itm.qty)
            for m in cat_cols:
                m_cid = int(m.get("category_id", m.get("id", 0)))
                if m_cid == cid and m["col"] in df.columns:
                    df.at[row_idx, m["col"]] = qty

        # Apply payments
        if sale.cash_payment > 0 and "CASH ₹" in df.columns:
            df.at[row_idx, "CASH ₹"] = float(sale.cash_payment)
        if sale.upi_payment > 0 and "UPI ₹" in df.columns:
            df.at[row_idx, "UPI ₹"] = float(sale.upi_payment)
        if sale.cheque_payment > 0 and "CHEQUE ₹" in df.columns:
            df.at[row_idx, "CHEQUE ₹"] = float(sale.cheque_payment)

    # Apply standalone payments
    for pay in batch_res.payments:
        target_rid = int(pay.retailer_id)
        if target_rid <= 0:
            continue
        mask = df["ID"].astype(str) == str(target_rid)
        if not mask.any():
            continue
        row_idx = df.index[mask][0]
        if target_rid not in modified_rids:
            modified_rids.append(target_rid)

        col_name = f"{pay.payment_mode} ₹"
        if col_name in df.columns:
            df.at[row_idx, col_name] = float(pay.amount)

    return df, modified_rids
