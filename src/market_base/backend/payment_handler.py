"""Compatibility shim around market_base.payments."""

from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Dict, Optional, Tuple

from market_base.payments import get_payment_provider
from market_base.payments.protocol import PaymentProvider

logger = logging.getLogger(__name__)

TEST_CARD = {
    'number': '1111 1111 1111 1026',
    'expiry': '12/22',
    'cvc': '000',
}


class YooMoneyPaymentHandler:
    """Thin adapter preserving bot-facing method signatures."""

    def __init__(self, provider: Optional[PaymentProvider] = None) -> None:
        self._provider = provider

    @property
    def provider(self) -> PaymentProvider:
        return self._provider or get_payment_provider()

    def create_payment(
        self,
        amount: float,
        description: str,
        user_id: int,
        user_email: Optional[str] = None,
        user_phone: Optional[str] = None,
        currency: str = 'RUB',
        return_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Tuple[str, str]:
        bot_username = os.getenv('BOT_USERNAME', '')
        meta = {
            'user_id': str(user_id),
            'bot_username': bot_username,
        }
        if metadata:
            meta.update({k: str(v) for k, v in metadata.items()})

        result = self.provider.create_payment(
            amount=Decimal(str(amount)),
            currency=currency,
            description=description,
            return_url=return_url
            or os.getenv('PAYMENT_RETURN_URL')
            or f'https://t.me/{bot_username}',
            metadata=meta,
            customer_email=user_email,
            customer_phone=user_phone,
        )
        return result.payment_id, result.confirmation_url

    def get_payment_status(self, payment_id: str) -> Dict:
        status = self.provider.get_status(payment_id)
        return {
            'id': status.payment_id,
            'status': status.status,
            'amount': str(status.amount),
            'currency': status.currency,
            'description': status.description,
            'paid': status.paid,
            'metadata': status.metadata,
        }

    def process_webhook(self, webhook_data: Dict) -> Dict:
        event = self.provider.parse_webhook(webhook_data)
        return {
            'status': event.status,
            'payment_id': event.payment_id,
            'user_id': event.user_id,
            'order_id': event.order_id,
            'amount': event.amount,
            'currency': event.currency,
            'event': event.event,
        }

    def create_test_payment(self, user_id: int) -> Tuple[str, str]:
        return self.create_payment(
            amount=1.00,
            description='Test payment for development',
            user_id=user_id,
        )


_handler_instance = None


def get_payment_handler() -> YooMoneyPaymentHandler:
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = YooMoneyPaymentHandler()
    return _handler_instance
