# Testing Strategy

## Layers

| Layer | Location | Scope | Marker |
|---|---|---|---|
| Unit | `tests/unit/` | Pure logic: config validation, newsvendor math, SQL rendering, logging bootstrap | — |
| Integration | `tests/integration/` | Real DuckDB file end-to-end: schema → ingest → validate; full CLI runs | `integration` |
| Data validation | `demandpilot.data.validation` | Runs in *production* after every ingest, not only in tests | — |

Planned additions: **leakage tests** as a first-class suite in Volume 2 (no
generated feature may correlate with the current row's target by construction),
and **backtest invariant tests** in Volume 3 (e.g. P10 ≤ P50 ≤ P90, empirical
coverage within tolerance).

## Fixture policy

Tests use a tiny, fully **deterministic** dataset generated in the exact M5 CSV
format (2 stores × 3 items × 56 days, closed-form `units_for()` values — no
randomness, no fabricated "realistic" data). Fixtures exist solely to exercise
code paths; anything resembling real analysis runs on the actual M5 dataset.
This is the boundary of the "never generate fake data" rule: synthetic *test
fixtures* yes, synthetic *business data or metrics* never.

## Running

```bash
poetry run poe test        # plain pytest
poetry run poe cov         # with coverage (fails under 85%)
poetry run pytest -m "not integration"   # fast unit-only loop
poetry run poe check       # everything CI runs
```

## Coverage expectations

- Global gate: **85%** branch coverage (`fail_under` in pyproject; CI-enforced).
- `core/` aims at 100% — it is pure math with no excuse for gaps.
- New code must not lower coverage; add tests in the same PR.

## Conventions

- Test names state behavior: `test_pre_launch_rows_dropped`, not `test_ingest_2`.
- Integration tests write only under `tmp_path`; never touch the repo's `data/`.
- Windows caveat: any test that configures file logging uses the
  `reset_logging` fixture so open handlers don't block tmp-dir cleanup.
