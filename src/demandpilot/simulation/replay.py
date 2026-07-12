"""Historical policy-replay simulation engine.

Compares the ML quantile-forecast policy against the classical baseline
(``demandpilot.simulation.baseline``) on real, held-out historical outcomes:
for each of many past decision points, both policies compute an order
quantity using only data available at that point, and both are graded
against the same realized demand with the newsvendor cost function
(``demandpilot.core.newsvendor.realized_cost_breakdown``). See ADR-017 for
the full design rationale, including why this reuses Volume 3's chronological
train/validation/test split rather than a new mechanism.
"""

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import numpy.typing as npt
import polars as pl

from demandpilot.config.models import (
    CostsConfig,
    FeaturesConfig,
    ForecastConfig,
    SimulationConfig,
)
from demandpilot.core.newsvendor import realized_cost_breakdown
from demandpilot.exceptions import SimulationError
from demandpilot.features.snapshots import latest_snapshot_table
from demandpilot.forecasting.dataset import HorizonDatasetAssembler
from demandpilot.forecasting.model import QuantileForecaster
from demandpilot.forecasting.split import chronological_split
from demandpilot.simulation.baseline import classical_order_up_to
from demandpilot.sqlrender import SqlRenderer

logger = logging.getLogger(__name__)

SIMULATION_RESULTS_TABLE = "simulation_results"

_ML_POLICY = "ml_quantile"
_BASELINE_POLICY = "classical_baseline"


@dataclass(frozen=True)
class PolicyDecision:
    """One (policy, series, origin) decision and its realized outcome.

    ``cost`` is always ``understock_cost + overstock_cost``.
    """

    policy: str
    store_id: str
    sku_id: str
    origin_date: date
    target_date: date
    order_quantity: float
    actual_demand: float
    sell_price: float
    understock_cost: float
    overstock_cost: float
    cost: float


@dataclass(frozen=True)
class PolicyMetrics:
    """Aggregate cost outcomes for one policy across the replay window."""

    policy: str
    total_cost: float
    total_understock_cost: float
    total_overstock_cost: float
    mean_cost: float
    n_decisions: int


@dataclass(frozen=True)
class PolicyComparison:
    """Outcome of one historical policy-replay simulation."""

    snapshot_table: str
    lead_time_days: int
    review_period_days: int
    service_level: float
    demand_distribution: str
    ml_metrics: PolicyMetrics
    baseline_metrics: PolicyMetrics
    decisions: tuple[PolicyDecision, ...]

    @property
    def savings(self) -> float:
        """Positive means the ML policy cost less than the classical baseline."""
        return self.baseline_metrics.total_cost - self.ml_metrics.total_cost


def _apply_review_period(dataset: pl.DataFrame, review_period_days: int) -> pl.DataFrame:
    """Keep only origins on a 1-in-N calendar-day cadence (epoch-aligned).

    Mirrors the origin-sampling filter used in the generated feature/dataset
    SQL (ADR-015) so review cadence is applied consistently. ``1`` is a no-op.
    """
    epoch = date(1970, 1, 1)
    return dataset.filter(
        (pl.col("origin_date") - pl.lit(epoch)).dt.total_days() % review_period_days == 0
    )


def _build_series_history(
    train_and_validation: pl.DataFrame,
) -> dict[tuple[str, str], npt.NDArray[np.float64]]:
    """Group the pre-test data into a per-series historical demand sample."""
    history: dict[tuple[str, str], npt.NDArray[np.float64]] = {}
    for key, group in train_and_validation.group_by(["store_id", "sku_id"]):
        store_id, sku_id = key
        history[(str(store_id), str(sku_id))] = group["target"].to_numpy().astype(np.float64)
    return history


def _metrics_for(policy: str, decisions: list[PolicyDecision]) -> PolicyMetrics:
    """Aggregate one policy's decisions into totals."""
    costs = np.array([d.cost for d in decisions], dtype=np.float64)
    understock_costs = np.array([d.understock_cost for d in decisions], dtype=np.float64)
    overstock_costs = np.array([d.overstock_cost for d in decisions], dtype=np.float64)
    return PolicyMetrics(
        policy=policy,
        total_cost=float(costs.sum()),
        total_understock_cost=float(understock_costs.sum()),
        total_overstock_cost=float(overstock_costs.sum()),
        mean_cost=float(costs.mean()),
        n_decisions=len(decisions),
    )


