"""YooKassa (YooMoney) payment provider adapter."""

from __future__ import annotations

import logging
import os
import uuid
from decimal import Decimal
from typing import Any, Mapping, Optional

from yookassa import Configuration, Payment
from yookassa.domain.models.amount import Amount
from yookassa.domain.models.receipt import Receipt
from yookassa.domain.models.receipt_data.receipt_customer import ReceiptCustomer
from yookassa.domain.models.receipt_data.receipt_item import (
    PaymentMode,
    PaymentSubject,
    ReceiptItem,
)
from yookassa.domain.request import PaymentRequest

from market_base.payments.protocol import PaymentCreateResult, PaymentStatus, WebhookEvent

logger = logging.getLogger(__name__)


class YooKassaProvider:
    """Concrete PaymentProvider using the official YooKassa SDK."""

    def __init__(
        self,
        shop_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        default_return_url: Optional[str] = None,
    ) -> None:
        self.shop_id = shop_id or os.getenv('YOOMONEY_SHOP_ID', '')
        self.secret_key = secret_key or os.getenv('YOOMONEY_SECRET_KEY', '')
        self.default_return_url = default_return_url or os.getenv(
            'PAYMENT_RETURN_URL', ''
        )
        if not self.shop_id or not self.secret_key:
            raise ValueError('YOOMONEY_SHOP_ID and YOOMONEY_SECRET_KEY are required')
        Configuration.account_id = self.shop_id
        Configuration.secret_key = self.secret_key

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
        del kwargs
        amount_value = str(Decimal(str(amount)).quantize(Decimal('0.01')))
        idempotency_key = str(uuid.uuid4())
        meta = dict(metadata or {})
        inn = os.getenv('SELF_EMPLOYED_INN')
        if inn and 'self_employed_inn' not in meta:
            meta['self_employed_inn'] = inn

        receipt = self._build_receipt(
            amount=amount_value,
            currency=currency,
            description=description,
            customer_email=customer_email or meta.get('customer_email'),
            customer_phone=customer_phone or meta.get('customer_phone'),
            user_id=meta.get('user_id', '0'),
            receipt_items=receipt_items,
        )

        return_url = (return_url or '').strip() or (self.default_return_url or '').strip() or 'https://t.me/'

        payment_request = PaymentRequest(
            {
                'amount': Amount({'value': amount_value, 'currency': currency}),
                'description': description,
                'confirmation': {
                    'type': 'redirect',
                    'return_url': return_url,
                },
                'receipt': receipt,
                'capture': True,
                'metadata': meta,
            }
        )

        response = Payment.create(payment_request, idempotency_key)
        logger.info('YooKassa payment created: %s', response.id)
        return PaymentCreateResult(
            payment_id=response.id,
            confirmation_url=response.confirmation.confirmation_url,
        )

    def get_status(self, payment_id: str) -> PaymentStatus:
        payment = Payment.find_one(payment_id)
        return PaymentStatus(
            payment_id=payment.id,
            status=payment.status,
            amount=Decimal(str(payment.amount.value)),
            currency=payment.amount.currency,
            description=payment.description or '',
            paid=bool(getattr(payment, 'paid', False)),
            metadata=dict(payment.metadata or {}),
        )

    def parse_webhook(
        self,
        payload: Mapping[str, Any],
        headers: Optional[Mapping[str, str]] = None,
    ) -> WebhookEvent:
        del headers  # signature verification not implemented yet
        event = str(payload.get('event', ''))
        payment_data = payload.get('object') or {}
        metadata = payment_data.get('metadata') or {}
        amount_obj = payment_data.get('amount') or {}

        if event == 'payment.succeeded':
            status = 'success'
        elif event == 'payment.canceled':
            status = 'canceled'
        else:
            status = 'unknown'

        return WebhookEvent(
            event=event,
            status=status,
            payment_id=str(payment_data.get('id', '')),
            user_id=str(metadata.get('user_id', '')),
            order_id=str(metadata.get('order_id', '')),
            amount=str(amount_obj.get('value', '')),
            currency=str(amount_obj.get('currency', '')),
            raw=dict(payload),
        )

    @staticmethod
    def _build_receipt(
        *,
        amount: str,
        currency: str,
        description: str,
        customer_email: Optional[str],
        customer_phone: Optional[str],
        user_id: str,
        receipt_items: Optional[list[dict[str, Any]]] = None,
    ) -> Receipt:
        email = customer_email or os.getenv('SELF_EMPLOYED_EMAIL') or f'user_{user_id}@telegram.local'
        phone = customer_phone or os.getenv('SELF_EMPLOYED_PHONE') or '+70000000000'
        customer_dict: dict[str, Any] = {'email': email, 'phone': phone}

        items = []
        if receipt_items:
            for r in receipt_items:
                item_amount = str(Decimal(str(r.get('amount', '0'))).quantize(Decimal('0.01')))
                subj = r.get('payment_subject', PaymentSubject.COMMODITY)
                if isinstance(subj, str):
                    subj = (
                        PaymentSubject.COMMODITY
                        if subj.lower() in ('commodity', 'goods', 'product')
                        else PaymentSubject.SERVICE
                    )
                items.append(
                    ReceiptItem(
                        {
                            'description': str(r.get('description', 'Товар'))[:128],
                            'quantity': str(r.get('quantity', '1')),
                            'amount': Amount({'value': item_amount, 'currency': currency}),
                            'vat_code': int(r.get('vat_code', 1)),
                            'payment_subject': subj,
                            'payment_mode': PaymentMode.FULL_PAYMENT,
                        }
                    )
                )
        if not items:
            items.append(
                ReceiptItem(
                    {
                        'description': description[:128],
                        'quantity': '1',
                        'amount': Amount({'value': amount, 'currency': currency}),
                        'vat_code': 1,
                        'payment_subject': PaymentSubject.COMMODITY,
                        'payment_mode': PaymentMode.FULL_PAYMENT,
                    }
                )
            )

        customer = ReceiptCustomer(customer_dict)
        return Receipt(
            {
                'customer': customer,
                'items': items,
                'tax_system_code': 1,
                'type': 'sale',
            }
        )
