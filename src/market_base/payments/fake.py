"""In-memory PaymentProvider for unit tests."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Mapping, Optional

from market_base.payments.protocol import PaymentCreateResult, PaymentStatus, WebhookEvent


class FakePaymentProvider:
    """Deterministic fake used in tests — no network calls."""

    def __init__(self) -> None:
        self.payments: dict[str, PaymentStatus] = {}

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
        **kwargs: Any,
    ) -> PaymentCreateResult:
        del customer_email, customer_phone, receipt_items, kwargs

        payment_id = str(uuid.uuid4())
        self.payments[payment_id] = PaymentStatus(
            payment_id=payment_id,
            status='pending',
            amount=Decimal(str(amount)),
            currency=currency,
            description=description,
            paid=False,
            metadata=dict(metadata or {}),
        )
        return PaymentCreateResult(
            payment_id=payment_id,
            confirmation_url=f'{return_url}?payment_id={payment_id}',
        )

    def get_status(self, payment_id: str) -> PaymentStatus:
        if payment_id not in self.payments:
            raise KeyError(f'Unknown payment: {payment_id}')
        return self.payments[payment_id]

    def parse_webhook(
        self,
        payload: Mapping[str, Any],
        headers: Optional[Mapping[str, str]] = None,
    ) -> WebhookEvent:
        del headers
        status = 'success' if payload.get('event') == 'payment.succeeded' else 'unknown'
        obj = payload.get('object') or {}
        meta = obj.get('metadata') or {}
        return WebhookEvent(
            event=str(payload.get('event', '')),
            status=status,
            payment_id=str(obj.get('id', '')),
            user_id=str(meta.get('user_id', '')),
            order_id=str(meta.get('order_id', '')),
            amount=str(obj.get('amount', {}).get('value', '')),
            currency=str(obj.get('amount', {}).get('currency', 'RUB')),
            raw=dict(payload),
        )
