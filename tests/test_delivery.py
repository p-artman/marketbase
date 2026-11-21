"""Unit tests for market_base.delivery contracts and providers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from market_base.core.types import Address, Parcel
from market_base.delivery.cdek import CdekProvider
from market_base.delivery.fake import FakeDeliveryProvider
from market_base.delivery.protocol import DeliveryProvider


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
