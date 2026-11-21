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
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    weight_grams = models.PositiveIntegerField(
        default=500,
        help_text='Parcel weight hint for delivery quotes',
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
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

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
