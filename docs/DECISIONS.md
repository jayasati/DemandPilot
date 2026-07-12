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
