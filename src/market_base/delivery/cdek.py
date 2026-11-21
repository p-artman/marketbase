"""CDEK API v2 delivery provider adapter."""

from __future__ import annotations

import logging
import os
import time
from decimal import Decimal
from typing import Any, Optional, Sequence
from urllib.parse import urljoin

import requests

from market_base.core.types import Address, Parcel
from market_base.delivery.protocol import DeliveryRate, Shipment, TrackingInfo

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = 'https://api.cdek.ru/v2/'
TEST_BASE_URL = 'https://api.edu.cdek.ru/v2/'


class CdekError(RuntimeError):
    """Raised when CDEK API returns an error."""


class CdekProvider:
    name = 'cdek'

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        from_city_code: Optional[int] = None,
    ) -> None:
        self.client_id = client_id or os.getenv('CDEK_CLIENT_ID', '')
        self.client_secret = client_secret or os.getenv('CDEK_CLIENT_SECRET', '')
        use_test = os.getenv('CDEK_TEST', 'true').lower() in ('1', 'true', 'yes')
        self.base_url = base_url or (
            os.getenv('CDEK_BASE_URL')
            or (TEST_BASE_URL if use_test else DEFAULT_BASE_URL)
        )
        self.from_city_code = int(
            from_city_code
            or os.getenv('CDEK_FROM_CITY_CODE', '44')  # Moscow default
        )
        self._token: Optional[str] = None
        self._token_expires_at: float = 0
        if not self.client_id or not self.client_secret:
            raise ValueError('CDEK_CLIENT_ID and CDEK_CLIENT_SECRET are required')

    def _authenticate(self) -> str:
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token
        response = requests.post(
            urljoin(self.base_url, 'oauth/token'),
            data={
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            },
            timeout=20,
        )
        if not response.ok:
            raise CdekError(f'CDEK auth failed: {response.status_code} {response.text}')
        data = response.json()
        self._token = data['access_token']
        self._token_expires_at = time.time() + int(data.get('expires_in', 3600))
        return self._token

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        token = self._authenticate()
        response = requests.request(
            method,
            urljoin(self.base_url, path.lstrip('/')),
            headers={'Authorization': f'Bearer {token}'},
            json=json,
            params=params,
            timeout=30,
        )
        if not response.ok:
            raise CdekError(f'CDEK {method} {path}: {response.status_code} {response.text}')
        if not response.content:
            return {}
        return response.json()

    def autocomplete_cities(self, query: str = '') -> list[dict[str, Any]]:
        q = (query or '').strip()
        if not q:
            q = 'Москва'
        try:
            # 1. Try modern CDEK v2 suggestions endpoint (supports partial names/prefixes)
            res = self._request('GET', 'location/suggest/cities', params={'name': q, 'country_code': 'RU'})
            if isinstance(res, list) and res:
                cities = []
                for c in res:
                    full = c.get('full_name') or c.get('city') or ''
                    parts = [p.strip() for p in full.split(',') if p.strip()]
                    city_name = parts[0] if parts else (c.get('city') or '')
                    region_name = parts[1] if len(parts) > 1 else (c.get('region') or '')
                    cities.append({
                        'code': c.get('code'),
                        'city': city_name,
                        'region': region_name,
                        'full_name': full,
                        'postal_code': c.get('postal_code', ''),
                        'fias_guid': c.get('city_uuid', ''),
                    })
                return cities
        except Exception as e:
            logger.debug('CDEK suggest/cities failed: %s, falling back to location/cities', e)

        try:
            # 2. Fallback to location/cities
            res = self._request('GET', 'location/cities', params={'city': q, 'country_codes': 'RU', 'size': 10})
            if isinstance(res, list) and res:
                return [
                    {
                        'code': c.get('code'),
                        'city': c.get('city'),
                        'region': c.get('region', ''),
                        'postal_code': c.get('postal_code', ''),
                        'fias_guid': c.get('fias_guid', ''),
                    }
                    for c in res
                ]
        except Exception as e:
            logger.warning('CDEK location/cities failed: %s', e)
        # Fallback to predefined cities
        from market_base.delivery.fake import FakeDeliveryProvider
        return FakeDeliveryProvider().autocomplete_cities(q)

    def find_city_code(self, city_name: str) -> Optional[int]:
        q = (city_name or '').strip()
        if not q:
            return None
        cities = self.autocomplete_cities(q)
        for c in cities:
            if c.get('city', '').lower() == q.lower() and c.get('code'):
                return int(c['code'])
        if cities and cities[0].get('code'):
            return int(cities[0]['code'])
        return None

    def get_pickup_points(self, city_code_or_name: str = '') -> list[dict[str, Any]]:
        city_code: Optional[int] = None
        city_name: str = ''
        if str(city_code_or_name).isdigit():
            city_code = int(city_code_or_name)
        elif city_code_or_name:
            city_name = str(city_code_or_name).strip()
            city_code = self.find_city_code(city_name)

        points: list[dict[str, Any]] = []
        seen_codes: set[str] = set()

        # 1. Fetch from CDEK live directory (contains up-to-date points like NLCH9)
        if city_code:
            try:
                resp = requests.get(
                    f'https://integration.cdek.ru/pvzlist/v1/json?cityid={city_code}',
                    timeout=5,
                )
                if resp.ok:
                    data = resp.json()
                    pvz_list = data.get('pvz', [])
                    if isinstance(pvz_list, dict):
                        pvz_list = [pvz_list]
                    for p in pvz_list:
                        code = str(p.get('code', '')).strip()
                        if not code or code in seen_codes:
                            continue
                        seen_codes.add(code)
                        points.append({
                            'code': code,
                            'name': p.get('name') or code,
                            'address': p.get('address') or '',
                            'address_full': p.get('fullAddress') or p.get('address') or '',
                            'phone': p.get('phone') or '',
                            'work_time': p.get('workTime') or '',
                            'note': p.get('note') or p.get('addressComment') or '',
                        })
            except Exception as exc:
                logger.debug('CDEK live pvzlist failed: %s', exc)

        # 2. Query /v2/deliverypoints API
        params: dict[str, Any] = {'country_code': 'RU'}
        if city_code:
            params['city_code'] = city_code
        elif city_name:
            params['city'] = city_name

        try:
            res = self._request('GET', 'deliverypoints', params=params)
            if isinstance(res, list):
                for p in res:
                    code = str(p.get('code', '')).strip()
                    if not code or code in seen_codes:
                        continue
                    seen_codes.add(code)
                    points.append({
                        'code': code,
                        'name': p.get('name') or code,
                        'address': p.get('location', {}).get('address'),
                        'address_full': p.get('location', {}).get('address_full'),
                        'phone': p.get('phones', [{}])[0].get('number', '') if p.get('phones') else '',
                        'work_time': p.get('work_time', ''),
                        'note': p.get('note', ''),
                    })
        except Exception as e:
            logger.warning('CDEK get_pickup_points failed: %s', e)
        return points

    def calculate_rates(
        self,
        *,
        from_address: Address,
        to_address: Address,
        parcels: Sequence[Parcel],
    ) -> list[DeliveryRate]:
        packages = []
        for parcel in parcels:
            pkg: dict[str, Any] = {'weight': max(parcel.weight_grams, 1)}
            if parcel.length_cm:
                pkg['length'] = parcel.length_cm
            if parcel.width_cm:
                pkg['width'] = parcel.width_cm
            if parcel.height_cm:
                pkg['height'] = parcel.height_cm
            packages.append(pkg)

        to_loc: dict[str, Any] = {
            'address': to_address.as_single_line() or to_address.city,
            'city': to_address.city,
            'postal_code': to_address.postal_code or None,
        }
        if to_address.city:
            code = self.find_city_code(to_address.city)
            if code:
                to_loc['code'] = code

        from_code = self.from_city_code
        if from_address.city:
            resolved_from = self.find_city_code(from_address.city)
            if resolved_from:
                from_code = resolved_from

        payload: dict[str, Any] = {
            'type': 1,
            'from_location': {
                'code': from_code,
                'address': from_address.address_line or from_address.city,
            },
            'to_location': {
                k: v for k, v in to_loc.items() if v is not None
            },
            'packages': packages or [{'weight': 500}],
        }

        data = self._request('POST', 'calculator/tarifflist', json=payload)
        tariffs = data.get('tariff_codes') or data.get('tariffs') or []
        rates: list[DeliveryRate] = []
        for tariff in tariffs:
            tariff_code = tariff.get('tariff_code') or tariff.get('code')
            if tariff_code is None:
                continue
            price = Decimal(str(tariff.get('delivery_sum') or tariff.get('sum') or '0'))
            rates.append(
                DeliveryRate(
                    rate_id=str(tariff_code),
                    provider=self.name,
                    service_name=str(tariff.get('tariff_name') or tariff.get('name') or tariff_code),
                    price=price,
                    currency='RUB',
                    min_days=tariff.get('period_min'),
                    max_days=tariff.get('period_max'),
                    meta=dict(tariff),
                )
            )
        rates.sort(key=lambda r: r.price)
        return rates

    def create_shipment(
        self,
        *,
        order_ref: str,
        rate_id: str,
        recipient: Address,
        parcels: Sequence[Parcel],
        sender: Optional[Address] = None,
    ) -> Shipment:
        packages = []
        for idx, parcel in enumerate(parcels, start=1):
            packages.append(
                {
                    'number': str(idx),
                    'weight': max(parcel.weight_grams, 1),
                    'length': parcel.length_cm or 10,
                    'width': parcel.width_cm or 10,
                    'height': parcel.height_cm or 10,
                    'items': [
                        {
                            'name': f'Order {order_ref}',
                            'ware_key': order_ref,
                            'payment': {'value': 0},
                            'cost': 0,
                            'amount': 1,
                            'weight': max(parcel.weight_grams, 1),
                        }
                    ],
                }
            )

        payload: dict[str, Any] = {
            'type': 1,
            'number': order_ref,
            'tariff_code': int(rate_id),
            'recipient': {
                'name': recipient.full_name or 'Recipient',
                'phones': [{'number': recipient.phone or '+70000000000'}],
            },
            'to_location': {
                'address': recipient.as_single_line(),
                'city': recipient.city,
                'postal_code': recipient.postal_code or None,
            },
            'packages': packages or [
                {
                    'number': '1',
                    'weight': 500,
                    'length': 10,
                    'width': 10,
                    'height': 10,
                    'items': [
                        {
                            'name': f'Order {order_ref}',
                            'ware_key': order_ref,
                            'payment': {'value': 0},
                            'cost': 0,
                            'amount': 1,
                            'weight': 500,
                        }
                    ],
                }
            ],
        }
        payload['to_location'] = {
            k: v for k, v in payload['to_location'].items() if v is not None
        }
        if sender:
            payload['from_location'] = {
                'address': sender.as_single_line(),
                'city': sender.city,
            }
        else:
            payload['from_location'] = {'code': self.from_city_code}

        data = self._request('POST', 'orders', json=payload)
        entity = data.get('entity') or data
        requests_info = data.get('requests') or []
        uuid = entity.get('uuid') or (requests_info[0].get('request_uuid') if requests_info else '')
        tracking = entity.get('cdek_number') or entity.get('number') or str(uuid)
        return Shipment(
            shipment_id=str(uuid),
            tracking_number=str(tracking),
            provider=self.name,
            status='created',
            meta=data,
        )

    def track(self, tracking_number: str) -> TrackingInfo:
        data = self._request('GET', f'orders/{tracking_number}')
        entity = data.get('entity') or data
        statuses = entity.get('statuses') or []
        latest = statuses[-1] if statuses else {}
        return TrackingInfo(
            tracking_number=tracking_number,
            status=str(latest.get('code') or entity.get('status') or 'unknown'),
            description=str(latest.get('name') or latest.get('date_time') or ''),
            events=list(statuses),
        )
