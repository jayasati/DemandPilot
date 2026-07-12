# DemandPilot

Project guidance for Claude Code when working in this repository.

## Overview

DemandPilot is a decision-intelligence platform for retail: probabilistic
demand forecasting (P10/P50/P90, quantile LightGBM) on the M5/Walmart dataset,
newsvendor inventory optimization, historical policy simulation, generated
executive reports, and a Streamlit dashboard. DuckDB is the analytical store;
all configuration is validated Pydantic models loaded from `configs/`.

Work proceeds in volumes (see `docs/ROADMAP.md`). Volumes 0–4 are complete
(foundation, data layer, feature engineering, quantile forecasting, newsvendor
optimization); Volume 5 (historical policy simulation) is next.

## Structure

- `configs/` — all runtime configuration (validated by `src/demandpilot/config/`)
- `data/` — raw/processed data + DuckDB file (gitignored, reconstructible)
- `docs/` — architecture, strategies, ADRs (`docs/adr/`), roadmap
- `sql/` — ALL SQL: DDL, views, Jinja2 templates (`.sql.j2`); never inline SQL in Python
- `src/demandpilot/` — layered package: `core/` (pure math) → `config/` → `data/` →
  `features/` → `forecasting/` → `optimization/` → `cli.py`
- `tests/` — unit + integration; deterministic M5-format fixtures in `conftest.py`
- `scripts/` — operational scripts (M5 download)
- `docker/`, `.github/` — container + CI definitions

## Conventions

- Python 3.12+, Poetry, Black+Ruff+MyPy-strict (line length 100), pytest with
  85% coverage gate. Run everything via `poetry run poe check`.
- Google-style docstrings on all public functions (Ruff-enforced); structured
  exceptions from `demandpilot.exceptions`; logger-per-module.
- Polars for dataframes; pandas only at library boundaries (ADR-007).
- Leakage rule (ADR-008): no feature may reference the current row's target or
  the future. Check this on every feature/model change.
- Config first: tunables live in `configs/` and get a validator in
  `config/models.py`. Never hardcode paths.
- Follow the lifecycle in `docs/DEVELOPMENT_WORKFLOW.md`; significant design
  decisions get an ADR before implementation; update `docs/CHANGELOG.md` in
  the same change.

See `.claude/RULES.md` for enforced rules and `.claude/PROMPTS/` for reusable
prompt templates.
