from django.contrib import admin

from market_base.django_app.admin import (
    BaseCategoryAdmin,
    BaseMessengerCartAdmin,
    BaseOrderAdmin,
    BaseOrderItemInline,
    BaseProductAdmin,
)
from shop.models import Category, MessengerCart, Order, OrderItem, Product


@admin.register(Category)
class CategoryAdmin(BaseCategoryAdmin):
    pass


@admin.register(Product)
class ProductAdmin(BaseProductAdmin):
    pass


class OrderItemInline(BaseOrderItemInline):
    model = OrderItem


@admin.register(Order)
class OrderAdmin(BaseOrderAdmin):
    inlines = [OrderItemInline]


@admin.register(MessengerCart)
class MessengerCartAdmin(BaseMessengerCartAdmin):
    pass
