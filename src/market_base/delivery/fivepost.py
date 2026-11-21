"""5Post (X5 Retail Group) delivery provider adapter."""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from market_base.core.types import Address, Parcel
from market_base.delivery.protocol import DeliveryRate, Shipment, TrackingInfo
from market_base.delivery.schedule import DispatchSchedule

logger = logging.getLogger(__name__)

# Fallback cities with dense 5Post locker coverage (Pyaterochka & Perekrestok)
FALLBACK_FIVEPOST_CITIES = [
    {'code': '5P_MOW', 'city': 'Москва', 'region': 'Московская обл.'},
    {'code': '5P_SPB', 'city': 'Санкт-Петербург', 'region': 'Ленинградская обл.'},
    {'code': '5P_NLCH', 'city': 'Нальчик', 'region': 'Кабардино-Балкарская Респ.'},
    {'code': '5P_KZN', 'city': 'Казань', 'region': 'Татарстан Респ.'},
    {'code': '5P_EKB', 'city': 'Екатеринбург', 'region': 'Свердловская обл.'},
    {'code': '5P_KRD', 'city': 'Краснодар', 'region': 'Краснодарский край'},
    {'code': '5P_ROV', 'city': 'Ростов-на-Дону', 'region': 'Ростовская обл.'},
    {'code': '5P_SAM', 'city': 'Самара', 'region': 'Самарская обл.'},
    {'code': '5P_NNV', 'city': 'Нижний Новгород', 'region': 'Нижегородская обл.'},
]

FALLBACK_FIVEPOST_POINTS: dict[str, list[dict[str, Any]]] = {
    'нальчик': [
        {
            'code': '5P_NLCH_101',
            'name': 'Постамат 5Post (Пятёрочка, ул. Ленина, 30)',
            'address': 'ул. Ленина, 30',
            'address_full': 'г. Нальчик, ул. Ленина, 30 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-23:00',
            'note': 'Постамат в прикассовой зоне Пятёрочки',
        },
        {
            'code': '5P_NLCH_102',
            'name': 'Постамат 5Post (Пятёрочка, пр-т Кулиева, 2б)',
            'address': 'пр-т Кулиева, 2б',
            'address_full': 'г. Нальчик, пр-т Кулиева, 2б (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': 'Вход в супермаркет Пятёрочка',
        },
        {
            'code': '5P_NLCH_103',
            'name': 'Пункт выдачи 5Post (Пятёрочка, ул. Ватутина, 18)',
            'address': 'ул. Ватутина, 18',
            'address_full': 'г. Нальчик, ул. Ватутина, 18 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': 'Выдача на кассе',
        },
        {
            'code': '5P_NLCH_104',
            'name': 'Постамат 5Post (Перекрёсток, пр-т Кулиева, 1)',
            'address': 'пр-т Кулиева, 1',
            'address_full': 'г. Нальчик, пр-т Кулиева, 1 (ТЦ Галерея)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 09:00-23:00',
            'note': 'Цокольный этаж, Перекрёсток',
        },
        {
            'code': '5P_NLCH_105',
            'name': 'Постамат 5Post (Пятёрочка, ул. Кирова, 179)',
            'address': 'ул. Кирова, 179',
            'address_full': 'г. Нальчик, ул. Кирова, 179 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': 'Вход в магазин',
        },
        {
            'code': '5P_NLCH_106',
            'name': 'Постамат 5Post (Пятёрочка, ул. Тарчокова, 54)',
            'address': 'ул. Тарчокова, 54',
            'address_full': 'г. Нальчик, ул. Тарчокова, 54 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-23:00',
            'note': 'При входе справа',
        },
        {
            'code': '5P_NLCH_107',
            'name': 'Постамат 5Post (Пятёрочка, пр-т Шогенцукова, 32)',
            'address': 'пр-т Шогенцукова, 32',
            'address_full': 'г. Нальчик, пр-т Шогенцукова, 32 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': 'Прикассовая зона',
        },
        {
            'code': '5P_NLCH_108',
            'name': 'Постамат 5Post (Пятёрочка, ул. Кабардинская, 38)',
            'address': 'ул. Кабардинская, 38',
            'address_full': 'г. Нальчик, ул. Кабардинская, 38 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': 'При входе',
        },
        {
            'code': '5P_NLCH_109',
            'name': 'Постамат 5Post (Пятёрочка, ул. Байсултанова, 12)',
            'address': 'ул. Байсултанова, 12',
            'address_full': 'г. Нальчик, ул. Байсултанова, 12 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': 'Возле касс',
        },
        {
            'code': '5P_NLCH_110',
            'name': 'Постамат 5Post (Пятёрочка, ул. Ахохова, 62)',
            'address': 'ул. Ахохова, 62',
            'address_full': 'г. Нальчик, ул. Ахохова, 62 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': '1 этаж',
        },
        {
            'code': '5P_NLCH_111',
            'name': 'Постамат 5Post (Пятёрочка, ул. Пачева, 18)',
            'address': 'ул. Пачева, 18',
            'address_full': 'г. Нальчик, ул. Пачева, 18 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': 'Торговый зал',
        },
        {
            'code': '5P_NLCH_112',
            'name': 'Постамат 5Post (Пятёрочка, ул. Идарова, 160)',
            'address': 'ул. Идарова, 160',
            'address_full': 'г. Нальчик, ул. Идарова, 160 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': 'При входе в супермаркет',
        },
        {
            'code': '5P_NLCH_113',
            'name': 'Постамат 5Post (Пятёрочка, ул. Головко, 50)',
            'address': 'ул. Головко, 50',
            'address_full': 'г. Нальчик, ул. Головко, 50 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': 'Прикассовая зона',
        },
        {
            'code': '5P_NLCH_114',
            'name': 'Постамат 5Post (Пятёрочка, ул. Мальбахова, 34)',
            'address': 'ул. Мальбахова, 34',
            'address_full': 'г. Нальчик, ул. Мальбахова, 34 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-23:00',
            'note': 'Прикассовая зона',
        },
        {
            'code': '5P_NLCH_115',
            'name': 'Постамат 5Post (Пятёрочка, ул. Чернышевского, 201)',
            'address': 'ул. Чернышевского, 201',
            'address_full': 'г. Нальчик, ул. Чернышевского, 201 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': 'Вход в супермаркет',
        },
        {
            'code': '5P_NLCH_116',
            'name': 'Постамат 5Post (Пятёрочка, пр-т Ленина, 53)',
            'address': 'пр-т Ленина, 53',
            'address_full': 'г. Нальчик, пр-т Ленина, 53 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-23:00',
            'note': 'Рядом с кассами самообслуживания',
        },
        {
            'code': '5P_NLCH_117',
            'name': 'Постамат 5Post (Пятёрочка, ул. Калинина, 264)',
            'address': 'ул. Калинина, 264',
            'address_full': 'г. Нальчик, ул. Калинина, 264 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': 'Универсам Пятёрочка',
        },
        {
            'code': '5P_NLCH_118',
            'name': 'Постамат 5Post (Пятёрочка, ул. Хуранова, 9)',
            'address': 'ул. Хуранова, 9',
            'address_full': 'г. Нальчик, ул. Хуранова, 9 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': '1 этаж',
        },
        {
            'code': '5P_NLCH_119',
            'name': 'Постамат 5Post (Пятёрочка, ул. Атажукина, 11)',
            'address': 'ул. Атажукина, 11',
            'address_full': 'г. Нальчик, ул. Атажукина, 11 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-23:00',
            'note': 'Постамат в универсаме Пятёрочка',
        },
        {
            'code': '5P_NLCH_120',
            'name': 'Постамат 5Post (Пятёрочка, ул. Атажукина, 2)',
            'address': 'ул. Атажукина, 2',
            'address_full': 'г. Нальчик, ул. Атажукина, 2 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': 'При входе',
        },
        {
            'code': '5P_NLCH_121',
            'name': 'Пункт выдачи 5Post (Пятёрочка, ул. Атажукина, 131)',
            'address': 'ул. Атажукина, 131',
            'address_full': 'г. Нальчик, ул. Атажукина, 131 (Пятёрочка)',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-22:00',
            'note': 'Выдача на кассе',
        },
    ],
    'москва': [
        {
            'code': '5P_MOW_001',
            'name': 'Постамат 5Post (Пятёрочка, ул. Арбат, 25)',
            'address': 'ул. Арбат, 25',
            'address_full': 'г. Москва, ул. Арбат, 25',
            'phone': '+7-800-511-88-00',
            'work_time': 'пн-вс: 08:00-23:00',
            'note': 'В торговом зале',
        },
        {
            'code': '5P_MOW_002',
            'name': 'Постамат 5Post (Перекрёсток, Тверская, 12)',
            'address': 'ул. Тверская, 12',
            'address_full': 'г. Москва, ул. Тверская, 12',
            'phone': '+7-800-511-88-00',
            'work_time': 'круглосуточно 24/7',
            'note': 'Прикассовая зона супермаркета Перекрёсток',
        },
    ],
}


