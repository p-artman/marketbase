"""Factory for DeliveryProvider instances selected by env."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from market_base.delivery.protocol import DeliveryProvider

_override: Optional[DeliveryProvider] = None


def set_delivery_provider(provider: Optional[DeliveryProvider]) -> None:
    global _override
    _override = provider
    _build_delivery_provider.cache_clear()


def get_delivery_provider() -> DeliveryProvider:
    if _override is not None:
        return _override
    return _build_delivery_provider()


@lru_cache(maxsize=1)
def _build_delivery_provider() -> DeliveryProvider:
    name = os.getenv('DELIVERY_PROVIDER', 'fake').lower()
    if name == 'cdek':
        from market_base.delivery.cdek import CdekProvider

        return CdekProvider()
    if name == 'fake':
        from market_base.delivery.fake import FakeDeliveryProvider

        return FakeDeliveryProvider()
    raise ValueError(f'Unknown DELIVERY_PROVIDER: {name}')
