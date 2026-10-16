"""
MILK ACCOUNTING PRO — INTELLIGENCE LAYER
=========================================
Production-ready, deterministic intelligence layer providing voice/text
intent parsing, entity resolution, and accounting assistance.

Architecture Hierarchy:
  1. Database (Supabase) - Ultimate Source of Truth
  2. ERP Business Rules & Deterministic Accounting
  3. User Confirmation & Verification
  4. AI Intelligence Layer (Assistance & Draft Suggestions Only)
"""

from ai.config import AIConfig, get_ai_config
from ai.schemas.command_types import (
    IntentType,
    ConfidenceScore,
    ParsedDraft,
    SaleCommand,
    PaymentCommand,
    ExpenseCommand,
    PurchaseCommand,
    AmbiguousMatch,
)
from ai.parser.command_parser import parse_command
from ai.parser.number_parser import parse_number_words
from ai.entity_resolution.retailer_matcher import match_retailer
from ai.entity_resolution.category_matcher import match_category
from ai.entity_resolution.distributor_matcher import match_distributor

__all__ = [
    "AIConfig",
    "get_ai_config",
    "IntentType",
    "ConfidenceScore",
    "ParsedDraft",
    "SaleCommand",
    "PaymentCommand",
    "ExpenseCommand",
    "PurchaseCommand",
    "AmbiguousMatch",
    "parse_command",
    "parse_number_words",
    "match_retailer",
    "match_category",
    "match_distributor",
]
