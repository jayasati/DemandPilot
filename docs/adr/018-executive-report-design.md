# 018. Executive HTML report: gathering, templating, and graceful-empty design

## Status

Accepted; implemented in Volume 6.

## Context

ADR-005 already committed to Jinja2 for report templates; this ADR covers
the decisions ADR-005 deferred to "Volume 6": where templates physically
live, how the report reads data that may not exist yet, and how it reaches
MLflow (which Volume 3 writes to, but nothing before this volume read from).

Three concrete questions needed answers:

1. **Where do the HTML templates live?** `.gitignore` already states "report
   templates are code and live in `src/`" (written in Volume 0, before any
   reporting code existed) — this ADR honors that by shipping templates as
   package data under `demandpilot/reporting/templates/`, resolved via
   `Path(__file__).parent`, not a runtime-configurable path.
2. **What if `recommend`/`simulate`/`train` have never been run?** A report
   is a read-only view over whatever state exists; it must not require every
   upstream command to have run first, or fail obscurely if they haven't.
3. **How does the report reach MLflow read-only, without training anything?**
   `ForecastingPipeline` uses `mlflow.start_run()` (a write operation via
   global state); the report needs read-only lookup instead.

## Decision

1. **Templates and SQL as code, output as data.** The Jinja2 HTML template
   lives in `demandpilot/reporting/templates/`; the report's summary
   queries are plain static `.sql` files in `sql/` (no runtime parameters,
   so no need for `SqlRenderer`/`StrictUndefined` — table names are fixed).
   Rendered `.html` output goes to `reports/` (gitignored, generated).
2. **Presence-checked, not assumed.** `_table_exists()` queries
   `information_schema.tables` before reading `recommendations` /
   `simulation_results` (both are created dynamically, unlike
   `feature_snapshots` which is part of the static schema and always exists,
   possibly empty). Each report section renders either its data or an
   explicit "run `demandpilot X`" prompt — never a crash, never silently
   blank.
3. **`MlflowClient(tracking_uri=...)` for read-only lookup**
   (`demandpilot.mlflow_utils.latest_run`), verified against the installed
   MLflow version rather than assumed: accepts a tracking URI directly, no
   `mlflow.set_tracking_uri()` global mutation needed. `resolve_mlflow_tracking_uri`
   (previously private to `cli.py`) moved to the shared `mlflow_utils` module
   so both the CLI's `train` command and the reporting layer resolve a
   relative tracking URI against `--root` the same way.
4. **Detail is capped and labeled, not dumped.** The "largest forecast
   misses" table shows the top 20 by absolute error, with the total count
   stated alongside — real M5 scale (30k+ series) makes a full dump useless
   for an executive audience; the cap is visible, never silent.
5. **Stat tiles follow the project's data-viz skill**: label / value / signed
   delta with direction-based color (the ML-savings tile), using the fixed
   status palette (`good`/`critical`) — never a categorical hue repurposed
   for status. No charts are used (this is a static summary, not an
   interactive dashboard — Plotly/Streamlit remain Volume 7's job per ADR-004).

## Consequences

- Zero new business logic in the presentation layer (ARCHITECTURE.md's
  rule): `data.py` only queries and lightly aggregates what Volumes 1-5
  already computed and persisted.
- A report can be generated at any point in the pipeline's lifecycle,
  immediately after `build-features`, and remains genuinely useful (lineage
  + cost assumptions) even with nothing else run yet — verified directly
  by rendering a real report end-to-end and reading the output (not just
  asserting on substrings) before calling this done.
- MLflow experiment name comes from `forecast_config.mlflow.experiment_name`
  (already part of `ForecastConfig`) — no new config needed.
- Adding a new report section later means adding one static `.sql` file, one
  dataclass, and one template block — the pattern is uniform across all
  three optional sections.
