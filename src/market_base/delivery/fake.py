"""In-memory DeliveryProvider for unit tests."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Optional, Sequence

from market_base.core.types import Address, Parcel
from market_base.delivery.protocol import DeliveryRate, Shipment, TrackingInfo


class FakeDeliveryProvider:
    name = 'fake'

    def calculate_rates(
        self,
        *,
        from_address: Address,
        to_address: Address,
        parcels: Sequence[Parcel],
    ) -> list[DeliveryRate]:
        del from_address, parcels
        weight_factor = Decimal('1')
        return [
            DeliveryRate(
                rate_id='fake-standard',
                provider=self.name,
                service_name=f'Standard to {to_address.city}',
                price=Decimal('350.00') * weight_factor,
                min_days=3,
                max_days=7,
            ),
            DeliveryRate(
                rate_id='fake-express',
                provider=self.name,
                service_name=f'Express to {to_address.city}',
                price=Decimal('650.00') * weight_factor,
                min_days=1,
                max_days=2,
            ),
        ]

    def create_shipment(
        self,
        *,
        order_ref: str,
        rate_id: str,
        recipient: Address,
        parcels: Sequence[Parcel],
        sender: Optional[Address] = None,
    ) -> Shipment:
        del recipient, parcels, sender
        tracking = f'FAKE{uuid.uuid4().hex[:10].upper()}'
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
            description='Fake shipment in transit',
            events=[{'code': 'CREATED'}, {'code': 'IN_TRANSIT'}],
        )

    def autocomplete_cities(self, query: str = '') -> list[dict[str, Any]]:
        default_cities = [
            {'code': 44, 'city': 'Москва', 'region': 'Москва', 'postal_code': '101000'},
            {'code': 137, 'city': 'Санкт-Петербург', 'region': 'Санкт-Петербург', 'postal_code': '190000'},
            {'code': 424, 'city': 'Казань', 'region': 'Татарстан', 'postal_code': '420000'},
            {'code': 270, 'city': 'Новосибирск', 'region': 'Новосибирская обл.', 'postal_code': '630000'},
            {'code': 267, 'city': 'Екатеринбург', 'region': 'Свердловская обл.', 'postal_code': '620000'},
            {'code': 435, 'city': 'Нижний Новгород', 'region': 'Нижегородская обл.', 'postal_code': '603000'},
            {'code': 445, 'city': 'Самара', 'region': 'Самарская обл.', 'postal_code': '443000'},
            {'code': 293, 'city': 'Краснодар', 'region': 'Краснодарский край', 'postal_code': '350000'},
        ]
        q = (query or '').strip().lower()
        if not q:
            return default_cities
        return [c for c in default_cities if q in c['city'].lower() or q in c['region'].lower()]

    def get_pickup_points(self, city_code_or_name: str = '') -> list[dict[str, Any]]:
        city = city_code_or_name or 'Город'
        return [
            {
                'code': 'PVZ1',
                'name': 'ПВЗ Центральный',
                'address': f'{city}, ул. Ленина, 10',
                'phone': '+78001000000',
            },
            {
                'code': 'PVZ2',
                'name': 'ПВЗ Северный',
                'address': f'{city}, пр. Мира, 25',
                'phone': '+78001000000',
            },
        ]
