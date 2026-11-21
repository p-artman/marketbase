"""Email / notification provider contract."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class OrderEmailPayload:
    to_email: str
    order_id: str
    customer_name: str
    total_amount: Decimal
    currency: str = 'RUB'
    payment_status: str = ''
    shipping_address: str = ''
    tracking_number: str = ''
    items_summary: str = ''


@runtime_checkable
class EmailNotifier(Protocol):
    def send_order_confirmation(self, payload: OrderEmailPayload) -> None: ...

    def send_payment_receipt(
        self,
        payload: OrderEmailPayload,
        *,
        payment_id: str = '',
    ) -> None: ...
