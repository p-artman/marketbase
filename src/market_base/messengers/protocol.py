"""MessengerPlatform contract for mini-app messengers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class MessengerUser:
    user_id: str
    username: str = ''
    first_name: str = ''
    last_name: str = ''
    language_code: str = 'en'
    platform: str = 'telegram'


@runtime_checkable
class MessengerPlatform(Protocol):
    name: str

    def validate_init_data(self, raw: str) -> MessengerUser: ...

    def webapp_url(self) -> str: ...

    def notify_user(self, user_id: str, text: str) -> None: ...
