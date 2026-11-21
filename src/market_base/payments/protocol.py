"""PaymentProvider contract shared by all payment adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class PaymentCreateResult:
    payment_id: str
    confirmation_url: str


@dataclass(frozen=True)
class PaymentStatus:
    payment_id: str
    status: str
    amount: Decimal
    currency: str
    description: str = ''
    paid: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookEvent:
    event: str
    status: str  # success | canceled | unknown
    payment_id: str = ''
    user_id: str = ''
    order_id: str = ''
    amount: str = ''
    currency: str = ''
    raw: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class PaymentProvider(Protocol):
    def create_payment(
        self,
        *,
        amount: Decimal | float | str,
        currency: str = 'RUB',
        description: str,
        return_url: str,
        metadata: Optional[Mapping[str, str]] = None,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
        receipt_items: Optional[list[dict[str, Any]]] = None,
    ) -> PaymentCreateResult: ...

    def get_status(self, payment_id: str) -> PaymentStatus: ...

    def parse_webhook(
        self,
        payload: Mapping[str, Any],
        headers: Optional[Mapping[str, str]] = None,
    ) -> WebhookEvent: ...
