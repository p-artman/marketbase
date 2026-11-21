"""Concrete shop models inheriting from market_base abstract classes."""

from django.db import models

from market_base.django_app.models import (
    AbstractCategory,
    AbstractMessengerCart,
    AbstractOrder,
    AbstractOrderItem,
    AbstractProduct,
)


class Category(AbstractCategory):
    pass


class Product(AbstractProduct):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
    )


class MessengerCart(AbstractMessengerCart):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['platform', 'user_id'],
                name='demo_uniq_messenger_cart',
            )
        ]


class Order(AbstractOrder):
    pass


class OrderItem(AbstractOrderItem):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
