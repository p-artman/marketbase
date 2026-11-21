"""Unit tests for TelegramPlatform initData validation."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from market_base.messengers.telegram import TelegramAuthError, TelegramPlatform

FAKE_BOT_TOKEN = '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'


def _build_signed_init_data(user_dict: dict, bot_token: str = FAKE_BOT_TOKEN) -> str:
    params = {
        'auth_date': str(int(time.time())),
        'query_id': 'AAHdF6IQAAAAAN0XohDhrOrc',
        'user': json.dumps(user_dict, separators=(',', ':')),
    }
    check_string = '\n'.join(f'{k}={v}' for k, v in sorted(params.items()))
    secret_key = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
    data_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    params['hash'] = data_hash
    return urlencode(params)


def test_telegram_validate_valid():
    platform = TelegramPlatform(bot_token=FAKE_BOT_TOKEN, webapp_url='https://example.com')
    raw = _build_signed_init_data({'id': 123456, 'first_name': 'Test', 'username': 'tester'})
    user = platform.validate_init_data(raw)
    assert user.user_id == '123456'
    assert user.first_name == 'Test'
    assert user.username == 'tester'
    assert user.platform == 'telegram'


def test_telegram_validate_invalid_hash():
    platform = TelegramPlatform(bot_token=FAKE_BOT_TOKEN, webapp_url='https://example.com')
    raw = _build_signed_init_data({'id': 123456}) + '&extra=bad'
    with pytest.raises(TelegramAuthError):
        platform.validate_init_data(raw)
