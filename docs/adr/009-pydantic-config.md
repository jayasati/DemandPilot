# 009. Typed, fail-fast configuration with Pydantic

## Status

Accepted (stack addition approved by the project owner, 2026-07-11)

## Context

Everything tunable lives in `configs/*.yaml` (project rule: no hardcoded
configuration). Raw `yaml.safe_load` dicts push failures to use time: a typo'd
key, a negative horizon, or degenerate newsvendor costs (all-zero costs make
the critical fractile 0/0) would surface deep inside a pipeline run — or worse,
not at all. Hand-rolled dataclass validation is more code for less safety.

## Decision

Every config file maps to a frozen Pydantic v2 model (`config/models.py`) with
domain validators (quantiles strictly in (0,1), increasing, median required;
salvage < unit cost; positive horizons; `extra="forbid"` so unknown keys fail).
`load_config()` (`config/loader.py`) is the **single entry point**; no other
module reads config files. Validation failures raise `ConfigError` before any
pipeline work starts.

## Consequences

- Misconfiguration is impossible to run with; error messages name the exact
  field and constraint. Config objects are immutable and fully typed — MyPy
  checks every access.
- Pydantic joins the runtime stack (small, pure-Python core, huge ecosystem);
  models must be kept in sync with YAML files — `extra="forbid"` plus the
  test that loads the repo's real configs make drift a CI failure.
