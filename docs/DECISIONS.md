# Decisions

Lightweight log of decisions not significant enough for a full ADR. For major
architecture/technology decisions, see [adr/](adr/README.md).

| Date | Decision | Rationale |
|---|---|---|
| 2026-07-12 | Project name is **DemandPilot** (final; "OptiRetail AI" dropped) | Owner decision; repo, package, and docs stay consistent |
| 2026-07-12 | `requires-python = ">=3.12,<3.15"`, local dev on 3.13 | 3.12 is the standard; 3.12 not installed locally, 3.13 is — CI covers both |
| 2026-07-12 | Line length 100 (Black + Ruff) | Better fit for typed signatures than 88; consistent across tools |
| 2026-07-12 | Task runner is poethepoet, not Make | Windows-first dev machine; tasks live in pyproject.toml |
| 2026-07-12 | Logs write to `logs/`, not `reports/logs/` | Logs are operational output, not report artifacts |
| 2026-07-12 | Streamlit binds 127.0.0.1 in dev; 0.0.0.0 only in container | Don't expose a dev dashboard on all interfaces by default |
| 2026-07-12 | Costs expressed as ratios of sell price | M5 has prices but no procurement costs; per-SKU absolute costs don't transfer |
| 2026-07-12 | CLI built on argparse (stdlib), not click/typer | Three subcommands don't justify a dependency (YAGNI) |
| 2026-07-12 | Test fixtures are deterministic M5-format CSVs | Exercise ingestion without violating the no-fake-data rule (see TESTING.md) |
| 2026-07-12 | MLflow tracking backend switched from `file:./mlruns` to `sqlite:///mlruns/mlflow.db` | Installed MLflow (3.14) raises on plain file-store `start_run()` — "maintenance mode"; verified empirically before writing code against it (ADR-006) |
| 2026-07-12 | Quantile crossing fixed by post-hoc rearrangement, not a joint training objective | Standard, simple, and effective (Chernozhukov et al.); revisit only if backtests show it's insufficient |
| 2026-07-12 | Metrics config (`forecast.yaml`'s `metrics` list) documents intent, not a gate | The 5 core metrics are cheap pure functions always computed; the list will drive what Volume 6 reporting surfaces |
| 2026-07-12 | `SimulationConfig.lead_time_days` tightened from `>= 0` to `>= 1` | `0` would self-join a row to itself in the horizon assembler (leakage) — caught while designing Volume 5; also affects Volume 4's `RecommendationBuilder`, which uses the same field |
| 2026-07-12 | Volume 5 replays independent single-period decisions rather than building a stateful multi-period inventory simulator | Matches ADR-003's original scope promise exactly; a full carryover simulator is real, separate future work, not a natural extension |
