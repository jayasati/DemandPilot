# 014. Direct multi-horizon dataset assembly: future-known vs. history-derived features

## Status

Accepted; implemented in Volume 3.

## Context

ADR-008 establishes the target-shift formulation: one leakage-safe
`feature_store_v{N}` snapshot row (computed "as of" a date, using only
strictly-prior history) can serve as the input for a target read `h` days
later. But a naive implementation — pairing the *origin* row's entire feature
set with the *target* row's label — silently throws away the single most
important retail demand signal: **what day of the week, price, and
promotional/SNAP conditions hold on the day being forecast**. An origin row
dated Tuesday tells the model nothing about the fact that the target day is a
Saturday.

Retail covariates split cleanly into two kinds:
- **Future-known**: calendar (day-of-week, month, holidays, events, SNAP) and
  price. These are known in advance for any future date — M5 supplies prices
  for the full evaluation horizon, and calendars/holidays are public schedules
  set well ahead of time. They are demand drivers *for the day being
  forecast*, not for the day the forecast is made.
- **History-derived**: lags and rolling statistics of past `units_sold`. These
  are only known as of the forecast origin — using the target day's own
  history-derived values would be leakage.

## Decision

`demandpilot.forecasting.dataset.HorizonDatasetAssembler` renders a self-join
of `feature_store_v{N}` against itself: the **origin** row supplies
history-derived columns (lags/rolling stats — from
`demandpilot.features.naming.history_derived_columns`, shared with the
Volume 2 generator so both agree on column names); the **target** row (origin
date + horizon) supplies calendar, price, and dimension columns, plus the
label itself. `origin`/`target` are joined on the series key
(`FeaturesConfig.group_columns`) and `target.date = origin.date + horizon`.

## Consequences

- The model can learn genuine calendar seasonality and price sensitivity for
  the day being forecast — the actual mechanism that makes multi-horizon
  demand forecasting work, not an artifact avoided by accident.
- The assembler is a self-join, doubling the read against the snapshot table
  per horizon — acceptable given DuckDB's columnar scan performance and that
  ADR-015's origin sampling already bounds row counts.
- Verified end-to-end: `tests/integration/test_forecasting.py` checks that a
  future-known column (day-of-week) reflects the target date and a
  history-derived column (lag_1) reflects the origin date, on real join output
  — not just by reading the SQL template.
