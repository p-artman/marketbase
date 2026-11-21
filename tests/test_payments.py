"""Unit tests for market_base.payments contract and fake provider."""

from __future__ import annotations

from decimal import Decimal

import pytest

from market_base.payments.fake import FakePaymentProvider
from market_base.payments.protocol import PaymentProvider


def test_fake_provider_satisfies_protocol():
    provider = FakePaymentProvider()
    assert isinstance(provider, PaymentProvider)


def test_create_and_status():
    provider = FakePaymentProvider()
    created = provider.create_payment(
        amount=Decimal('100.00'),
        currency='RUB',
        description='Test',
        return_url='https://t.me/bot',
        metadata={'order_id': '1', 'user_id': '42'},
    )
    assert created.payment_id
    assert 'payment_id=' in created.confirmation_url

    status = provider.get_status(created.payment_id)
    assert status.status == 'pending'
    assert status.amount == Decimal('100.00')
    assert status.metadata['order_id'] == '1'


def test_webhook_marks_succeeded():
    provider = FakePaymentProvider()
    created = provider.create_payment(
        amount=10,
        description='Pay',
        return_url='https://example.com',
        metadata={'order_id': '9', 'user_id': '7'},
    )
    event = provider.parse_webhook(
        {
            'event': 'payment.succeeded',
            'object': {
                'id': created.payment_id,
                'amount': {'value': '10.00', 'currency': 'RUB'},
                'metadata': {'order_id': '9', 'user_id': '7'},
            },
        }
    )
    assert event.status == 'success'
    assert event.payment_id == created.payment_id
    assert event.order_id == '9'


@pytest.mark.integration
def test_yookassa_live_sandbox():
    import os
    if not (os.getenv('YOOMONEY_SHOP_ID') and os.getenv('YOOMONEY_SECRET_KEY')):
        pytest.skip('YooKassa credentials not set')
    from market_base.payments.yookassa import YooKassaProvider

    provider = YooKassaProvider()
    res = provider.create_payment(
        amount='1.00',
        description='Live test payment',
        return_url='https://t.me/test_bot',
        metadata={'test': 'true'},
    )
    assert res.payment_id
    assert res.confirmation_url.startswith('https://')
