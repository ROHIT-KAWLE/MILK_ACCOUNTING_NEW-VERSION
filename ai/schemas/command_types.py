"""
Typed data schemas for intelligence pipeline draft transactions.
Every parsed command is held in a structured draft object until explicit user confirmation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntentType(str, Enum):
    RETAILER_SALE = "RETAILER_SALE"
    RETAILER_PAYMENT = "RETAILER_PAYMENT"
    ROUTE_EXPENSE = "ROUTE_EXPENSE"
    DISTRIBUTOR_PURCHASE = "DISTRIBUTOR_PURCHASE"
    DISTRIBUTOR_PAYMENT = "DISTRIBUTOR_PAYMENT"
    UNKNOWN = "UNKNOWN"


@dataclass
class ConfidenceScore:
    overall: float = 0.0
    intent: float = 0.0
    entity: float = 0.0
    quantity: float = 0.0
    amount: float = 0.0
    category: float = 0.0
    payment_mode: float = 0.0
    level: str = "LOW"  # "HIGH", "MEDIUM", "LOW"

    def compute_level(self) -> str:
        if self.overall >= 0.80:
            self.level = "HIGH"
        elif self.overall >= 0.55:
            self.level = "MEDIUM"
        else:
            self.level = "LOW"
        return self.level


@dataclass
class ParsedItem:
    category_id: int | None = None
    category_name: str | None = None
    qty: float | None = None
    # NOTE: Rate must NEVER be calculated or invented by AI.
    # It remains None until resolved deterministically by ERP pricing engine.
    rate: float | None = None
    amount: float | None = None


@dataclass
class SaleCommand:
    retailer_id: int
    retailer_name: str
    items: list[ParsedItem] = field(default_factory=list)
    cash_payment: float = 0.0
    upi_payment: float = 0.0
    cheque_payment: float = 0.0
    zone: str | None = None
    date: str | None = None


@dataclass
class PaymentCommand:
    retailer_id: int
    retailer_name: str
    amount: float
    payment_mode: str = "Cash"
    zone: str | None = None
    date: str | None = None


@dataclass
class ExpenseCommand:
    category: str  # Fuel, Nasta, Toll, Repair, Police / Fine, Rent, etc.
    amount: float
    payment_mode: str = "Cash"
    zone: str | None = None
    note: str | None = None

    @property
    def expense_type(self) -> str:
        return self.category


@dataclass
class PurchaseCommand:
    distributor_id: int
    distributor_name: str
    category_id: int
    category_name: str
    qty: float
    rate: float | None = None
    amount: float | None = None
    date: str | None = None


@dataclass
class AmbiguousCandidate:
    id: int
    name: str
    score: float
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AmbiguousMatch:
    query: str
    entity_type: str  # "retailer", "category", "distributor"
    candidates: list[AmbiguousCandidate] = field(default_factory=list)


@dataclass
class ParsedDraft:
    intent: IntentType = IntentType.UNKNOWN
    command: SaleCommand | PaymentCommand | ExpenseCommand | PurchaseCommand | None = None
    confidence: ConfidenceScore = field(default_factory=ConfidenceScore)
    raw_text: str = ""
    normalized_text: str = ""
    missing_fields: list[str] = field(default_factory=list)
    ambiguity: AmbiguousMatch | None = None
    is_valid_draft: bool = False
    validation_notes: list[str] = field(default_factory=list)
    error_message: str | None = None
