# 007. Use Polars for dataframe processing

## Status

Accepted

## Context

Python-side data work (feature assembly edges, simulation state, evaluation)
touches millions of rows. Pandas is the default choice but is slow and
memory-hungry at M5 scale and its type system is loose. Polars offers lazy
execution, multi-threading, strict dtypes, and zero-copy Arrow interop with
DuckDB. Risk: two dataframe idioms in one codebase if the boundary is fuzzy —
several stack libraries (LightGBM, MLflow, Streamlit) still expect pandas.

## Decision

Polars is the only dataframe library for internal logic. Pandas may appear
**only** at third-party boundaries (e.g. `.to_pandas()` immediately before a
LightGBM/MLflow/Streamlit call), never for transformation logic. Heavy
relational work (joins, windows over the full fact table) stays in DuckDB SQL;
Polars handles what SQL expresses poorly.

## Consequences

- Fast, memory-lean, strictly typed transformations; lazy plans compose well
  with DuckDB Arrow streaming.
- Contributors must know the boundary rule — enforced in review
  (docs/CODE_REVIEW_CHECKLIST.md); pandas remains a declared dependency, which
  is intentional, not an oversight.
