# MarketBase (`marketbase`)

> **Core framework, provider abstractions, and backend engine for omnichannel marketplace platforms**

`marketbase` is an extensible foundation library for building custom online stores and marketplace bots. It provides ready-to-use provider adapters (YooKassa with 54-FZ, CDEK API v2, Telegram Mini Apps, MAX Messenger), reusable Django abstractions (`BaseCart`, abstract models, base admins), and notification services.

Using this foundation, you can rapidly build different client stores with unique storefront designs, customized views, and custom product catalogs while sharing a tested core backend.

---

## 📦 Architecture & Modules

- **`market_base.core`**: Universal DTOs (`Money`, `Address`, `Parcel`) and base configuration contracts.
- **`market_base.payments`**:
  - `PaymentProvider` protocol
  - `YooKassaProvider`: Official YooKassa SDK integration, 54-FZ fiscalization for self-employed, receipt items calculation
  - `FakePaymentProvider`: In-memory provider for unit tests
  - Provider factory (`get_payment_provider()`, `set_payment_provider()`)
- **`market_base.delivery`**:
  - `DeliveryProvider` protocol
  - `CdekProvider`: CDEK API v2 with OAuth, city autocomplete, pickup points (ПВЗ), and real-time tariff calculations
  - `FakeDeliveryProvider`: Mock carrier for local development and tests
  - Provider factory (`get_delivery_provider()`, `set_delivery_provider()`)
- **`market_base.messengers`**:
  - `MessengerPlatform` protocol
  - `TelegramPlatform`: WebApp HMAC-SHA256 initData validation, message delivery
  - `MaxPlatform`: MAX Messenger Bot API, Ministry of Digital Development trusted root TLS certificates, WebApp authentication, `open_app` inline keyboards
- **`market_base.notifications`**:
  - `EmailNotifier` protocol & `OrderEmailPayload`
  - `DjangoEmailNotifier` (SMTP) & `ConsoleEmailNotifier`
- **`market_base.django_app`**:
  - Abstract models: `AbstractCategory`, `AbstractProduct`, `AbstractOrder`, `AbstractOrderItem`, `AbstractMessengerCart`
  - `BaseCart`: Session-backed shopping cart with persistent messenger user synchronization across WebView cookie resets
  - Base ModelAdmin classes (`BaseProductAdmin`, `BaseOrderAdmin`, etc.)
  - Reusable API endpoints: `/api/delivery/quote/`, `/api/delivery/autocomplete/`, `/api/delivery/pickup-points/`, `/api/messenger/bind/`
- **`market_base.backend`**:
  - Bot runner abstractions and webhook servers

---

## 🚀 Installation

### From GitHub Repository
```bash
pip install git+https://github.com/p-artman/marketbase.git
```
Or via `pyproject.toml` (e.g. in your store project):
```toml
dependencies = [
    "marketbase @ git+https://github.com/p-artman/marketbase.git",
]
```

### Local Development / Editable
```toml
[tool.uv.sources]
marketbase = { path = "../marketbase", editable = true }
```

---

## 🛠️ Quick Example: Creating a Shop

1. Define your models in `shop/models.py`:
```python
from django.db import models
from market_base.django_app.models import AbstractProduct, AbstractCategory, AbstractOrder

class Category(AbstractCategory):
    pass

class Product(AbstractProduct):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')

class Order(AbstractOrder):
    pass
```

2. Implement a cart in `shop/cart.py`:
```python
from market_base.django_app.cart import BaseCart
from shop.models import Product

class ShopCart(BaseCart):
    product_model = Product
```

3. Include delivery & messenger API in `urls.py`:
```python
from django.urls import path, include

urlpatterns = [
    path('api/', include('market_base.django_app.urls')),
]
```

See a complete runnable example in [`examples/demo_shop/`](examples/demo_shop/).

---

## 🧪 Running Tests

```bash
pytest
# Run external sandbox tests:
pytest -m integration
```

---

## 📜 License

MIT License
