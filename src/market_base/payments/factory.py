"""Factory for PaymentProvider instances selected by env."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from market_base.payments.protocol import PaymentProvider

_override: Optional[PaymentProvider] = None


def set_payment_provider(provider: Optional[PaymentProvider]) -> None:
    """Override the global provider (tests). Pass None to clear."""
    global _override
    _override = provider
    _build_payment_provider.cache_clear()


def get_payment_provider() -> PaymentProvider:
    """Return the configured PaymentProvider (or test override)."""
    if _override is not None:
        return _override
    return _build_payment_provider()


@lru_cache(maxsize=1)
def _build_payment_provider() -> PaymentProvider:
    name = os.getenv('PAYMENT_PROVIDER', 'yookassa').lower()
    if name in ('yookassa', 'yoomoney'):
        from market_base.payments.yookassa import YooKassaProvider

        return YooKassaProvider()
    if name == 'fake':
        from market_base.payments.fake import FakePaymentProvider

        return FakePaymentProvider()
    raise ValueError(f'Unknown PAYMENT_PROVIDER: {name}')
