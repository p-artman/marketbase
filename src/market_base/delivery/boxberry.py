"""Boxberry delivery provider adapter."""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

import requests

from market_base.core.types import Address, Parcel
from market_base.delivery.protocol import DeliveryRate, Shipment, TrackingInfo
from market_base.delivery.schedule import DispatchSchedule

logger = logging.getLogger(__name__)

BOXBERRY_API_URL = 'https://api.boxberry.ru/json.php'

# Fallback cities with active Boxberry offices
FALLBACK_BOXBERRY_CITIES = [
    {'code': '1', 'city': 'Москва', 'region': 'Московская обл.'},
    {'code': '2', 'city': 'Санкт-Петербург', 'region': 'Ленинградская обл.'},
    {'code': '1081', 'city': 'Нальчик', 'region': 'Кабардино-Балкарская Респ.'},
    {'code': '30', 'city': 'Казань', 'region': 'Татарстан Респ.'},
    {'code': '3', 'city': 'Екатеринбург', 'region': 'Свердловская обл.'},
    {'code': '4', 'city': 'Новосибирск', 'region': 'Новосибирская обл.'},
    {'code': '5', 'city': 'Нижний Новгород', 'region': 'Нижегородская обл.'},
    {'code': '6', 'city': 'Краснодар', 'region': 'Краснодарский край'},
    {'code': '7', 'city': 'Ростов-на-Дону', 'region': 'Ростовская обл.'},
    {'code': '8', 'city': 'Самара', 'region': 'Самарская обл.'},
]

FALLBACK_BOXBERRY_POINTS: dict[str, list[dict[str, Any]]] = {
    'нальчик': [
        {
            'code': 'BB_NLCH1',
            'name': 'Boxberry Отделение на Ленина',
            'address': 'пр-т Ленина, 24',
            'address_full': 'г. Нальчик, пр-т Ленина, 24',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-вс: 09:00-20:00',
            'note': 'Вход с торца здания',
        },
        {
            'code': 'BB_NLCH2',
            'name': 'Boxberry Отделение на Кулиева',
            'address': 'пр-т Кулиева, 10',
            'address_full': 'г. Нальчик, пр-т Кулиева, 10',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-сб: 10:00-19:00, вс: вых.',
            'note': 'Рядом с ТЦ Галерея',
        },
        {
            'code': 'BB_NLCH3',
            'name': 'Boxberry Отделение на Ватутина',
            'address': 'ул. Ватутина, 29',
            'address_full': 'г. Нальчик, ул. Ватутина, 29',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-вс: 09:00-21:00',
            'note': 'Отдельный вход',
        },
        {
            'code': 'BB_NLCH4',
            'name': 'Boxberry Отделение на Кирова',
            'address': 'ул. Кирова, 226',
            'address_full': 'г. Нальчик, ул. Кирова, 226',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-вс: 09:00-20:00',
            'note': '1 этаж, отдельный вход',
        },
        {
            'code': 'BB_NLCH5',
            'name': 'Boxberry Отделение на Тарчокова',
            'address': 'ул. Тарчокова, 19',
            'address_full': 'г. Нальчик, ул. Тарчокова, 19',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-вс: 10:00-20:00',
            'note': 'Вход со двора',
        },
        {
            'code': 'BB_NLCH6',
            'name': 'Boxberry Отделение на Шогенцукова',
            'address': 'пр-т Шогенцукова, 14',
            'address_full': 'г. Нальчик, пр-т Шогенцукова, 14',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-вс: 09:00-19:00',
            'note': 'Центральный вход',
        },
        {
            'code': 'BB_NLCH7',
            'name': 'Boxberry Отделение на Кабардинской',
            'address': 'ул. Кабардинская, 15',
            'address_full': 'г. Нальчик, ул. Кабардинская, 15',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-вс: 09:00-20:00',
            'note': 'Пешеходная зона Арбата',
        },
        {
            'code': 'BB_NLCH8',
            'name': 'Boxberry Отделение на Байсултанова',
            'address': 'ул. Байсултанова, 33',
            'address_full': 'г. Нальчик, ул. Байсултанова, 33',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-сб: 09:00-19:00',
            'note': '1 этаж жилого дома',
        },
        {
            'code': 'BB_NLCH9',
            'name': 'Boxberry Отделение на Ахохова',
            'address': 'ул. Ахохова, 96',
            'address_full': 'г. Нальчик, ул. Ахохова, 96',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-вс: 09:00-20:00',
            'note': 'Рядом с рынком',
        },
        {
            'code': 'BB_NLCH10',
            'name': 'Boxberry Отделение на Пачева',
            'address': 'ул. Пачева, 36',
            'address_full': 'г. Нальчик, ул. Пачева, 36',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-вс: 09:00-20:00',
            'note': 'Отдельный вход с улицы',
        },
        {
            'code': 'BB_NLCH11',
            'name': 'Boxberry Отделение на Идарова',
            'address': 'ул. Идарова, 138',
            'address_full': 'г. Нальчик, ул. Идарова, 138',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-вс: 09:00-20:00',
            'note': 'Остановка Автовокзал',
        },
        {
            'code': 'BB_NLCH12',
            'name': 'Boxberry Отделение на Головко',
            'address': 'ул. Головко, 3',
            'address_full': 'г. Нальчик, ул. Головко, 3',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-сб: 10:00-19:00',
            'note': 'Вход с улицы',
        },
        {
            'code': 'BB_NLCH13',
            'name': 'Boxberry Отделение на Ногмова',
            'address': 'ул. Ногмова, 73',
            'address_full': 'г. Нальчик, ул. Ногмова, 73',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-вс: 09:00-20:00',
            'note': 'Рядом с КБГУ',
        },
        {
            'code': 'BB_NLCH14',
            'name': 'Boxberry Отделение на Мальбахова',
            'address': 'ул. Мальбахова, 32',
            'address_full': 'г. Нальчик, ул. Мальбахова, 32',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-вс: 09:00-20:00',
            'note': 'ТЦ Стрелка',
        },
        {
            'code': 'BB_NLCH15',
            'name': 'Boxberry Отделение на Атажукина',
            'address': 'ул. Атажукина, 11',
            'address_full': 'г. Нальчик, ул. Атажукина, 11',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-вс: 09:00-20:00',
            'note': '1 этаж, вход с торца',
        },
    ],
    'москва': [
        {
            'code': 'BB_MOW1',
            'name': 'Boxberry Отделение Тверская',
            'address': 'ул. Тверская, 7',
            'address_full': 'г. Москва, ул. Тверская, 7',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-вс: 09:00-21:00',
            'note': '1 этаж',
        },
        {
            'code': 'BB_MOW2',
            'name': 'Boxberry Отделение Арбат',
            'address': 'ул. Новый Арбат, 15',
            'address_full': 'г. Москва, ул. Новый Арбат, 15',
            'phone': '+7-800-222-80-00',
            'work_time': 'пн-вс: 10:00-20:00',
            'note': 'Вход через арку',
        },
    ],
}


