# 016. Recommendations computed retrospectively, not into unobserved future dates

## Status

Accepted; implemented in Volume 4.

## Context

Volume 4's exit criterion is order-quantity recommendations "per store/SKU,
reproducible from one command." The direct-multi-horizon assembly (ADR-014)
pairs an origin row's history-derived features with a target row's
future-known features (calendar, price, dimensions) — but that target row
must **exist** in the feature snapshot, which only contains dates already
present in `sales`. Genuinely forecasting into an unobserved future date would
require extending the calendar and price data beyond the ingested history:
calendar fields (day-of-week, month, holidays) are pure date arithmetic and
easy to extend, but price requires either a real forward-looking price
schedule (M5's `sell_prices.csv` does cover the full competition evaluation
window, so this is available for the *real* dataset) or a carry-forward
assumption — a distinct, non-trivial capability in its own right, not a
natural extension of what Volumes 1–3 already built.

## Decision

`RecommendationBuilder` computes recommendations **retrospectively**: it finds
the most recent origin date for which a `lead_time_days`-ahead outcome already
exists in the feature snapshot (`origin = max(date) - lead_time_days`), and
recommends for that date — using the exact same self-join assembly and
quantile training as Volume 3. Because the target already exists, every
recommendation also carries the realized `actual_demand`, which is genuinely
useful decision support on its own (a real, verifiable "would this order
quantity have covered demand?" check) and gives Volume 5's simulation
something concrete to extend.

Live inference into dates beyond the ingested history is **out of scope** for
Volume 4 and documented in docs/KNOWN_LIMITATIONS.md rather than left
ambiguous — building it would mean adding a future-calendar generator and a
price-forecast/carry-forward assumption, which is real, separate engineering
work (a natural fit for a future serving layer, alongside the already-listed
FastAPI extension).

## Consequences

- Every recommendation is fully verifiable against real outcomes today, with
  zero new "predict beyond the data" machinery — Volume 4 stays a thin,
  well-tested layer over Volume 3's forecasting core.
- "Recommendations" here answer "what would we have ordered, and would it
  have been enough" for the most recent day we can grade — not "what should
  we order tomorrow." This is an explicit, load-bearing scope boundary, not
  an oversight; the CLI help text and docs/API.md make it discoverable.
- Live serving is a clearly scoped future extension, not a vague TODO.
