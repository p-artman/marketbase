"""BaseCart session management with optional messenger persistence."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Type

from django.conf import settings

MESSENGER_SESSION_KEY = 'bsl_messenger_user'
MESSENGER_CART_LOADED_KEY = 'bsl_messenger_cart_loaded'


class BaseCart:
    """Session cart with optional messenger-user persistence across WebViews."""

    product_model: Type[Any] = None
    messenger_cart_model: Type[Any] = None

    def __init__(self, request, product_model=None, messenger_cart_model=None):
        self.request = request
        self.session = request.session
        self.product_model = product_model or self.product_model
        self.messenger_cart_model = messenger_cart_model or self.messenger_cart_model

        messenger = self.session.get(MESSENGER_SESSION_KEY) or {}
        self._platform = (messenger.get('messenger_platform') or '').strip() or None
        try:
            self._user_id = (
                int(messenger['telegram_user_id'])
                if messenger.get('telegram_user_id')
                else None
            )
        except (TypeError, ValueError):
            self._user_id = None

        cart_session_id = getattr(settings, 'CART_SESSION_ID', 'cart')
        session_cart = self.session.get(cart_session_id)
        if not isinstance(session_cart, dict):
            session_cart = {}

        session_cart = self._serialize_items(session_cart)

        # Sync from DB if messenger cart is bound and not loaded yet
        if (
            self._platform
            and self._user_id
            and self.messenger_cart_model
            and not self.session.get(MESSENGER_CART_LOADED_KEY)
        ):
            row = self.messenger_cart_model.objects.filter(
                platform=self._platform,
                user_id=self._user_id,
            ).only('items').first()
            if row and row.items:
                session_cart = self._merge_items(row.items, session_cart)
            self.session[MESSENGER_CART_LOADED_KEY] = True
            self.session.modified = True

        self.session[cart_session_id] = session_cart
        self.cart = session_cart

    @staticmethod
    def _serialize_items(items: dict) -> dict:
        out = {}
        for product_id, item in (items or {}).items():
            out[str(product_id)] = {
                'quantity': int(item.get('quantity') or 0),
                'price': str(item.get('price') or '0'),
            }
        return out

    @classmethod
    def _merge_items(cls, primary: dict, overlay: dict) -> dict:
        merged = cls._serialize_items(primary)
        for product_id, item in cls._serialize_items(overlay).items():
            if product_id not in merged:
                merged[product_id] = item
                continue
            merged[product_id] = {
                'quantity': max(merged[product_id]['quantity'], item['quantity']),
                'price': item['price'] or merged[product_id]['price'],
            }
        return {k: v for k, v in merged.items() if v['quantity'] > 0}

    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': str(product.price),
            }

        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity

        self.save()

    def save(self):
        cart_session_id = getattr(settings, 'CART_SESSION_ID', 'cart')
        self.cart = self._serialize_items(self.cart)
        self.session[cart_session_id] = self.cart
        self.session.modified = True
        if self._platform and self._user_id and self.messenger_cart_model:
            self.messenger_cart_model.objects.update_or_create(
                platform=self._platform,
                user_id=self._user_id,
                defaults={'items': self.cart},
            )

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        if not self.product_model:
            return iter([])
        products = {
            str(p.id): p
            for p in self.product_model.objects.filter(id__in=list(self.cart.keys()))
        }
        for product_id, item in self.cart.items():
            product = products.get(str(product_id))
            if product is None:
                continue
            price = Decimal(str(item.get('price') or '0'))
            quantity = int(item.get('quantity') or 0)
            yield {
                'product': product,
                'quantity': quantity,
                'price': price,
                'total_price': price * quantity,
            }

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self) -> Decimal:
        return sum(
            Decimal(item['price']) * item['quantity'] for item in self.cart.values()
        )

    def clear(self):
        cart_session_id = getattr(settings, 'CART_SESSION_ID', 'cart')
        self.cart = {}
        self.session[cart_session_id] = {}
        self.session.modified = True
        if self._platform and self._user_id and self.messenger_cart_model:
            self.messenger_cart_model.objects.filter(
                platform=self._platform,
                user_id=self._user_id,
            ).update(items={})

    def get_item_quantity(self, product_id):
        product_id = str(product_id)
        if product_id in self.cart:
            return self.cart[product_id]['quantity']
        return 0


def session_cart_count(session) -> int:
    """Fast badge count from session only (no DB calls)."""
    cart_session_id = getattr(settings, 'CART_SESSION_ID', 'cart')
    cart = session.get(cart_session_id) or {}
    if not isinstance(cart, dict):
        return 0
    total = 0
    for item in cart.values():
        try:
            total += int(item.get('quantity') or 0)
        except (TypeError, ValueError, AttributeError):
            continue
    return total
