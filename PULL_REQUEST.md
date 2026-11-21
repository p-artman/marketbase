# PR: feat(core): enhance CDEK suggest API, add warehouse abstract model and delivery origin routing

## Summary of Changes

1. **CDEK Autocomplete & Suggestions (`market_base.delivery.cdek`):**
   - Switched city autocomplete to CDEK API v2 `location/suggest/cities`, enabling instant typeahead matching by any partial name/prefix (e.g. "Наль", "Моск") instead of requiring exact city names.
   - Preserved fallback to `/v2/location/cities` and `FakeDeliveryProvider`.

2. **CDEK Pickup Points (ПВЗ) Directory:**
   - Integrated live directory lookup (`integration.cdek.ru/pvzlist/v1/json?cityid=...`), ensuring all real active points are returned (including missing points like `NLCH9` in Nalchik, пр. Кулиева, 2).
   - De-duplicated and merged with v2 `/deliverypoints`.

3. **Origin Routing & Warehouse Location (`AbstractWarehouse`):**
   - Added `AbstractWarehouse` model for shipping origin points (city, CDEK city_code, address, postal_code, is_default, is_active).
   - Updated `AbstractProduct.stock_quantity` default to 1.
   - Updated `CdekProvider.calculate_rates` to dynamically resolve origin location from `from_address.city` and `find_city_code(...)` instead of hardcoding a fixed default.

4. **Standards & Protocol:**
   - Added `AGENTS.md` specifying Modular Context and PR maintenance rules.

## Testing
- Unit tests: 11 passed, 2 skipped (integration).
- Live CDEK sandbox test verified:
  - "Наль" autocomplete returns matching cities with city codes.
  - Pickup points for Nalchik return all 12 points including `NLCH9`.
