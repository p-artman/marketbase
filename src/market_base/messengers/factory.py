"""Factory for MessengerPlatform instances selected by env."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from market_base.messengers.protocol import MessengerPlatform

_override: Optional[MessengerPlatform] = None


def set_messenger_platform(platform: Optional[MessengerPlatform]) -> None:
    global _override
    _override = platform
    _build_messenger_platform.cache_clear()


def get_messenger_platform() -> MessengerPlatform:
    if _override is not None:
        return _override
    return _build_messenger_platform()


@lru_cache(maxsize=1)
def _build_messenger_platform() -> MessengerPlatform:
    name = os.getenv('MESSENGER_PLATFORM', 'telegram').lower()
    if name == 'telegram':
        from market_base.messengers.telegram import TelegramPlatform

        return TelegramPlatform()
    if name == 'max':
        from market_base.messengers.max_platform import MaxPlatform

        return MaxPlatform()
    raise ValueError(f'Unknown MESSENGER_PLATFORM: {name}')
