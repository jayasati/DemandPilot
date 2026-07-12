# Git Strategy

## Branching — trunk-based

- `main` is always releasable: CI green, docs current.
- All work happens on short-lived branches: `volume-02-features`,
  `fix/ingest-null-prices`, `docs/adr-014`. Branch from `main`, merge back via
  PR within days, delete after merge.
- No long-lived develop/release branches — the project has one deliverable
  stream (the volumes) and doesn't need them (YAGNI).

## Commits

Conventional Commits (see CODING_STANDARDS.md). One logical change per commit;
a volume lands as a small series (schema → code → tests → docs), not one blob.

## Merging

- PRs into `main` require: CI green, the Definition of Done checklist, and a
  review pass against docs/CODE_REVIEW_CHECKLIST.md.
- Squash-merge when the branch history is noisy; merge-commit when the
  commit series itself documents the change well.

## What is never committed

Raw/derived data, the DuckDB file, `logs/`, `mlruns/`, generated reports,
`.env`, credentials (all enforced via `.gitignore`). Large-file guard runs in
pre-commit (`check-added-large-files`, 1 MB).

## Tags & releases

Semantic version tags (`v0.2.0`) at the end of each completed volume, matching
`pyproject.toml` and CHANGELOG.md.
