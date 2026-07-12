# Known Limitations

Honest list of what DemandPilot currently does **not** do, and why.

## Data

- **No inventory positions**: M5 contains no on-hand inventory, so replenishment
  starts from simulated state (Volume 5), not observed positions.
- **Pre-launch rows are dropped** (ADR-013): a SKU's history starts at its first
  priced week. Zero-demand days *after* launch are kept — but true
  out-of-stock days are indistinguishable from zero-demand days in M5, which
  biases forecasts slightly low (censored demand).
- **Price is weekly**: daily price effects within a week are invisible.

## Modeling

- **Fixed quantile set**: P10/P50/P90 + the critical fractile — not a full
  predictive distribution. Quantile crossing between independently trained
  models is corrected post-hoc by rearrangement
  (`demandpilot.core.metrics.enforce_monotonic_quantiles`, ADR-002) rather
  than prevented during training — the correction is a well-established
  technique, but a jointly-monotonic training objective would be more
  principled if crossing turns out to be frequent in practice.
- **Horizon-as-feature, not per-horizon models** (ADR-015): one shared model
  per quantile may fit horizon-dependent effects less precisely than 28
  specialized models — an accepted training-cost trade-off, revisit if
  backtests show horizon-dependent error patterns the shared model misses.
- **Origin sampling** (`train.origin_stride_days`, ADR-015): training uses
  1-in-N calendar days as forecast origins, not every day — a documented,
  logged reduction to keep the assembled dataset tractable, not silent
  truncation, but it does mean rare origin-specific patterns get less
  training signal than a full-density dataset would provide.
- **Intermittent demand**: plain quantile LightGBM may collapse low quantiles
  to zero for slow movers (risk R5) — not yet evaluated against real M5 data.
- **Single-period newsvendor**: no multi-period carryover, lead-time demand
  aggregation, or capacity constraints in the first optimization cut.
- **Recommendations are retrospective, not live forecasts** (ADR-016):
  `demandpilot recommend` computes order quantities "as of" the most recent
  origin date for which a lead-time-ahead outcome already exists in the
  snapshot — it cannot yet forecast into genuinely unobserved future dates.
  That requires extending calendar (easy — pure date math) and price (harder
  — needs a real forward schedule or a carry-forward assumption) beyond the
  ingested history; a natural fit for a future serving layer alongside the
  already-listed FastAPI extension, not built here.

## Engineering

- **Single-node by design**: DuckDB + one machine. Fine for M5 (~59M rows);
  beyond ~10× that, the storage ADR must be revisited (MotherDuck/warehouse).
- **Single writer**: pipeline steps must not run concurrently against one DB file.
- **`sql/feature_store.sql` is still hand-written** (the dimensional join
  itself, not the rolling features it selects via `rf.* EXCLUDE (...)`) —
  acceptable since it has no config-duplication risk today; would need
  generation too if the dimensional join set ever became config-driven.
- Python 3.12 is the floor but local dev runs 3.13; both are in CI.

## Future extensions (beyond the roadmap)

Hierarchical forecast reconciliation · conformal prediction for calibrated
intervals · price-elasticity/promo uplift modeling · (s,S) and multi-echelon
policies · FastAPI serving layer · DuckDB → MotherDuck/warehouse migration path.
