from django.http import JsonResponse

from market_base.django_app.cart import BaseCart
from market_base.django_app.views import (
    autocomplete_delivery_city,
    delivery_pickup_points,
    quote_delivery,
    yookassa_webhook_handler,
)
from shop.models import MessengerCart, Order, Product


class ShopCart(BaseCart):
    product_model = Product
    messenger_cart_model = MessengerCart


def webhook_view(request):
    return yookassa_webhook_handler(request, order_model=Order)


def cart_summary(request):
    cart = ShopCart(request)
    return JsonResponse({
        'total_items': len(cart),
        'total_price': str(cart.get_total_price()),
    })
