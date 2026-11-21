"""MAX messenger adapter (Bot API + Mini App initData validation).

Docs:
- https://dev.max.ru/docs/chatbots/bots-coding/prepare
- https://dev.max.ru/docs/webapps/introduction
- https://dev.max.ru/docs/webapps/validation
- https://dev.max.ru/docs-api/methods/POST/messages
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Optional
from urllib.parse import parse_qsl, unquote

import requests

from market_base.messengers.max_ssl import ssl_verify_arg
from market_base.messengers.protocol import MessengerUser

logger = logging.getLogger(__name__)

DEFAULT_API_BASE = 'https://platform-api2.max.ru'


class MaxAuthError(ValueError):
    """Raised when Max WebApp initData is invalid."""


class MaxApiError(RuntimeError):
    """Raised when Max Bot API returns an error."""


class MaxPlatform:
    """MAX для бизнеса — messenger + mini-app contract implementation."""

    name = 'max'

    def __init__(
        self,
        bot_token: Optional[str] = None,
        webapp_url: Optional[str] = None,
        api_base: Optional[str] = None,
        auth_max_age_seconds: int = 3600,
    ) -> None:
        self.bot_token = bot_token or os.getenv('MAX_BOT_TOKEN', '')
        self._webapp_url = (
            webapp_url
            or os.getenv('MAX_WEBAPP_URL', '')
            or os.getenv('WEBAPP_URL', '')
        )
        self.api_base = (api_base or os.getenv('MAX_API_BASE', DEFAULT_API_BASE)).rstrip(
            '/'
        )
        self.auth_max_age_seconds = auth_max_age_seconds
        if not self.bot_token:
            raise ValueError('MAX_BOT_TOKEN is required for MaxPlatform')

    def webapp_url(self) -> str:
        url = (self._webapp_url or '').strip()
        if not url:
            raise ValueError(
                'MAX_WEBAPP_URL (or WEBAPP_URL) is required for Max mini-app'
            )
        # Prefer dedicated Max entry if only Telegram marketplace URL is set
        if url.rstrip('/').endswith('/marketplace') and '/max' not in url:
            url = url.rstrip('/') + '/max/'
        return url.rstrip('/') + '/'

    def validate_init_data(self, raw: str) -> MessengerUser:
        """Validate Max WebAppData / initData (HMAC-SHA256, same family as TG)."""
        app_data = self._extract_webapp_data(raw)
        if not app_data:
            raise MaxAuthError('Empty Max WebAppData / initData')

        params = dict(parse_qsl(app_data, keep_blank_values=True))
        received_hash = params.pop('hash', None)
        if not received_hash:
            raise MaxAuthError('Missing hash in Max initData')

        # Values must be URL-decoded for the check string
        decoded_items = sorted(
            (k, unquote(v)) for k, v in params.items()
        )
        launch_params = '\n'.join(f'{k}={v}' for k, v in decoded_items)

        secret_key = hmac.new(
            b'WebAppData', self.bot_token.encode(), hashlib.sha256
        ).digest()
        calculated = hmac.new(
            secret_key, launch_params.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(calculated, received_hash):
            raise MaxAuthError('Invalid Max initData signature')

        auth_date = int(params.get('auth_date', '0') or '0')
        if auth_date and (time.time() - auth_date) > self.auth_max_age_seconds:
            raise MaxAuthError('Max initData expired')

        user_raw = params.get('user')
        if not user_raw:
            raise MaxAuthError('Missing user in Max initData')
        user = json.loads(unquote(user_raw) if '%' in user_raw else user_raw)
        return MessengerUser(
            user_id=str(user.get('id', '')),
            username=user.get('username') or '',
            first_name=user.get('first_name') or user.get('name') or '',
            last_name=user.get('last_name') or '',
            language_code=user.get('language_code') or 'ru',
            platform=self.name,
        )

    def notify_user(self, user_id: str, text: str) -> None:
        """Send a message to a Max user via Bot API."""
        self.send_message(user_id=int(user_id), text=text)

    def get_me(self) -> dict[str, Any]:
        return self._request('GET', '/me')

    def get_updates(
        self,
        *,
        marker: Optional[int] = None,
        timeout: int = 30,
        limit: int = 100,
        types: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {'timeout': timeout, 'limit': limit}
        if marker is not None:
            params['marker'] = marker
        if types:
            params['types'] = ','.join(types)
        return self._request('GET', '/updates', params=params)

    def send_message(
        self,
        *,
        text: str,
        user_id: Optional[int] = None,
        chat_id: Optional[int] = None,
        attachments: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        if user_id is None and chat_id is None:
            raise ValueError('user_id or chat_id is required')
        params: dict[str, Any] = {}
        if user_id is not None:
            params['user_id'] = user_id
        if chat_id is not None:
            params['chat_id'] = chat_id
        body: dict[str, Any] = {'text': text}
        if attachments is not None:
            body['attachments'] = attachments
        return self._request('POST', '/messages', params=params, json=body)

    def shop_keyboard(self) -> list[dict[str, Any]]:
        """Inline keyboard that opens the Max mini-app (Bridge + initData)."""
        bot_username = (os.getenv('MAX_BOT_USERNAME') or '').lstrip('@').strip()
        button: dict[str, Any] = {
            'type': 'open_app',
            'text': 'Открыть магазин',
            'web_app': bot_username or self.webapp_url(),
        }
        return [
            {
                'type': 'inline_keyboard',
                'payload': {'buttons': [[button]]},
            }
        ]

    def shop_keyboard_link_fallback(self) -> list[dict[str, Any]]:
        """Fallback link button (no Bridge) if open_app is rejected by API."""
        return [
            {
                'type': 'inline_keyboard',
                'payload': {
                    'buttons': [
                        [
                            {
                                'type': 'link',
                                'text': 'Открыть магазин',
                                'url': self.webapp_url(),
                            }
                        ]
                    ]
                },
            }
        ]

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        url = f'{self.api_base}{path}'
        headers = {
            'Authorization': self.bot_token,
            'Content-Type': 'application/json',
        }
        response = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json,
            timeout=max(35, int((params or {}).get('timeout', 30)) + 5),
            verify=ssl_verify_arg(),
        )
        if not response.ok:
            raise MaxApiError(
                f'Max API {method} {path}: {response.status_code} {response.text}'
            )
        if not response.content:
            return {}
        return response.json()

    @staticmethod
    def _extract_webapp_data(raw: str) -> str:
        raw = (raw or '').strip()
        if not raw:
            return ''
        if 'WebAppData=' in raw:
            fragment = raw.split('#', 1)[-1]
            parsed = dict(parse_qsl(fragment, keep_blank_values=True))
            return parsed.get('WebAppData', '') or ''
        return raw
