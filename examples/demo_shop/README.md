# Demo Shop — Reference Implementation using `market-base`

This is a minimal reference marketplace shop built on top of the `market-base` library.
It demonstrates:
1. Inheriting models from `market_base.django_app.models` (`AbstractCategory`, `AbstractProduct`, `AbstractOrder`, `AbstractOrderItem`, `AbstractMessengerCart`).
2. Reusing base admin interfaces (`BaseProductAdmin`, `BaseOrderAdmin`).
3. Using `BaseCart` for session + messenger persistence.
4. Hooking up delivery calculation (CDEK) and payment webhooks (YooKassa).

## Running the Demo

```bash
cd examples/demo_shop
python manage.py migrate
python manage.py runserver 8000
```
