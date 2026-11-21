"""DeliveryProvider contract shared by carrier adapters."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from market_base.core.types import Address, Parcel


@dataclass(frozen=True)
class DeliveryRate:
    rate_id: str
    provider: str
    service_name: str
    price: Decimal
    currency: str = 'RUB'
    min_days: int | None = None
    max_days: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Shipment:
    shipment_id: str
    tracking_number: str
    provider: str
    status: str = 'created'
    label_url: str = ''
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TrackingInfo:
    tracking_number: str
    status: str
    description: str = ''
    events: list[dict[str, Any]] = field(default_factory=list)


@runtime_checkable
class DeliveryProvider(Protocol):
    name: str

    def calculate_rates(
        self,
        *,
        from_address: Address,
        to_address: Address,
        parcels: Sequence[Parcel],
        schedule: Any | None = None,
        **kwargs: Any,
    ) -> list[DeliveryRate]: ...

    def create_shipment(
        self,
        *,
        order_ref: str,
        rate_id: str,
        recipient: Address,
        parcels: Sequence[Parcel],
        sender: Address | None = None,
    ) -> Shipment: ...

    def track(self, tracking_number: str) -> TrackingInfo: ...

    def autocomplete_cities(self, query: str) -> list[dict[str, Any]]: ...

    def get_pickup_points(self, city_code_or_name: str) -> list[dict[str, Any]]: ...
