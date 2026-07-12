# Definition of Done

A change is **done** when every line below is true. The PR template mirrors
this list.

## Code

- [ ] All public functions/classes have type hints and Google-style docstrings
- [ ] MyPy strict, Ruff, and Black pass (`poe check`)
- [ ] Meaningful logging at pipeline milestones and every data-dropping decision
- [ ] Errors raised as `DemandPilotError` subclasses with actionable messages
- [ ] No hardcoded paths/values that belong in `configs/`
- [ ] No SQL strings in Python; no business logic outside its layer
- [ ] No dead code, placeholder implementations, or TODO functions

## Tests

- [ ] Unit tests for new logic; integration tests for new pipeline behavior
- [ ] Coverage does not drop below the 85% gate
- [ ] Tests are deterministic (no randomness, no network, no real dataset)

## Documentation

- [ ] CHANGELOG.md updated
- [ ] Affected docs updated (ARCHITECTURE, DATA_MODEL, API, SYSTEM_FLOW, ...)
- [ ] New significant decision → ADR; minor decision → DECISIONS.md row

## Integrity

- [ ] No fake data, fabricated metrics, or hand-typed results — every number
      traces to a reproducible run
- [ ] For anything touching features/models: leakage audit done (no feature
      sees the current row's target or the future)

## Process

- [ ] CI green on the PR
- [ ] CODE_REVIEW_CHECKLIST.md pass recorded in the PR
