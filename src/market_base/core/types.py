"""Shared value types used across marketplace provider packages."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = 'RUB'

    def __post_init__(self) -> None:
        object.__setattr__(self, 'amount', Decimal(str(self.amount)))


@dataclass(frozen=True)
class Address:
    city: str
    address_line: str
    postal_code: str = ''
    country_code: str = 'RU'
    region: str = ''
    phone: str = ''
    full_name: str = ''

    def as_single_line(self) -> str:
        parts = [p for p in (self.postal_code, self.city, self.region, self.address_line) if p]
        return ', '.join(parts)


@dataclass(frozen=True)
class Parcel:
    weight_grams: int
    length_cm: Optional[int] = None
    width_cm: Optional[int] = None
    height_cm: Optional[int] = None
