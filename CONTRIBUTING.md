# Contributing to DemandPilot

Thanks for contributing! The short version: read
[docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md), and don't merge
anything that fails [docs/DEFINITION_OF_DONE.md](docs/DEFINITION_OF_DONE.md).

## Setup

Follow [docs/ENVIRONMENT_SETUP.md](docs/ENVIRONMENT_SETUP.md), then
`poetry run pre-commit install`.

## Making a change

1. Branch from `main` (`volume-NN-topic` or `fix/...` — see
   [docs/GIT_STRATEGY.md](docs/GIT_STRATEGY.md)).
2. Significant design choice? Write the ADR **before** the code
   ([docs/adr/README.md](docs/adr/README.md)).
3. Code + tests + docs in the same PR. `poetry run poe check` must be green.
4. Use Conventional Commits (`feat:`, `fix:`, `docs:`, ...).
5. Open a PR; the template walks you through the Definition of Done.

## Hard rules (enforced in review)

- No fake data, fabricated metrics, placeholder functions, or dead code.
- No hardcoded paths/config — everything flows through `configs/`.
- No SQL strings in Python — SQL lives in `sql/`.
- No feature may see the current row's target or the future (leakage).
- Every public function: type hints, docstring, tests.

## Reporting issues

Include: what you ran, expected vs. actual, OS/Python version, and the
relevant `logs/demandpilot.log` lines (JSON, greppable).
