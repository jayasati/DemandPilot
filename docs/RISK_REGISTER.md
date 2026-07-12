# Risk Register

| # | Risk | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| R1 | **Target leakage** inflates backtest accuracy and destroys credibility | Medium | Critical | Structural rule (windows end ≥1 before target; direct multi-horizon shifts, ADR-008); leakage test in CI; review checklist item | Mitigated, re-audit each volume |
| R2 | **Scope creep** across 12 skill areas stalls delivery | High | High | Strict volume boundaries + exit criteria (ROADMAP); DoD; YAGNI in review | Active |
| R3 | **M5 scale** (~59M rows) exceeds laptop memory during ingest/training | Medium | Medium | DuckDB-native ingest (no in-memory unpivot); no ART indexes on facts; Polars lazy; `origin_stride_days` bounds the assembled training set (ADR-015) | Mitigated for V1/V2; untested against the full real M5 dataset (not yet downloaded) |
| R4 | **Windows dev vs. Linux CI/Docker drift** | Medium | Medium | pathlib-only paths; CI on ubuntu from day one; Docker e2e job planned (V8); logging-handler cleanup pattern in tests | Active |
| R5 | **Intermittent/zero-inflated demand** defeats plain quantile LightGBM (P10 collapses to 0) | Medium | Medium | Accepted for now (KNOWN_LIMITATIONS); evaluate in V3 backtests; candidate fixes: tweedie point + empirical residual quantiles, hierarchical pooling | Watch |
| R6 | **DuckDB single-writer** conflicts between dashboard and pipeline | Low | Low | Read-only connections for all consumers (enforced in `Database.connect`) | Mitigated |
| R7 | **Kaggle dependency**: credentials/rules block dataset access for new users | Low | Medium | Clear setup docs; deterministic fixtures keep the test suite independent of the dataset | Mitigated |
| R8 | **Assumed cost ratios** misrepresent real economics and skew recommendations | Medium | Medium | Ratios are validated, documented as assumptions (costs.yaml, ADR-012); sensitivity analysis planned in V4 reports | Watch |
| R9 | **Recursive-quantile fallacy** reintroduced by a future contributor | Low | High | ADR-008 records why; config only accepts `strategy: direct`; review checklist | Mitigated |
| R10 | **Dependency behavior drift** (a library changes a default between when an ADR was written and when it's actually run) | Medium | Medium | Empirically verify third-party API assumptions against the installed version before writing code that depends on them (caught: MLflow >=3 deprecating the file tracking store — ADR-006 corrected) | Active — recurring practice, not a one-time fix |

Review cadence: revisit at the end of every volume; move resolved risks to a
"closed" section with the volume that closed them.
