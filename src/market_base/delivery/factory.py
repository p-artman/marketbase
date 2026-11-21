"""Factory for DeliveryProvider instances selected by name or env."""

from __future__ import annotations

import os
from functools import lru_cache

from market_base.delivery.protocol import DeliveryProvider

_override: DeliveryProvider | None = None


def set_delivery_provider(provider: DeliveryProvider | None) -> None:
    global _override
    _override = provider
    _build_delivery_provider.cache_clear()


def get_delivery_provider(name: str | None = None) -> DeliveryProvider:
    """Return delivery provider by name, override, or env setting."""
    if name:
        return _build_delivery_provider(name.lower().strip())
    if _override is not None:
        return _override
    env_name = os.getenv('DELIVERY_PROVIDER', 'cdek').lower().strip()
    return _build_delivery_provider(env_name)


@lru_cache(maxsize=16)
def _build_delivery_provider(name: str) -> DeliveryProvider:
    if name == 'cdek':
        from market_base.delivery.cdek import CdekProvider

        return CdekProvider()
    if name == 'boxberry':
        from market_base.delivery.boxberry import BoxberryProvider

        return BoxberryProvider()
    if name in ('fivepost', '5post'):
        from market_base.delivery.fivepost import FivePostProvider

        return FivePostProvider()
    if name == 'fake':
        from market_base.delivery.fake import FakeDeliveryProvider

        return FakeDeliveryProvider()
    raise ValueError(f'Unknown DELIVERY_PROVIDER: {name}')


def get_available_providers() -> list[str]:
    """Return identifiers of all registered delivery providers."""
    return ['cdek', 'boxberry', 'fivepost']
