# Architecture

## Layering (Clean Architecture — dependencies point inward only)

```
┌────────────────────────────────────────────────────────────┐
│ Presentation      dashboard/ (Streamlit) · reporting/      │  V6–V7
├────────────────────────────────────────────────────────────┤
│ Application       cli.py · pipelines: features/,           │
│                   forecasting/, optimization/, simulation/ │  V2–V5
├────────────────────────────────────────────────────────────┤
│ Infrastructure    data/ (DuckDB, ingestion, validation)    │
│                   sqlrender.py · logging_setup.py · MLflow │  V1
├────────────────────────────────────────────────────────────┤
│ Domain (core/)    newsvendor math · forecast metrics       │
│                   PURE: no I/O, no configs, no frameworks  │
└────────────────────────────────────────────────────────────┘
        config/ (typed, validated) is injected everywhere
```

Rules:

- `core/` imports nothing from the other layers and does no I/O; it is the only
  place business math lives.
- Presentation contains zero business logic — it renders what the application
  layer computed.
- Infrastructure exceptions never cross a layer boundary raw; they are wrapped
  in the `DemandPilotError` hierarchy (docs/EXCEPTION_STRATEGY.md).
- All object wiring is constructor injection (`M5Ingestor(db, renderer, raw_dir)`);
  no module-level singletons, which keeps every layer testable in isolation.

## Key mechanisms

- **Configuration** — `load_config()` is the single entry point; every YAML in
  `configs/` is parsed into frozen Pydantic models that fail fast on invalid
  values (ADR-009). No other module opens config files.
- **SQL as code** — all SQL lives in `sql/`; parameterized statements are
  Jinja2 templates rendered with `StrictUndefined` (missing parameters fail
  loudly). Python never embeds ad-hoc SQL strings.
- **Single-writer DuckDB** — pipelines are the only writer; the dashboard and
  validators open read-only connections (ADR-001).
- **Leakage-safe features** — no feature window may include the current row's
  target; enforced structurally and by an automated test (ADR-008).
- **Cost-coupled quantiles** — the forecast quantile set includes the critical
  fractile implied by `configs/costs.yaml`, so optimization consumes a quantile
  the model was actually trained at (ADR-012).

## Significant decisions

Major choices are ADRs under [adr/](adr/README.md); smaller ones are logged in
[DECISIONS.md](DECISIONS.md).
