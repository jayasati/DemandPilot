# 017. Historical policy-replay simulation: ML quantile vs. classical baseline

## Status

Accepted; implemented in Volume 5.

## Context

Volume 4 answers "what should we order" for one point in time. Volume 5's
job (per docs/PROJECT.md) is "what would policy X have cost us" — a
multi-period comparison. ADR-003 explicitly deferred this: "the simulation
engine (Volume 5) quantifies how much the single-period simplification
costs." Two design questions had to be resolved:

1. **What counts as a full multi-period inventory simulation vs. a repeated
   single-period decision?** A true multi-period simulator would carry
   inventory state (on-hand, in-transit, backorders) across time — explicitly
   out of scope per ADR-003's "no inventory carryover" limitation. Building
   that now would silently expand Volume 5 into the deferred multi-period
   problem instead of the single-period question it was scoped to answer.
2. **What does the "baseline" being compared against actually look like?**
   `configs/simulation.yaml` already declares `service_level`,
   `demand_distribution`, `n_simulations`, and `random_seed` — fields no
   volume had used yet.

## Decision

**Replay, don't carry state.** At each of many historical decision points
(origin dates), independently: both policies compute an order quantity using
only pre-origin data, and both are graded against the same realized demand
with the newsvendor cost function
(`core.newsvendor.realized_cost_breakdown`). This directly answers "what
would we have ordered, and what would it have cost" at scale, without
building (or silently mis-scoping into) a stateful multi-period simulator.

**Two policies, one decision framework.** Both are "newsvendor" decisions
(`simulation.yaml`'s `policy: newsvendor`) that differ only in how the demand
distribution is estimated:
- **ML policy**: reuses Volume 3/4's `HorizonDatasetAssembler` and
  `QuantileForecaster` directly — `Q*` is the critical-fractile prediction.
- **Classical baseline**: `demandpilot.simulation.classical_order_up_to`
  fits `demand_distribution` (`empirical` | `normal` | `poisson`) to each
  series' pre-test daily demand and returns the `service_level` quantile.
  `empirical` uses Monte Carlo bootstrap (`n_simulations` draws of
  `lead_time_days` days, summed, then quantiled) — the statistically correct
  way to estimate lead-time demand from single-day observations without
  assuming a parametric form; `normal`/`poisson` use the closed-form
  aggregation of `lead_time_days` i.i.d. draws.

**Reuses the exact chronological split** (`forecasting.split.
chronological_split`) rather than a new train/test mechanism: the ML model
trains on train+validation, the classical baseline's per-series demand
sample is drawn from the same train+validation rows, and both are evaluated
on the identical held-out test origins (filtered to a `review_period_days`
cadence) — a fair, paired, leakage-free comparison.

**Costs in real currency**: `realized_cost_breakdown` multiplies the
ratio-based costs (ADR-012) by each row's actual `sell_price` at the target
date, so the comparison reports real dollars, not dimensionless ratios.

## Consequences

- Directly answers Volume 5's exit criterion — a policy comparison with a
  cost breakdown — using entirely reused, already-tested machinery
  (assembler, split, forecaster) plus ~150 lines of genuinely new logic
  (the baseline estimator and the replay loop).
- Gives every field in `simulation.yaml` a real implementation for the first
  time (`service_level`, `demand_distribution`, `n_simulations`,
  `random_seed`, `review_period_days`, `lead_time_days`).
- Still single-period per decision, as scoped — a true multi-period
  inventory simulator with carryover remains a documented future extension
  (docs/KNOWN_LIMITATIONS.md), not something this ADR silently expanded into.
- Caught and fixed a latent validation gap while designing this: `configs/
  simulation.yaml`'s `lead_time_days` allowed `0`, which — used as a
  self-join horizon — would join a row to itself (leakage). Tightened to
  `>= 1`; this also fixes an unexercised edge case in Volume 4's
  `RecommendationBuilder`, which uses the same field the same way.