class SimulationEngine:
    """Runs one historical policy-replay simulation."""

    def __init__(self, sql_dir: Path) -> None:
        """Create an engine.

        Args:
            sql_dir: Directory containing SQL files and templates.
        """
        self._assembler = HorizonDatasetAssembler(SqlRenderer(sql_dir))

    def run(
        self,
        connection: duckdb.DuckDBPyConnection,
        features_config: FeaturesConfig,
        forecast_config: ForecastConfig,
        costs_config: CostsConfig,
        simulation_config: SimulationConfig,
        snapshot_table: str | None = None,
    ) -> PolicyComparison:
        """Replay both policies over held-out historical decision points.

        Args:
            connection: Open (read-only is sufficient) DuckDB connection.
            features_config: Validated feature engineering configuration.
            forecast_config: Validated forecasting configuration (LightGBM
                hyperparameters and train/validation/test split sizes).
            costs_config: Validated cost configuration (critical fractile,
                cost ratios — ADR-012).
            simulation_config: Validated simulation configuration (lead time,
                review cadence, baseline distribution, service level).
            snapshot_table: Feature snapshot to use; defaults to the most
                recently built one.

        Returns:
            The policy comparison, including per-decision detail.

        Raises:
            FeatureError: If no snapshot exists.
            SimulationError: If there is no data at the configured lead time,
                or no rows survive review-period filtering.
            ForecastError: If the dataset has too few origin dates for the
                configured split sizes.
        """
        table = snapshot_table or latest_snapshot_table(connection)
        dataset = self._assembler.assemble(
            connection,
            features_config,
            table,
            simulation_config.lead_time_days,
            origin_stride_days=1,
        )
        if dataset.height == 0:
            raise SimulationError(
                f"No rows available at lead_time_days={simulation_config.lead_time_days} in {table}"
            )

        split = chronological_split(dataset, forecast_config.train)
        review_rows = _apply_review_period(split.test, simulation_config.review_period_days)
        if review_rows.height == 0:
            raise SimulationError(
                f"No test rows survive review_period_days="
                f"{simulation_config.review_period_days} filtering"
            )
        logger.info(
            "Simulation dataset: %d train / %d validation / %d test / %d reviewed rows",
            split.train.height,
            split.validation.height,
            split.test.height,
            review_rows.height,
        )

        categorical_columns = tuple(
            col for col in features_config.categorical_features if col in dataset.columns
        )
        forecaster = QuantileForecaster(forecast_config.model, categorical_columns)
        models = forecaster.fit(split.train, split.validation, [costs_config.critical_fractile])
        predictions = forecaster.predict(models, review_rows)
        ml_order_quantities = predictions[costs_config.critical_fractile]

        train_and_validation = pl.concat([split.train, split.validation])
        series_history = _build_series_history(train_and_validation)

        ml_decisions: list[PolicyDecision] = []
        baseline_decisions: list[PolicyDecision] = []
        skipped_no_history = 0

        for i, row in enumerate(review_rows.iter_rows(named=True)):
            history = series_history.get((row["store_id"], row["sku_id"]))
            if history is None or history.size == 0:
                skipped_no_history += 1
                continue

            actual_demand = float(row["target"])
            sell_price = float(row["sell_price"])

            ml_quantity = float(ml_order_quantities[i])
            baseline_quantity = classical_order_up_to(
                history,
                simulation_config.lead_time_days,
                simulation_config.service_level,
                simulation_config.demand_distribution,
                simulation_config.n_simulations,
                simulation_config.random_seed,
            )

            for policy, quantity, bucket in (
                (_ML_POLICY, ml_quantity, ml_decisions),
                (_BASELINE_POLICY, baseline_quantity, baseline_decisions),
            ):
                understock_cost, overstock_cost = realized_cost_breakdown(
                    quantity,
                    actual_demand,
                    costs_config.understock_cost_ratio,
                    costs_config.overstock_cost_ratio,
                    sell_price,
                )
                bucket.append(
                    PolicyDecision(
                        policy=policy,
                        store_id=row["store_id"],
                        sku_id=row["sku_id"],
                        origin_date=row["origin_date"],
                        target_date=row["target_date"],
                        order_quantity=quantity,
                        actual_demand=actual_demand,
                        sell_price=sell_price,
                        understock_cost=understock_cost,
                        overstock_cost=overstock_cost,
                        cost=understock_cost + overstock_cost,
                    )
                )

        if not ml_decisions:
            raise SimulationError(
                "No reviewed rows had prior history to build a baseline from "
                f"({skipped_no_history} skipped)"
            )
        if skipped_no_history:
            logger.info(
                "Skipped %d reviewed rows with no prior history for their series",
                skipped_no_history,
            )

        comparison = PolicyComparison(
            snapshot_table=table,
            lead_time_days=simulation_config.lead_time_days,
            review_period_days=simulation_config.review_period_days,
            service_level=simulation_config.service_level,
            demand_distribution=simulation_config.demand_distribution,
            ml_metrics=_metrics_for(_ML_POLICY, ml_decisions),
            baseline_metrics=_metrics_for(_BASELINE_POLICY, baseline_decisions),
            decisions=tuple(ml_decisions + baseline_decisions),
        )
        logger.info(
            "Simulated %d decisions: ML total cost=%.2f, baseline total cost=%.2f, savings=%.2f",
            comparison.ml_metrics.n_decisions,
            comparison.ml_metrics.total_cost,
            comparison.baseline_metrics.total_cost,
            comparison.savings,
        )
        return comparison


def persist_simulation_results(
    connection: duckdb.DuckDBPyConnection, comparison: PolicyComparison
) -> None:
    """Materialize a policy comparison into the ``simulation_results`` table.

    Replaces the table wholesale, like ``recommendations`` (ADR-016) — a live
    operational output, not a versioned artifact.

    Args:
        connection: Open (writable) DuckDB connection.
        comparison: The comparison to persist.

    Raises:
        SimulationError: If the table cannot be created.
    """
    frame = pl.DataFrame(
        [{**vars(d), "snapshot_table": comparison.snapshot_table} for d in comparison.decisions]
    )
    try:
        connection.register("_simulation_results_df", frame.to_arrow())
        connection.execute(
            f"CREATE OR REPLACE TABLE {SIMULATION_RESULTS_TABLE} "
            "AS SELECT * FROM _simulation_results_df"
        )
    except duckdb.Error as exc:
        raise SimulationError(f"Failed to persist simulation results: {exc}") from exc
    finally:
        connection.unregister("_simulation_results_df")
    logger.info("Persisted %d rows to %s", frame.height, SIMULATION_RESULTS_TABLE)
