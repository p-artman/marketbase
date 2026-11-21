"""Reusable generic views and API endpoints for delivery, payments and messengers."""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any, Optional, Type

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from market_base.core.types import Address, Parcel
from market_base.delivery import get_delivery_provider
from market_base.messengers import (
    MaxAuthError,
    MaxPlatform,
    TelegramAuthError,
    TelegramPlatform,
    get_messenger_platform,
)
from market_base.notifications import OrderEmailPayload, get_email_notifier
from market_base.payments import get_payment_provider

logger = logging.getLogger(__name__)


def sender_address() -> Address:
    return Address(
        city=getattr(settings, 'DELIVERY_FROM_CITY', 'Москва'),
        address_line=getattr(settings, 'DELIVERY_FROM_ADDRESS', 'Склад'),
        postal_code=getattr(settings, 'DELIVERY_FROM_POSTAL', '101000'),
    )


@require_POST
def quote_delivery(request: HttpRequest) -> JsonResponse:
    """Calculate shipping tariffs via the active DeliveryProvider."""
    try:
        data = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    city = (data.get('city') or '').strip()
    address_line = (data.get('address') or '').strip()
    postal_code = (data.get('postal_code') or '').strip()
    if not city and not address_line:
        return JsonResponse({'error': 'city or address is required'}, status=400)

    weight_grams = int(data.get('weight_grams') or 500)
    to_addr = Address(
        city=city,
        address_line=address_line,
        postal_code=postal_code,
    )
    provider = get_delivery_provider()
    try:
        rates = provider.calculate_rates(
            from_address=sender_address(),
            to_address=to_addr,
            parcels=[Parcel(weight_grams=weight_grams)],
        )
    except Exception as e:
        logger.exception('Delivery calculation failed: %s', e)
        return JsonResponse({'error': 'Delivery calculation unavailable', 'detail': str(e)}, status=502)

    return JsonResponse(
        {
            'rates': [
                {
                    'rate_id': r.rate_id,
                    'provider': r.provider,
                    'service_name': r.service_name,
                    'price': str(r.price),
                    'currency': r.currency,
                    'min_days': r.min_days,
                    'max_days': r.max_days,
                }
                for r in rates
            ]
        }
    )


@require_GET
def autocomplete_delivery_city(request: HttpRequest) -> JsonResponse:
    """Autocomplete Russian cities via the active DeliveryProvider."""
    q = (request.GET.get('q') or '').strip()
    provider = get_delivery_provider()
    cities = provider.autocomplete_cities(q)
    return JsonResponse({'cities': cities})


@require_GET
def delivery_pickup_points(request: HttpRequest) -> JsonResponse:
    """Return pickup points (ПВЗ) for a city via active DeliveryProvider."""
    city = (request.GET.get('city') or '').strip()
    provider = get_delivery_provider()
    points = provider.get_pickup_points(city)
    return JsonResponse({'pickup_points': points})


@csrf_exempt
@require_POST
def bind_messenger(request: HttpRequest) -> JsonResponse:
    """Bind WebApp initData (Telegram or MAX) to Django session."""
    try:
        data = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = {}

    platform_name = (
        data.get('messenger_platform')
        or request.headers.get('X-Messenger-Platform')
        or 'telegram'
    ).strip().lower()

    init_data = (
        data.get('init_data')
        or request.headers.get('X-Telegram-Init-Data')
        or request.headers.get('X-Max-Init-Data')
        or ''
    )

    try:
        platform = get_messenger_platform()
        user = platform.validate_init_data(init_data)
        request.session['bsl_messenger_user'] = {
            'messenger_platform': user.platform,
            'telegram_user_id': user.user_id,
            'telegram_username': user.username,
            'telegram_first_name': user.first_name,
            'telegram_last_name': user.last_name,
            'language_code': user.language_code,
        }
        request.session.modified = True
        return JsonResponse({'status': 'ok', 'user_id': user.user_id, 'platform': user.platform})
    except (TelegramAuthError, MaxAuthError, ValueError) as exc:
        return JsonResponse({'status': 'error', 'detail': str(exc)}, status=400)


@csrf_exempt
@require_POST
def yookassa_webhook_handler(request: HttpRequest, order_model: Type[Any]) -> JsonResponse:
    """Process incoming YooKassa payment notifications and update order status."""
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'status': 'invalid json'}, status=400)

    provider = get_payment_provider()
    event = provider.parse_webhook(payload)

    if event.payment_id:
        order = order_model.objects.filter(payment_id=event.payment_id).first()
        if order:
            if event.status == 'success':
                order.payment_status = 'succeeded'
                if order.status == 'pending':
                    order.status = 'confirmed'
                order.save()
                notify_order_paid(order)
            elif event.status == 'canceled':
                order.payment_status = 'canceled'
                order.status = 'cancelled'
                order.save()

    return JsonResponse({'status': 'ok'})


def notify_order_paid(order: Any) -> None:
    """Send notifications via messenger bot and customer email."""
    # Email confirmation
    if getattr(order, 'customer_email', None):
        try:
            notifier = get_email_notifier()
            notifier.send_payment_receipt(
                OrderEmailPayload(
                    to_email=order.customer_email,
                    order_id=str(order.id),
                    customer_name=order.customer_name,
                    total_amount=order.total_amount,
                    payment_status='succeeded',
                    shipping_address=order.shipping_address,
                    tracking_number=getattr(order, 'tracking_number', ''),
                ),
                payment_id=getattr(order, 'payment_id', ''),
            )
        except Exception as e:
            logger.warning('Failed to send order email: %s', e)

    # Messenger message
    user_id = getattr(order, 'telegram_user_id', None)
    if user_id:
        try:
            platform = get_messenger_platform()
            text = (
                f'✅ Оплата по заказу #{order.id} успешно получена!\n'
                f'Сумма: {order.total_amount} RUB\n'
                f'Адрес доставки: {order.shipping_address}\n\n'
                f'Мы начинаем сборку вашего заказа.'
            )
            platform.notify_user(str(user_id), text)
        except Exception as e:
            logger.warning('Failed to send messenger notification: %s', e)
