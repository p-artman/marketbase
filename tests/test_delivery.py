"""Unit tests for market_base.delivery contracts and providers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from market_base.core.types import Address, Parcel
from market_base.delivery.boxberry import BoxberryProvider
from market_base.delivery.cdek import CdekProvider
from market_base.delivery.factory import get_available_providers, get_delivery_provider
from market_base.delivery.fake import FakeDeliveryProvider
from market_base.delivery.fivepost import FivePostProvider
from market_base.delivery.protocol import DeliveryProvider
from market_base.delivery.schedule import DispatchSchedule


def test_dispatch_schedule_next_day_and_weekend():
    import datetime
    schedule = DispatchSchedule(working_days=(0, 1, 2, 3, 4, 5), default_offset_days=1)

    # Friday (2026-11-20 is Friday) -> next day Saturday
    friday = datetime.date(2026, 11, 20)
    assert friday.weekday() == 4
    assert schedule.get_dispatch_date(friday) == datetime.date(2026, 11, 21)
    assert schedule.get_dispatch_offset_days(friday) == 1

    # Saturday (2026-11-21 is Saturday) -> Sunday closed -> Monday 2026-11-23 (+2 days)
    saturday = datetime.date(2026, 11, 21)
    assert saturday.weekday() == 5
    assert schedule.get_dispatch_date(saturday) == datetime.date(2026, 11, 23)
    assert schedule.get_dispatch_offset_days(saturday) == 2

    # Sunday (2026-11-22 is Sunday) -> Monday 2026-11-23 (+1 day)
    sunday = datetime.date(2026, 11, 22)
    assert sunday.weekday() == 6
    assert schedule.get_dispatch_date(sunday) == datetime.date(2026, 11, 23)
    assert schedule.get_dispatch_offset_days(sunday) == 1


def test_dispatch_schedule_timeline_formatting():
    import datetime

    from market_base.delivery.protocol import DeliveryRate
    schedule = DispatchSchedule(working_days=(0, 1, 2, 3, 4, 5))
    saturday = datetime.date(2026, 11, 21)

    rate = DeliveryRate(
        rate_id='136',
        provider='cdek',
        service_name='Посылка склад-склад',
        price=Decimal('350.00'),
        min_days=2,
        max_days=4,
    )
    enriched = schedule.apply_to_rate(rate, current_date=saturday)
    assert enriched.min_days == 2 + 2  # transit 2 + offset 2
    assert enriched.max_days == 4 + 2  # transit 4 + offset 2
    assert enriched.meta['dispatch_date'] == '2026-11-23'
    assert 'отправка пн, 23 ноя' in enriched.meta['formatted_timeline']


def test_cdek_calculate_rates_filtering(monkeypatch):
    provider = CdekProvider(client_id='mock', client_secret='mock')
    monkeypatch.setattr(provider, '_authenticate', lambda: 'mock-token')
    
    mock_tariffs = [
        {
            'tariff_code': 136,
            'tariff_name': 'Посылка склад-склад',
            'delivery_mode': 4,
            'delivery_sum': 320,
            'period_min': 2,
            'period_max': 3,
        },
        {
            'tariff_code': 137,
            'tariff_name': 'Посылка склад-дверь',
            'delivery_mode': 3,
            'delivery_sum': 480,
            'period_min': 2,
            'period_max': 4,
        },
        {
            'tariff_code': 138,
            'tariff_name': 'Посылка дверь-склад',
            'delivery_mode': 2,
            'delivery_sum': 500,
            'period_min': 2,
            'period_max': 4,
        },
        {
            'tariff_code': 139,
            'tariff_name': 'Посылка дверь-дверь',
            'delivery_mode': 1,
            'delivery_sum': 650,
            'period_min': 2,
            'period_max': 4,
        },
    ]

    monkeypatch.setattr(
        provider,
        '_request',
        lambda method, path, **kwargs: {'tariff_codes': mock_tariffs},
    )

    # 1. When destination is PVZ: ONLY mode 4 (склад-склад) should remain
    rates_pvz = provider.calculate_rates(
        from_address=Address(city='Москва', address_line='Склад'),
        to_address=Address(city='Нальчик', address_line='ПВЗ СДЭК [NLCH9]: пр-т. Кулиева, 2'),
        parcels=[Parcel(weight_grams=500)],
    )
    assert len(rates_pvz) == 1
    assert rates_pvz[0].rate_id == '136'
    assert rates_pvz[0].service_name == 'Посылка склад-склад'

    # 2. When destination is door address: warehouse delivery is NEVER removed, so both warehouse (136) and door (137) remain
    rates_door = provider.calculate_rates(
        from_address=Address(city='Москва', address_line='Склад'),
        to_address=Address(city='Нальчик', address_line='ул. Ленина, 15, кв. 4'),
        parcels=[Parcel(weight_grams=500)],
    )
    assert len(rates_door) == 2
    assert any(r.rate_id == '136' for r in rates_door)
    assert any(r.rate_id == '137' for r in rates_door)



def test_fake_delivery_satisfies_protocol():
    provider = FakeDeliveryProvider()
    assert isinstance(provider, DeliveryProvider)


def test_fake_rates():
    provider = FakeDeliveryProvider()
    rates = provider.calculate_rates(
        from_address=Address(city='Москва', address_line='Склад'),
        to_address=Address(city='Казань', address_line='ул. Баумана, 1'),
        parcels=[Parcel(weight_grams=500)],
    )
    assert len(rates) >= 2
    assert any(r.rate_id == 'fake-standard' for r in rates)
    assert any(r.rate_id == 'fake-express' for r in rates)
    assert all(r.price > 0 for r in rates)


def test_fake_autocomplete_and_pvz():
    provider = FakeDeliveryProvider()
    cities = provider.autocomplete_cities('Санкт')
    assert len(cities) >= 1
    assert 'Санкт-Петербург' in cities[0]['city']

    points = provider.get_pickup_points('Казань')
    assert len(points) >= 2
    assert points[0]['code'] == 'PVZ1'


def test_boxberry_provider():
    provider = BoxberryProvider()
    assert isinstance(provider, DeliveryProvider)
    assert provider.name == 'boxberry'

    cities = provider.autocomplete_cities('Наль')
    assert len(cities) >= 1
    assert cities[0]['city'] == 'Нальчик'

    points = provider.get_pickup_points('Нальчик')
    assert len(points) >= 2
    assert any('Кулиева' in p['address'] for p in points)

    # Calculate rates to PVZ
    rates_pvz = provider.calculate_rates(
        from_address=Address(city='Москва', address_line='Склад'),
        to_address=Address(city='Нальчик', address_line='ПВЗ Boxberry [BB_NLCH2]: пр-т Кулиева, 10'),
        parcels=[Parcel(weight_grams=500)],
    )
    assert len(rates_pvz) == 1
    assert rates_pvz[0].rate_id == 'boxberry-pvz'

    # Calculate rates to door address
    rates_door = provider.calculate_rates(
        from_address=Address(city='Москва', address_line='Склад'),
        to_address=Address(city='Нальчик', address_line='ул. Ленина, 15'),
        parcels=[Parcel(weight_grams=500)],
    )
    assert len(rates_door) == 2


def test_fivepost_provider():
    provider = FivePostProvider()
    assert isinstance(provider, DeliveryProvider)
    assert provider.name == 'fivepost'

    cities = provider.autocomplete_cities('Наль')
    assert len(cities) >= 1
    assert cities[0]['city'] == 'Нальчик'

    points = provider.get_pickup_points('Нальчик')
    assert len(points) >= 2
    assert any('Пятёрочка' in p['name'] for p in points)

    rates = provider.calculate_rates(
        from_address=Address(city='Москва', address_line='Склад'),
        to_address=Address(city='Нальчик', address_line='Постамат 5Post (Пятёрочка)'),
        parcels=[Parcel(weight_grams=500)],
    )
    assert len(rates) == 1
    assert rates[0].provider == 'fivepost'


def test_delivery_factory_multi_provider():
    assert 'cdek' in get_available_providers()
    assert 'boxberry' in get_available_providers()
    assert 'fivepost' in get_available_providers()

    cdek = get_delivery_provider('cdek')
    assert isinstance(cdek, CdekProvider)

    bb = get_delivery_provider('boxberry')
    assert isinstance(bb, BoxberryProvider)

    fp = get_delivery_provider('fivepost')
    assert isinstance(fp, FivePostProvider)



@pytest.mark.integration
def test_cdek_live_sandbox():
    import os
    if not (os.getenv('CDEK_CLIENT_ID') and os.getenv('CDEK_CLIENT_SECRET')):
        pytest.skip('CDEK credentials not set')
    provider = CdekProvider()
    cities = provider.autocomplete_cities('Наль')
    assert len(cities) > 0
    assert any('Нальчик' in c.get('city', '') for c in cities)

    points = provider.get_pickup_points('Нальчик')
    assert len(points) >= 3
    assert any(p.get('code') == 'NLCH9' for p in points)
