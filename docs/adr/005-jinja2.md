# 005. Use Jinja2 for report and SQL templating

## Status

Accepted; both uses implemented (SQL templating in Volumes 1-2, HTML reports
in Volume 6 — see ADR-018 for the report-specific design decisions).

## Context

Two templating needs: (1) executive HTML reports generated from pipeline
outputs (Volume 6); (2) parameterized SQL — ingestion statements need runtime
paths, and ADR-010 generates feature SQL from configuration. Using one mature
engine for both avoids a second dependency and a second idiom.

## Decision

Jinja2 everywhere text is generated from data: report templates (HTML) and SQL
templates (`sql/*.sql.j2`, rendered by `demandpilot.sqlrender.SqlRenderer`
with `StrictUndefined` so missing parameters fail loudly).

## Consequences

- One well-known engine; SQL stays in `sql/` files (reviewable, syntax-highlighted)
  instead of Python string concatenation.
- Template logic can grow unwieldy — rule: templates format, Python computes;
  no business logic in templates.
- SQL templating is **not** an escaping mechanism: parameters must be trusted
  values (paths, identifiers) supplied by our own code, never user input.
  Data values go through DuckDB prepared-statement parameters.
