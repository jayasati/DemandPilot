# Coding Standards

Enforced automatically wherever possible — the linters are the standard; this
page records the intent and the rules tools can't check.

## Python

- **Python 3.12+** (`requires-python = ">=3.12,<3.15"`). Local dev on 3.13 is
  fine; CI runs 3.12 and 3.13.
- **Black** (line length 100) formats; **Ruff** lints (pycodestyle, pyflakes,
  bugbear, pyupgrade, isort, simplify, pydocstyle-google); **MyPy strict** on
  `src/`. All three gate CI — code that fails them does not merge.
- Every public function/class/module has type hints and a Google-style
  docstring (Ruff `D` rules enforce presence).
- Structured exceptions only: raise `DemandPilotError` subclasses; wrap
  infrastructure errors with `raise ... from exc` (docs/EXCEPTION_STRATEGY.md).
- Logging: module-level `logger = logging.getLogger(__name__)`; lazy `%s`
  formatting; no `print()` outside the CLI error path and `scripts/`.
- Configuration comes only from `load_config()`; **no hardcoded paths or
  constants that belong in `configs/`**.
- Dataframes: **Polars** is the default; pandas only at library boundaries
  (LightGBM/MLflow/Streamlit interop) — convert at the edge, don't mix.
- Composition over inheritance; constructor injection over globals/singletons.
- No notebook-style code in `src/`; notebooks live in `notebooks/` and never
  contain business logic.

## SQL

- All SQL lives in `sql/` — static DDL/views as `.sql`, parameterized
  statements as `.sql.j2` rendered via `SqlRenderer` (StrictUndefined).
- Keywords UPPERCASE, identifiers snake_case, one clause per line for
  multi-join queries; comment *why*, not *what*.
- Feature SQL must never reference the current row's target (ADR-008).

## Commits

- [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`.
- Scope by area when useful: `feat(data): ...`, `docs(adr): ...`.
- Subject in imperative mood, ≤72 chars; body explains motivation and
  trade-offs. See docs/GIT_STRATEGY.md.
