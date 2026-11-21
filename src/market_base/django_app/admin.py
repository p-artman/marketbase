"""Base ModelAdmin classes for marketplace models."""

from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html


class BaseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']
    ordering = ['name']


class BaseProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'category',
        'price',
        'stock_quantity',
        'weight_grams',
        'is_active',
        'image_preview',
        'created_at',
    ]
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['price', 'stock_quantity', 'is_active']
    ordering = ['-created_at']

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" '
                'style="object-fit: cover; border-radius: 5px;" />',
                obj.image.url,
            )
        return 'No image'

    image_preview.short_description = 'Image'


class BaseOrderItemInline(admin.TabularInline):
    extra = 0
    readonly_fields = ['total_price']


class BaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'customer_name',
        'total_amount',
        'shipping_cost',
        'status',
        'payment_status',
        'delivery_provider',
        'tracking_number',
        'created_at',
    ]
    list_filter = ['status', 'payment_status', 'delivery_provider', 'created_at']
    search_fields = ['customer_name', 'telegram_username', 'payment_id', 'tracking_number']
    readonly_fields = ['created_at', 'updated_at', 'payment_url']

    fieldsets = (
        (
            'Customer Information',
            {
                'fields': (
                    'messenger_platform',
                    'telegram_user_id',
                    'telegram_username',
                    'telegram_first_name',
                    'telegram_last_name',
                    'customer_name',
                    'customer_phone',
                    'customer_email',
                    'shipping_address',
                    'shipping_city',
                    'shipping_postal_code',
                )
            },
        ),
        ('Order Details', {'fields': ('total_amount', 'shipping_cost', 'status')}),
        (
            'Payment Information',
            {'fields': ('payment_id', 'payment_status', 'payment_url')},
        ),
        (
            'Delivery',
            {
                'fields': (
                    'delivery_provider',
                    'delivery_rate_id',
                    'delivery_service_name',
                    'tracking_number',
                )
            },
        ),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


class BaseMessengerCartAdmin(admin.ModelAdmin):
    list_display = ['platform', 'user_id', 'items_count', 'updated_at']
    list_filter = ['platform', 'updated_at']
    search_fields = ['platform', 'user_id']
    readonly_fields = ['updated_at']

    def items_count(self, obj):
        return len(obj.items or {})

    items_count.short_description = 'Items in cart'
