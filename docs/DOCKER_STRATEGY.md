# Docker Strategy

## Image (`docker/Dockerfile`)

Multi-stage build:

1. **builder** — installs Poetry, exports `poetry.lock` to `requirements.txt`
   (the lockfile is the single source of dependency truth; the image never
   re-resolves versions).
2. **runtime** — `python:3.12-slim` + `libgomp1` (LightGBM's OpenMP runtime),
   installs the exported requirements, then the `demandpilot` package itself
   with `--no-deps`.

Design rules:

- **Data never ships in the image.** `data/`, `logs/`, and `reports/` are
  volumes; `.dockerignore` keeps them out of the build context.
- Configs and SQL are copied in, so the container is self-sufficient with
  `DEMANDPILOT_ROOT=/app`; mount `./configs` over `/app/configs` to override
  settings without rebuilding.
- Entrypoint is the CLI. Inside the container Streamlit (Volume 7) binds
  0.0.0.0; on a dev machine it binds 127.0.0.1 (configs default).

## Compose (`docker/docker-compose.yml`)

Two services: `demandpilot` (the app/CLI) and `mlflow` (tracking server on
:5000, store mounted from `./mlruns`). Typical usage:

```bash
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml run demandpilot init-db
docker compose -f docker/docker-compose.yml run demandpilot ingest-m5
```

## Future (Volume 8)

- CI job that builds the image and runs the integration suite inside it
  (guards against Windows-dev/Linux-runtime drift).
- Pin the base image by digest for reproducible rebuilds.