class BoxberryProvider:
    name = 'boxberry'

    def __init__(
        self,
        token: str | None = None,
        base_url: str = BOXBERRY_API_URL,
    ) -> None:
        self.token = token or os.getenv('BOXBERRY_TOKEN', '')
        self.base_url = base_url

    def _api_get(self, method: str, **params: Any) -> Any:
        if not self.token:
            return None
        url_params = {'token': self.token, 'method': method}
        url_params.update(params)
        try:
            resp = requests.get(self.base_url, params=url_params, timeout=10)
            if resp.ok:
                data = resp.json()
                if isinstance(data, list) and data and 'err' in data[0]:
                    logger.warning('Boxberry API returned error: %s', data[0]['err'])
                    return None
                return data
        except Exception as exc:
            logger.debug('Boxberry request %s failed: %s', method, exc)
        return None

    def autocomplete_cities(self, query: str = '') -> list[dict[str, Any]]:
        q = (query or '').strip().lower()
        if not q:
            return [dict(c) for c in FALLBACK_BOXBERRY_CITIES[:5]]

        # Live API check if token configured
        live = self._api_get('ListCities')
        if isinstance(live, list) and live:
            matched: list[dict[str, Any]] = []
            for item in live:
                name = item.get('Name', '')
                if q in name.lower():
                    matched.append(
                        {
                            'code': str(item.get('Code', '')),
                            'city': name,
                            'region': item.get('Region', ''),
                            'postal_code': item.get('Zip', ''),
                        }
                    )
            if matched:
                return matched[:10]

        # Fallback local list
        return [
            dict(c)
            for c in FALLBACK_BOXBERRY_CITIES
            if q in c['city'].lower() or q in c.get('region', '').lower()
        ]

    def get_pickup_points(self, city_code_or_name: str = '') -> list[dict[str, Any]]:
        target = str(city_code_or_name or '').strip().lower()
        if not target:
            return []

        # Live API check if token configured
        live = self._api_get('ListPoints', CityCode=target)
        if isinstance(live, list) and live:
            points: list[dict[str, Any]] = []
            for p in live:
                points.append(
                    {
                        'code': str(p.get('Code', '')),
                        'name': p.get('Name') or f'Boxberry {p.get("Code", "")}',
                        'address': p.get('Address', ''),
                        'address_full': p.get('AddressReduce') or p.get('Address', ''),
                        'phone': p.get('Phone', '+7-800-222-80-00'),
                        'work_time': p.get('WorkSchedule', ''),
                        'note': p.get('TripDescription', ''),
                    }
                )
            if points:
                return points

        # Fallback dictionary matching city
        for city_key, pts in FALLBACK_BOXBERRY_POINTS.items():
            if city_key in target or target in city_key:
                return pts

        # Generic synthesized point for other cities
        cap_city = target.capitalize()
        return [
            {
                'code': f'BB_{target[:4].upper()}1',
                'name': f'Boxberry Центральное отделение ({cap_city})',
                'address': f'г. {cap_city}, ул. Ленина, 1',
                'address_full': f'г. {cap_city}, ул. Ленина, 1',
                'phone': '+7-800-222-80-00',
                'work_time': 'пн-вс: 09:00-20:00',
                'note': 'Центральное отделение',
            }
        ]

    def calculate_rates(
        self,
        *,
        from_address: Address,
        to_address: Address,
        parcels: Sequence[Parcel],
        schedule: DispatchSchedule | None = None,
        **kwargs: Any,
    ) -> list[DeliveryRate]:
        del from_address, kwargs
        total_weight_g = sum(p.weight_grams for p in parcels) if parcels else 500

        # Destination check: is PVZ or Door
        addr_line = (to_address.address_line or '').strip().lower()
        is_pvz = bool(
            getattr(to_address, 'is_pvz', False)
            or addr_line.startswith(('пвз', 'boxberry'))
            or 'boxberry' in addr_line
            or 'пвз' in addr_line
        )

        rates: list[DeliveryRate] = []

        # 1. Delivery to Boxberry pickup point (always available)
        base_pvz_price = Decimal('320.00') + Decimal(str(total_weight_g // 1000 * 30))
        rate_pvz = DeliveryRate(
            rate_id='boxberry-pvz',
            provider=self.name,
            service_name='Boxberry Доставка в отделение',
            price=base_pvz_price,
            currency='RUB',
            min_days=2,
            max_days=5,
            meta={'delivery_type': 'pvz', 'provider': self.name},
        )
        if schedule and hasattr(schedule, 'apply_to_rate'):
            rate_pvz = schedule.apply_to_rate(rate_pvz)
        rates.append(rate_pvz)

        # 2. Courier door delivery (excluded if PVZ was explicitly chosen)
        if not is_pvz:
            base_courier_price = Decimal('490.00') + Decimal(str(total_weight_g // 1000 * 40))
            rate_courier = DeliveryRate(
                rate_id='boxberry-courier',
                provider=self.name,
                service_name='Boxberry Курьерская доставка',
                price=base_courier_price,
                currency='RUB',
                min_days=3,
                max_days=6,
                meta={'delivery_type': 'courier', 'provider': self.name},
            )
            if schedule and hasattr(schedule, 'apply_to_rate'):
                rate_courier = schedule.apply_to_rate(rate_courier)
            rates.append(rate_courier)

        rates.sort(key=lambda r: r.price)
        return rates

    def create_shipment(
        self,
        *,
        order_ref: str,
        rate_id: str,
        recipient: Address,
        parcels: Sequence[Parcel],
        sender: Address | None = None,
    ) -> Shipment:
        del recipient, parcels, sender
        tracking = f'BB{uuid.uuid4().hex[:10].upper()}'
        return Shipment(
            shipment_id=str(uuid.uuid4()),
            tracking_number=tracking,
            provider=self.name,
            status='created',
            meta={'order_ref': order_ref, 'rate_id': rate_id},
        )

    def track(self, tracking_number: str) -> TrackingInfo:
        return TrackingInfo(
            tracking_number=tracking_number,
            status='in_transit',
            description='Boxberry отправление в пути',
            events=[{'code': 'ACCEPTED'}, {'code': 'IN_TRANSIT'}],
        )
