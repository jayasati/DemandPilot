# Development Workflow

Every volume (and any non-trivial change) follows this lifecycle — no stage
may be skipped:

```
Planning → Architecture → Implementation → Testing → Review → Audit → Documentation → Merge
```

| Stage | What it means here | Artifact |
|---|---|---|
| Planning | Scope, exit criterion, affected configs/docs identified | ROADMAP.md entry |
| Architecture | Design decisions made *before* code; trade-offs written down | ADR or DECISIONS.md row |
| Implementation | Code on a short-lived branch, following CODING_STANDARDS.md | Commits |
| Testing | Unit + integration tests in the same branch; `poe check` green | tests/ |
| Review | Self- or peer-review against CODE_REVIEW_CHECKLIST.md | PR review |
| Audit | Adversarial pass: leakage? hardcoding? silent data loss? fake metrics? | PR notes |
| Documentation | ARCHITECTURE / DATA_MODEL / API / CHANGELOG updated in the same PR | docs/ |
| Merge | DoD checklist complete, CI green | PR merged to main |

## Daily loop

```bash
git switch -c volume-02-features
# ... edit ...
poetry run poe fmt && poetry run poe check   # before every commit (pre-commit enforces)
git commit -m "feat(features): render lag SQL from config"
git push && open PR
```

## Ground rules

- Config first: if a value could ever change, it starts life in `configs/`.
- SQL lives in `sql/`; business math lives in `core/`; the two never swap.
- A feature without a test and docs is not done (docs/DEFINITION_OF_DONE.md).
- When implementation reveals the architecture was wrong, stop and update the
  ADR first — don't code around it.
