"""Unit tests for MAX Messenger platform validation and keyboard helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import quote, urlencode

import pytest

from market_base.messengers.max_platform import MaxAuthError, MaxPlatform

FAKE_MAX_TOKEN = 'test_max_token_12345'


def _build_signed_max_data(user_dict: dict, bot_token: str = FAKE_MAX_TOKEN) -> str:
    user_json = json.dumps(user_dict, separators=(',', ':'))
    params = {
        'auth_date': str(int(time.time())),
        'user': user_json,
    }
    decoded_items = sorted((k, v) for k, v in params.items())
    launch_params = '\n'.join(f'{k}={v}' for k, v in decoded_items)
    secret_key = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
    data_hash = hmac.new(secret_key, launch_params.encode(), hashlib.sha256).hexdigest()
    params['hash'] = data_hash
    return urlencode(params)


def test_max_validate_valid():
    platform = MaxPlatform(bot_token=FAKE_MAX_TOKEN, webapp_url='https://example.com/max/')
    raw = _build_signed_max_data({'id': 987654, 'name': 'MaxUser', 'username': 'maxuser'})
    user = platform.validate_init_data(raw)
    assert user.user_id == '987654'
    assert user.first_name == 'MaxUser'
    assert user.platform == 'max'


def test_max_validate_fragment():
    platform = MaxPlatform(bot_token=FAKE_MAX_TOKEN, webapp_url='https://example.com/max/')
    query = _build_signed_max_data({'id': 555})
    fragment = f'https://example.com/max/#WebAppData={quote(query)}&WebAppPlatform=desktop'
    user = platform.validate_init_data(fragment)
    assert user.user_id == '555'


def test_max_keyboard():
    platform = MaxPlatform(bot_token=FAKE_MAX_TOKEN, webapp_url='https://example.com/max/')
    kb = platform.shop_keyboard()
    assert len(kb) == 1
    buttons = kb[0]['payload']['buttons'][0]
    assert buttons[0]['type'] == 'open_app'