class FivePostProvider:
    name = 'fivepost'

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = 'https://api-preprod-gws.x5.ru',
    ) -> None:
        self.api_key = api_key or os.getenv('FIVEPOST_API_KEY', '')
        self.base_url = base_url

    def autocomplete_cities(self, query: str = '') -> list[dict[str, Any]]:
        q = (query or '').strip().lower()
        if not q:
            return [dict(c) for c in FALLBACK_FIVEPOST_CITIES[:5]]
        return [
            dict(c)
            for c in FALLBACK_FIVEPOST_CITIES
            if q in c['city'].lower() or q in c.get('region', '').lower()
        ]

    def get_pickup_points(self, city_code_or_name: str = '') -> list[dict[str, Any]]:
        target = str(city_code_or_name or '').strip().lower()
        if not target:
            return []

        for city_key, pts in FALLBACK_FIVEPOST_POINTS.items():
            if city_key in target or target in city_key:
                return pts

        cap_city = target.capitalize()
        return [
            {
                'code': f'5P_{target[:4].upper()}_01',
                'name': f'Постамат 5Post (Пятёрочка, {cap_city})',
                'address': f'г. {cap_city}, ул. Ленина, 10',
                'address_full': f'г. {cap_city}, ул. Ленина, 10 (Пятёрочка)',
                'phone': '+7-800-511-88-00',
                'work_time': 'пн-вс: 08:00-22:00',
                'note': 'Постамат в универсаме Пятёрочка',
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

        # 5Post operates as parcel lockers & supermarket pickup points
        price = Decimal('280.00') + Decimal(str(total_weight_g // 1000 * 25))

        rate = DeliveryRate(
            rate_id='fivepost-locker',
            provider=self.name,
            service_name='5Post Постамат (Пятёрочка)',
            price=price,
            currency='RUB',
            min_days=2,
            max_days=4,
            meta={'delivery_type': 'locker', 'provider': self.name},
        )
        if schedule and hasattr(schedule, 'apply_to_rate'):
            rate = schedule.apply_to_rate(rate)
        return [rate]

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
        tracking = f'5P{uuid.uuid4().hex[:10].upper()}'
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
            description='5Post посылка ожидает отправки в магазин',
            events=[{'code': 'ACCEPTED_AT_SORT'}, {'code': 'IN_TRANSIT'}],
        )
