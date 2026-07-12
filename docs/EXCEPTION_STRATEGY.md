# Exception Strategy

## Hierarchy (`demandpilot.exceptions`)

```
DemandPilotError
├── ConfigError            missing/unparsable/invalid configuration
├── DatabaseError          DuckDB operation failed
├── SqlRenderError         SQL template missing or failed to render
└── DataError
    ├── IngestionError     raw data missing/malformed
    └── DataValidationError ingested data failed integrity checks
```

New layers add exactly one subclass per failure domain (Volume 3 adds
`ForecastError`, Volume 4 `OptimizationError`, ...).

## Rules

1. **Wrap at the boundary**: infrastructure exceptions (`duckdb.Error`,
   `yaml.YAMLError`, `jinja2.TemplateError`, `OSError`) never leak past the
   layer that produced them — re-raise as a `DemandPilotError` subclass with
   `raise ... from exc` so the cause chain survives.
2. **Messages are actionable**: say what failed, with which path/value, and
   when possible what to do (`"Missing M5 raw files in ...: calendar.csv.
   Download them with scripts/download_m5.py"`).
3. **One catch site**: the CLI `main()` catches `DemandPilotError`, logs it,
   prints to stderr, returns exit code 1. Intermediate layers don't catch what
   they can't handle.
4. **Pure domain code raises `ValueError`**: `core/` knows nothing about the
   application; callers translate if needed.
5. **Fail fast on config**: invalid configuration stops the process at load
   time — no pipeline runs with degenerate parameters (e.g. newsvendor
   economics with an undefined critical fractile are rejected by validation).
6. Never catch bare `Exception` outside a top-level boundary; never silence an
   exception without logging it.
