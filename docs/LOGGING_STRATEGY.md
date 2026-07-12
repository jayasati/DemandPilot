# Logging Strategy

## Configuration

Declared in `configs/logging.yaml` (dictConfig schema), never in code.
`demandpilot.logging_setup.setup_logging()` loads it, resolves relative log
paths against the project root, and creates directories before handlers open —
it is called once, at the CLI entry point.

Two handlers:

- **console** — human-readable, INFO+, stdout.
- **file** — JSON lines, DEBUG+, `logs/demandpilot.log`, rotating 10 MB × 5
  backups. Machine-parsable for later analysis.

## Rules

- One logger per module: `logger = logging.getLogger(__name__)` — names mirror
  the package tree, so verbosity is tunable per subsystem in YAML.
- Lazy interpolation (`logger.info("rows=%d", n)`), never f-strings in log
  calls — arguments shouldn't be formatted when the level is off.
- Every pipeline stage logs: start (inputs), end (row counts / durations /
  summary), and every dropped-data decision (e.g. pre-launch row filtering
  logs how many rows were dropped — silent data loss is forbidden).
- Exceptions are logged **once**, at the boundary that handles them (the CLI),
  not at every layer they pass through.
- No `print()` outside the CLI's stderr error path and `scripts/`.
- Never log secrets or credentials.

## Levels

| Level | Use |
|---|---|
| DEBUG | Per-check/per-step detail (validation check results, rendered SQL paths) |
| INFO | Pipeline milestones, row counts, summaries |
| WARNING | Recoverable oddities (empty partitions, deprecated config keys) |
| ERROR | Operation failed; raised as a `DemandPilotError` |
