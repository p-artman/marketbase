"""Telegram Mini App messenger adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Optional
from urllib.parse import parse_qsl

import requests

from market_base.messengers.protocol import MessengerUser


class TelegramAuthError(ValueError):
    """Raised when Telegram WebApp initData is invalid."""


class TelegramPlatform:
    name = 'telegram'

    def __init__(
        self,
        bot_token: Optional[str] = None,
        webapp_url: Optional[str] = None,
        auth_max_age_seconds: int = 86400,
    ) -> None:
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN', '') or os.getenv('BOT_TOKEN', '')
        self._webapp_url = webapp_url or os.getenv('WEBAPP_URL', '')
        self.auth_max_age_seconds = auth_max_age_seconds
        if not self.bot_token:
            raise ValueError('TELEGRAM_BOT_TOKEN or BOT_TOKEN is required for TelegramPlatform')

    def webapp_url(self) -> str:
        if not self._webapp_url:
            raise ValueError('WEBAPP_URL is not configured')
        return self._webapp_url

    def validate_init_data(self, raw: str) -> MessengerUser:
        if not raw:
            raise TelegramAuthError('Empty initData')

        parsed = dict(parse_qsl(raw, keep_blank_values=True))
        received_hash = parsed.pop('hash', None)
        if not received_hash:
            raise TelegramAuthError('Missing hash in initData')

        data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(parsed.items()))
        secret_key = hmac.new(
            b'WebAppData', self.bot_token.encode(), hashlib.sha256
        ).digest()
        calculated = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(calculated, received_hash):
            raise TelegramAuthError('Invalid initData signature')

        auth_date = int(parsed.get('auth_date', '0') or '0')
        if auth_date and (time.time() - auth_date) > self.auth_max_age_seconds:
            raise TelegramAuthError('initData expired')

        user_raw = parsed.get('user')
        if not user_raw:
            raise TelegramAuthError('Missing user in initData')
        user = json.loads(user_raw)
        return MessengerUser(
            user_id=str(user.get('id', '')),
            username=user.get('username') or '',
            first_name=user.get('first_name') or '',
            last_name=user.get('last_name') or '',
            language_code=user.get('language_code') or 'en',
            platform=self.name,
        )

    def notify_user(self, user_id: str, text: str) -> None:
        url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'
        response = requests.post(
            url,
            json={'chat_id': user_id, 'text': text},
            timeout=15,
        )
        response.raise_for_status()
