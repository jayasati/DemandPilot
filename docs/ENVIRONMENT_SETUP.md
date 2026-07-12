# Environment Setup

## Prerequisites

- Python **3.12 or 3.13** (`py -0p` on Windows lists installed versions)
- [Poetry](https://python-poetry.org/docs/#installation) (`pipx install poetry`
  or `py -3.13 -m pip install --user poetry`)
- git

## Setup

```bash
git clone <repo-url> && cd DemandPilot
poetry config virtualenvs.in-project true   # .venv inside the repo (recommended)
poetry install --with dev
poetry run pre-commit install               # enable the git hooks
poetry run poe check                        # verify: format, lint, types, tests
```

On Windows, if `python` resolves to another version, pin the venv first:
`poetry env use C:\Python313\python.exe`.

## Getting the M5 dataset

1. Create a Kaggle account and API token (`kaggle.json` → `~/.kaggle/` /
   `%USERPROFILE%\.kaggle\`, or set `KAGGLE_USERNAME`/`KAGGLE_KEY` — see
   `.env.example`).
2. Accept the competition rules at
   <https://www.kaggle.com/competitions/m5-forecasting-accuracy>.
3. `pip install kaggle` (not a project dependency — download is a one-time,
   out-of-band step), then:

```bash
poetry run python scripts/download_m5.py    # → data/raw/m5/ (~450 MB unzipped)
```

## Building the database

```bash
poetry run demandpilot init-db
poetry run demandpilot ingest-m5            # full M5: expect a few minutes
poetry run demandpilot validate
```

Everything lands where `configs/app.yaml` says (DB at `data/demandpilot.duckdb`,
logs at `logs/demandpilot.log`). Use `--root` or `DEMANDPILOT_ROOT` to run
against a different project root.

## Day-to-day tasks

| Task | Command |
|---|---|
| Format / lint / typecheck / test | `poe fmt` / `poe lint` / `poe typecheck` / `poe test` |
| Everything CI runs | `poe check` |
| Coverage report | `poe cov` |

(Prefix with `poetry run`, or `poetry shell` once per session.)
