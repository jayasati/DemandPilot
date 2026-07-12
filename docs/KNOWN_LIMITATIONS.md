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

## Modeling (current design, revisited in Volume 3)

- **Fixed quantile set**: P10/P50/P90 + the critical fractile — not a full
  predictive distribution; quantile crossing between independently trained
  models is possible (will be monitored and post-sorted if observed).
- **Intermittent demand**: plain quantile LightGBM may collapse low quantiles
  to zero for slow movers (risk R5).
- **Single-period newsvendor**: no multi-period carryover, lead-time demand
  aggregation, or capacity constraints in the first optimization cut.

## Engineering

- **Single-node by design**: DuckDB + one machine. Fine for M5 (~59M rows);
  beyond ~10× that, the storage ADR must be revisited (MotherDuck/warehouse).
- **Single writer**: pipeline steps must not run concurrently against one DB file.
- **`rolling_features.sql` is hand-mirrored** from `configs/features.yaml`
  until the Volume 2 generator replaces it — the one temporary DRY exception.
- Python 3.12 is the floor but local dev runs 3.13; both are in CI.

## Future extensions (beyond the roadmap)

Hierarchical forecast reconciliation · conformal prediction for calibrated
intervals · price-elasticity/promo uplift modeling · (s,S) and multi-echelon
policies · FastAPI serving layer · DuckDB → MotherDuck/warehouse migration path.
