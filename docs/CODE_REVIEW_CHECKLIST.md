# Code Review Checklist

Work through top-down; stop and request changes at the first structural issue.

## Architecture

- [ ] Change lives in the right layer (math→`core`, I/O→`data`, wiring→app layer)?
- [ ] Dependencies still point inward (no `core` importing `data`/`config`)?
- [ ] New decision that deserves an ADR / DECISIONS.md row — is it recorded?
- [ ] Simplest design that works (KISS/YAGNI) — no speculative abstraction?

## Correctness

- [ ] Time-series discipline: nothing reads the current row's target or the
      future; splits/backtests respect chronology?
- [ ] Data dropped anywhere? Is it intentional, logged, and documented?
- [ ] Idempotency: re-running the pipeline yields the same state?
- [ ] Edge cases: empty tables, single-row series, NULLs, zero demand?

## Configuration & data

- [ ] Every tunable in `configs/` and validated in `config/models.py`?
- [ ] Degenerate config values rejected at load time, not at use time?
- [ ] SQL in `sql/`, templates use StrictUndefined, parameters trusted?

## Quality

- [ ] Types precise (no gratuitous `Any`); docstrings say args/returns/raises?
- [ ] Exceptions wrapped per EXCEPTION_STRATEGY.md, caught once at boundary?
- [ ] Logging: milestones + counts, lazy `%s`, no secrets, no `print`?
- [ ] Tests actually assert behavior (not just "doesn't crash"); failure
      messages will point at the cause?

## Docs & hygiene

- [ ] CHANGELOG + affected docs updated in the same PR?
- [ ] No commented-out code, stray files, or committed artifacts?
- [ ] Commit messages explain *why*?
