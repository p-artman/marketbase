"""Generic dispatch and delivery timeline schedule."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from market_base.delivery.protocol import DeliveryRate

# 0: Monday, 1: Tuesday, 2: Wednesday, 3: Thursday, 4: Friday, 5: Saturday, 6: Sunday
DEFAULT_DISPATCH_WORKING_DAYS = (0, 1, 2, 3, 4, 5)  # Mon-Sat, Sunday off


@dataclass(frozen=True)
class DeliveryTimeline:
    """Calculated timeline for dispatch and delivery."""

    dispatch_date: datetime.date
    dispatch_offset_days: int
    delivery_date_min: datetime.date | None
    delivery_date_max: datetime.date | None
    min_total_days: int | None
    max_total_days: int | None
    formatted_timeline: str


class DispatchSchedule:
    """Calculates dispatch date and total customer delivery days.

    Handles next-day shipping and non-shipping days (e.g. no shipping on Sundays).
    """

    def __init__(
        self,
        working_days: Sequence[int] = DEFAULT_DISPATCH_WORKING_DAYS,
        default_offset_days: int = 1,
    ) -> None:
        self.working_days = set(working_days)
        self.default_offset_days = max(default_offset_days, 1)

    def get_dispatch_date(self, current_date: datetime.date | None = None) -> datetime.date:
        start = current_date or datetime.date.today()
        candidate = start + datetime.timedelta(days=self.default_offset_days)
        for _ in range(7):
            if candidate.weekday() in self.working_days:
                return candidate
            candidate += datetime.timedelta(days=1)
        return candidate

    def get_dispatch_offset_days(self, current_date: datetime.date | None = None) -> int:
        start = current_date or datetime.date.today()
        dispatch = self.get_dispatch_date(start)
        return (dispatch - start).days

    def calculate_timeline(
        self,
        min_transit_days: int | None,
        max_transit_days: int | None,
        current_date: datetime.date | None = None,
    ) -> DeliveryTimeline:
        start = current_date or datetime.date.today()
        dispatch_date = self.get_dispatch_date(start)
        offset = (dispatch_date - start).days

        min_deliv = (
            dispatch_date + datetime.timedelta(days=min_transit_days)
            if min_transit_days is not None
            else None
        )
        max_deliv = (
            dispatch_date + datetime.timedelta(days=max_transit_days)
            if max_transit_days is not None
            else None
        )

        min_total = (min_transit_days + offset) if min_transit_days is not None else None
        max_total = (max_transit_days + offset) if max_transit_days is not None else None

        months = [
            '',
            'янв',
            'фев',
            'мар',
            'апр',
            'мая',
            'июн',
            'июл',
            'авг',
            'сен',
            'окт',
            'ноя',
            'дек',
        ]
        weekdays = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']

        dispatch_str = f'{weekdays[dispatch_date.weekday()]}, {dispatch_date.day} {months[dispatch_date.month]}'

        if min_deliv and max_deliv:
            if min_deliv == max_deliv:
                deliv_str = f'{min_deliv.day} {months[min_deliv.month]}'
            elif min_deliv.month == max_deliv.month:
                deliv_str = f'{min_deliv.day}–{max_deliv.day} {months[max_deliv.month]}'
            else:
                deliv_str = f'{min_deliv.day} {months[min_deliv.month]} – {max_deliv.day} {months[max_deliv.month]}'
            formatted = f'Срок: {min_total}–{max_total} дн. (отправка {dispatch_str}, доставка {deliv_str})'
        else:
            formatted = f'Отправка: {dispatch_str}'

        return DeliveryTimeline(
            dispatch_date=dispatch_date,
            dispatch_offset_days=offset,
            delivery_date_min=min_deliv,
            delivery_date_max=max_deliv,
            min_total_days=min_total,
            max_total_days=max_total,
            formatted_timeline=formatted,
        )

    def apply_to_rate(
        self,
        rate: DeliveryRate,
        current_date: datetime.date | None = None,
    ) -> DeliveryRate:
        timeline = self.calculate_timeline(
            min_transit_days=rate.min_days,
            max_transit_days=rate.max_days,
            current_date=current_date,
        )
        meta: dict[str, Any] = dict(rate.meta or {})
        meta.update(
            {
                'dispatch_date': timeline.dispatch_date.isoformat(),
                'dispatch_offset_days': timeline.dispatch_offset_days,
                'delivery_date_min': (
                    timeline.delivery_date_min.isoformat()
                    if timeline.delivery_date_min
                    else None
                ),
                'delivery_date_max': (
                    timeline.delivery_date_max.isoformat()
                    if timeline.delivery_date_max
                    else None
                ),
                'formatted_timeline': timeline.formatted_timeline,
            }
        )
        return DeliveryRate(
            rate_id=rate.rate_id,
            provider=rate.provider,
            service_name=rate.service_name,
            price=rate.price,
            currency=rate.currency,
            min_days=timeline.min_total_days,
            max_days=timeline.max_total_days,
            meta=meta,
        )
