"""Console EmailNotifier — logs messages (local/dev default)."""

from __future__ import annotations

import logging

from market_base.notifications.protocol import OrderEmailPayload

logger = logging.getLogger(__name__)


class ConsoleEmailNotifier:
    def send_order_confirmation(self, payload: OrderEmailPayload) -> None:
        logger.info(
            'ORDER CONFIRMATION -> %s | order #%s | %s %s | %s',
            payload.to_email,
            payload.order_id,
            payload.total_amount,
            payload.currency,
            payload.items_summary,
        )

    def send_payment_receipt(
        self,
        payload: OrderEmailPayload,
        *,
        payment_id: str = '',
    ) -> None:
        logger.info(
            'PAYMENT RECEIPT -> %s | order #%s | payment %s | %s %s',
            payload.to_email,
            payload.order_id,
            payment_id,
            payload.total_amount,
            payload.currency,
        )
