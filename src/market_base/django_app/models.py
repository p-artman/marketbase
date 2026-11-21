"""Base abstract models for marketplace products, categories, orders and carts."""

from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class AbstractCategory(models.Model):
    """Abstract category model for organizing items."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class AbstractWarehouse(models.Model):
    """Abstract warehouse / shipping origin location."""

    name = models.CharField(max_length=150, verbose_name='Название склада/локации')
    city = models.CharField(max_length=100, default='Москва', verbose_name='Город склада')
    city_code = models.PositiveIntegerField(null=True, blank=True, verbose_name='Код города (СДЭК)')
    address = models.CharField(max_length=255, blank=True, verbose_name='Адрес склада')
    pvz_code = models.CharField(
        max_length=64,
        blank=True,
        verbose_name='Код ПВЗ (СДЭК) для отгрузки',
        help_text='Код ПВЗ отправления (например, NLCH9)',
    )
    postal_code = models.CharField(max_length=20, blank=True, verbose_name='Индекс')
    supported_providers = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Службы доставки склада',
        help_text='Список подключенных служб доставки: cdek, boxberry, fivepost',
    )
    is_default = models.BooleanField(default=False, verbose_name='Основной склад по умолчанию')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        verbose_name = 'Склад отгрузки'
        verbose_name_plural = 'Склады отгрузки'

    def __str__(self):
        return f'{self.name} ({self.city})'

    def get_supported_providers(self) -> list[str]:
        if self.supported_providers:
            return list(self.supported_providers)
        return ['cdek', 'boxberry', 'fivepost']


class AbstractProduct(models.Model):
    """Abstract product model with pricing, stock, weight, and image."""

    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    stock_quantity = models.PositiveIntegerField(default=1, verbose_name='Количество на складе')
    is_active = models.BooleanField(default=True)
    weight_grams = models.PositiveIntegerField(
        default=500,
        help_text='Parcel weight hint for delivery quotes',
    )
    disabled_delivery_providers = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Отключенные службы доставки',
        help_text='Службы доставки, принудительно отключенные для данного товара',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    PLACEHOLDER_IMAGE = '/static/marketplace/images/placeholder.jpg'

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.price} RUB'

    @property
    def image_url(self) -> str:
        """Return uploaded image URL or static placeholder."""
        if self.image and getattr(self.image, 'name', None):
            try:
                return self.image.url
            except ValueError:
                pass
        return self.PLACEHOLDER_IMAGE

    @property
    def is_in_stock(self) -> bool:
        return self.stock_quantity > 0

    def get_effective_delivery_providers(self) -> list[str]:
        """Return active delivery providers based on warehouse minus disabled."""
        warehouse = getattr(self, 'warehouse', None)
        if warehouse and hasattr(warehouse, 'get_supported_providers'):
            base = warehouse.get_supported_providers()
        else:
            base = ['cdek', 'boxberry', 'fivepost']
        disabled = set(self.disabled_delivery_providers or [])
        return [p for p in base if p not in disabled]


class AbstractMessengerCart(models.Model):
    """Abstract cart persistent storage across WebView resets keyed by messenger identity."""

    platform = models.CharField(max_length=32)
    user_id = models.BigIntegerField()
    items = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.platform}:{self.user_id} ({len(self.items or {})} skus)'


class AbstractOrder(models.Model):
    """Abstract order model for customer purchases, payment and delivery states."""

    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('confirmed', 'Подтверждён'),
        ('paid', 'Оплачен'),
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменён'),
    ]

    PAYMENT_STATUS_NAMES = {
        'pending': 'Ожидает оплаты',
        'succeeded': 'Оплачено',
        'canceled': 'Отменено',
        'cancelled': 'Отменено',
        'waiting_for_capture': 'Авторизовано',
    }

    @property
    def payment_status_display(self) -> str:
        return self.PAYMENT_STATUS_NAMES.get(self.payment_status, self.payment_status)

    telegram_user_id = models.BigIntegerField(null=True, blank=True)
    telegram_username = models.CharField(max_length=100, blank=True)
    telegram_first_name = models.CharField(max_length=100, blank=True)
    telegram_last_name = models.CharField(max_length=100, blank=True)
    messenger_platform = models.CharField(max_length=32, default='telegram')

    # Customer contact info
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField(blank=True)
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100, blank=True)
    shipping_postal_code = models.CharField(max_length=20, blank=True)

    # Financial and status
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00')
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Payment tracking
    payment_id = models.CharField(max_length=100, blank=True)
    payment_status = models.CharField(max_length=20, default='pending')
    payment_url = models.URLField(blank=True)

    # Delivery tracking
    delivery_provider = models.CharField(max_length=32, blank=True)
    delivery_rate_id = models.CharField(max_length=64, blank=True)
    delivery_service_name = models.CharField(max_length=200, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.id} - {self.customer_name}'


class AbstractOrderItem(models.Model):
    """Abstract individual items in an order."""

    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        abstract = True

    @property
    def total_price(self):
        return self.quantity * self.price
