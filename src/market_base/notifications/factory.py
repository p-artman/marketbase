"""Factory for EmailNotifier selected by env."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from market_base.notifications.protocol import EmailNotifier

_override: Optional[EmailNotifier] = None


def set_email_notifier(notifier: Optional[EmailNotifier]) -> None:
    global _override
    _override = notifier
    _build_email_notifier.cache_clear()


def get_email_notifier() -> EmailNotifier:
    if _override is not None:
        return _override
    return _build_email_notifier()


@lru_cache(maxsize=1)
def _build_email_notifier() -> EmailNotifier:
    name = os.getenv('EMAIL_PROVIDER', 'console').lower()
    if name in ('django', 'smtp'):
        from market_base.notifications.django_smtp import DjangoEmailNotifier

        return DjangoEmailNotifier()
    if name == 'console':
        from market_base.notifications.console import ConsoleEmailNotifier

        return ConsoleEmailNotifier()
    raise ValueError(f'Unknown EMAIL_PROVIDER: {name}')
