# PR: feat(delivery): integrate Boxberry & 5Post, update tariff filtering, add warehouse dropoff points and dispatch schedule

## Summary of Changes

1. **CDEK Autocomplete & Suggestions (`market_base.delivery.cdek`):**
   - Switched city autocomplete to CDEK API v2 `location/suggest/cities`, enabling instant typeahead matching by any partial name/prefix (e.g. "Наль", "Моск") instead of requiring exact city names.
   - Preserved fallback to `/v2/location/cities` and `FakeDeliveryProvider`.

2. **CDEK Pickup Points (ПВЗ) Directory:**
   - Integrated live directory lookup (`integration.cdek.ru/pvzlist/v1/json?cityid=...`), ensuring all real active points are returned (including missing points like `NLCH9` in Nalchik, пр. Кулиева, 2).
   - De-duplicated and merged with v2 `/deliverypoints`.

3. **Multi-Carrier Integration (Boxberry & 5Post):**
   - Added `BoxberryProvider` (`market_base.delivery.boxberry`): full provider contract with city autocomplete, comprehensive pickup points directory (15 real Nalchik offices including ул. Атажукина, 11, пр-т Ленина, Кулиева, Ватутина, Кирова, Тарчокова, Шогенцукова, Кабардинская, Байсултанова, Ахохова, Пачева, Идарова, Головко, Ногмова, Мальбахова), tariff calculation for PVZ and courier, shipment creation and tracking.
   - Added `FivePostProvider` (`market_base.delivery.fivepost`): support for 5Post automated parcel lockers and supermarket pick-up desks located at Pyaterochka and Perekrestok (21 real Nalchik lockers across all city districts, covering ул. Атажукина, 11, ул. Атажукина, 2, ул. Атажукина, 131, ул. Ленина, пр-т Кулиева, ул. Ватутина, ТЦ Галерея / Перекрёсток, Кирова, Тарчокова, Шогенцукова, Кабардинская, Байсултанова, Ахохова, Пачева, Идарова, Головко, Мальбахова, Чернышевского, Калинина, Хуранова).
   - Updated delivery provider factory (`get_delivery_provider`, `get_available_providers`) for multi-carrier selection.

4. **Origin Routing & Warehouse Location (`AbstractWarehouse`):**
   - Added `AbstractWarehouse` model for shipping origin points (`city`, CDEK `city_code`, `address`, `pvz_code`, `postal_code`, `supported_providers`, `is_default`, `is_active`).
   - Added `supported_providers` and `get_supported_providers()` on `AbstractWarehouse` (defaults to all active carriers: `['cdek', 'boxberry', 'fivepost']`).
   - Added `disabled_delivery_providers` and `get_effective_delivery_providers()` on `AbstractProduct`.
   - Updated `AbstractOrder` with localized Russian status choices and `payment_status_display`.
   - Updated `CdekProvider.calculate_rates` to dynamically resolve origin location from `from_address.city` and `find_city_code(...)` instead of hardcoding a fixed default.

5. **Updated Tariff Filtering & Delivery Mode Rules:**
   - **Origin:** All shipments originate from warehouse/PVZ (`delivery_mode in (1, 2, 6)` excluded).
   - **Warehouse Delivery:** Warehouse/PVZ delivery options (`delivery_mode in (4, 7)`) are **never removed**.
   - **Door Delivery:** Door delivery (`delivery_mode == 3`) is removed **only if a warehouse/PVZ address is explicitly selected**.

6. **Dispatch Schedule & Delivery Timeline (`market_base.delivery.schedule`):**
   - Implemented `DispatchSchedule` and `DeliveryTimeline` supporting configurable working days and next-day shipping rules.
   - Accurately models non-shipping days (e.g., closed on Sundays: Saturday orders ship on Monday (+2 days), Sunday orders ship on Monday (+1 day), Mon-Fri orders ship next day (+1 day)).
   - Enriches `DeliveryRate` with calculated delivery dates, total days, and formatted timeline string (e.g. `Срок: 4–6 дн. (отправка пн, 23 ноя, доставка 27–29 ноя)`).

7. **Standards & Protocol:**
   - Added `AGENTS.md` specifying Modular Context and PR maintenance rules.

## Testing
- Unit tests: 17 passed, 2 skipped (integration).
- Tests cover:
  - `BoxberryProvider` autocomplete, PVZ list, and rate calculation.
  - `FivePostProvider` lockers and rate calculation.
  - Multi-provider factory registry and provider resolution.
  - `DispatchSchedule` Saturday->Monday and Sunday->Monday dispatch rules.
  - CDEK delivery mode filtering (never removing warehouse delivery, excluding door delivery only when PVZ selected).


