"""Gathers the data an executive report renders.

Reads (never recomputes) what earlier volumes already produced: feature
snapshot lineage, the latest MLflow backtest run, and the ``recommendations``
/``simulation_results`` tables — each optional, since a report can be built
before any of `train`/`recommend`/`simulate` has ever run.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import duckdb

from demandpilot.config.models import CostsConfig, ForecastConfig
from demandpilot.mlflow_utils import latest_run


@dataclass(frozen=True)
class SnapshotSummary:
    """Lineage of the feature snapshot the report is built from."""

    version: int
    table_name: str
    created_at: datetime
    git_commit: str | None
    row_count: int
    min_date: date | None
    max_date: date | None


@dataclass(frozen=True)
class QuantileAccuracy:
    """Backtest accuracy for one forecast quantile."""

    quantile: float
    pinball: float
    coverage: float


@dataclass(frozen=True)
class ForecastAccuracySummary:
    """The latest MLflow training run's backtest metrics."""

    run_id: str
    trained_at: datetime
    wape: float | None
    bias: float | None
    rmse: float | None
    quantile_metrics: tuple[QuantileAccuracy, ...]


@dataclass(frozen=True)
class RecommendationRow:
    """One recommendation, for the "largest misses" detail table."""

    store_id: str
    sku_id: str
    origin_date: date
    target_date: date
    order_quantity: float
    median_forecast: float
    safety_stock: float
    actual_demand: float
    absolute_miss: float


@dataclass(frozen=True)
class RecommendationsSummary:
    """Summary of the current ``recommendations`` table."""

    n_recommendations: int
    recommendation_date: date
    lead_time_days: int
    total_order_quantity: float
    total_safety_stock: float
    critical_fractile: float
    snapshot_table: str
    top_misses: tuple[RecommendationRow, ...]


@dataclass(frozen=True)
class PolicySummaryRow:
    """Aggregate cost outcomes for one simulated policy."""

    policy: str
    n_decisions: int
    total_cost: float
    total_understock_cost: float
    total_overstock_cost: float
    mean_cost: float


@dataclass(frozen=True)
class SimulationSummary:
    """Summary of the current ``simulation_results`` table."""

    policies: tuple[PolicySummaryRow, ...]

    @property
    def savings(self) -> float | None:
        """Classical baseline cost minus ML cost, or None if either is missing."""
        by_policy = {p.policy: p for p in self.policies}
        if "classical_baseline" in by_policy and "ml_quantile" in by_policy:
            return by_policy["classical_baseline"].total_cost - by_policy["ml_quantile"].total_cost
        return None


@dataclass(frozen=True)
class CostsSummary:
    """The cost assumptions behind every recommendation and simulation."""

    currency: str
    unit_cost_ratio: float
    salvage_ratio: float
    holding_cost_ratio: float
    stockout_penalty_ratio: float
    understock_cost_ratio: float
    overstock_cost_ratio: float
    critical_fractile: float


@dataclass(frozen=True)
class ReportData:
    """Everything the executive report template renders."""

    generated_at: datetime
    snapshot: SnapshotSummary | None
    forecast_accuracy: ForecastAccuracySummary | None
    recommendations: RecommendationsSummary | None
    simulation: SimulationSummary | None
    costs: CostsSummary


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    """Whether ``table_name`` exists in the connected database."""
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [table_name]
    ).fetchone()
    return row is not None and row[0] > 0


def _parse_quantile_metrics(metrics: dict[str, float]) -> tuple[QuantileAccuracy, ...]:
    """Reconstruct per-quantile accuracy from the flat MLflow metrics dict.

    Mirrors the tag scheme in ``ForecastingPipeline._log_to_mlflow``:
    ``pinball_q0_1`` / ``coverage_q0_1`` for quantile ``0.1``.
    """
    by_quantile: dict[float, dict[str, float]] = {}
    for key, value in metrics.items():
        for prefix, field in (("pinball_q", "pinball"), ("coverage_q", "coverage")):
            if key.startswith(prefix):
                quantile = float(key.removeprefix(prefix).replace("_", "."))
                by_quantile.setdefault(quantile, {})[field] = value
    return tuple(
        QuantileAccuracy(
            quantile=quantile,
            pinball=values.get("pinball", float("nan")),
            coverage=values.get("coverage", float("nan")),
        )
        for quantile, values in sorted(by_quantile.items())
    )


def _gather_snapshot(
    connection: duckdb.DuckDBPyConnection, snapshot_table: str | None
) -> SnapshotSummary | None:
    """Look up manifest lineage for ``snapshot_table``, or the latest snapshot."""
    columns = "version, table_name, created_at, git_commit, row_count, min_date, max_date"
    if snapshot_table:
        row = connection.execute(
            f"SELECT {columns} FROM feature_snapshots WHERE table_name = ?", [snapshot_table]
        ).fetchone()
    else:
        row = connection.execute(
            f"SELECT {columns} FROM feature_snapshots ORDER BY version DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    return SnapshotSummary(
        version=row[0],
        table_name=row[1],
        created_at=row[2],
        git_commit=row[3],
        row_count=row[4],
        min_date=row[5],
        max_date=row[6],
    )


def _gather_forecast_accuracy(
    tracking_uri: str, experiment_name: str
) -> ForecastAccuracySummary | None:
    """Fetch and parse the latest MLflow training run's metrics."""
    run = latest_run(tracking_uri, experiment_name)
    if run is None:
        return None
    return ForecastAccuracySummary(
        run_id=run.run_id,
        trained_at=run.start_time,
        wape=run.metrics.get("wape"),
        bias=run.metrics.get("bias"),
        rmse=run.metrics.get("rmse"),
        quantile_metrics=_parse_quantile_metrics(run.metrics),
    )


def _gather_recommendations(
    connection: duckdb.DuckDBPyConnection, sql_dir: Path
) -> RecommendationsSummary | None:
    """Summarize the ``recommendations`` table, if it exists and has rows."""
    if not _table_exists(connection, "recommendations"):
        return None
    summary_sql = (sql_dir / "report_recommendations_summary.sql").read_text(encoding="utf-8")
    row = connection.execute(summary_sql).fetchone()
    if row is None or row[0] == 0:
        return None
    top_misses_sql = (sql_dir / "report_recommendations_top_misses.sql").read_text(encoding="utf-8")
    top_rows = connection.execute(top_misses_sql).fetchall()
    return RecommendationsSummary(
        n_recommendations=row[0],
        recommendation_date=row[1],
        lead_time_days=row[2],
        total_order_quantity=row[3],
        total_safety_stock=row[4],
        critical_fractile=row[5],
        snapshot_table=row[6],
        top_misses=tuple(
            RecommendationRow(
                store_id=r[0],
                sku_id=r[1],
                origin_date=r[2],
                target_date=r[3],
                order_quantity=r[4],
                median_forecast=r[5],
                safety_stock=r[6],
                actual_demand=r[7],
                absolute_miss=r[8],
            )
            for r in top_rows
        ),
    )


def _gather_simulation(
    connection: duckdb.DuckDBPyConnection, sql_dir: Path
) -> SimulationSummary | None:
    """Summarize the ``simulation_results`` table, if it exists and has rows."""
    if not _table_exists(connection, "simulation_results"):
        return None
    summary_sql = (sql_dir / "report_simulation_summary.sql").read_text(encoding="utf-8")
    rows = connection.execute(summary_sql).fetchall()
    if not rows:
        return None
    return SimulationSummary(
        policies=tuple(
            PolicySummaryRow(
                policy=r[0],
                n_decisions=r[1],
                total_cost=r[2],
                total_understock_cost=r[3],
                total_overstock_cost=r[4],
                mean_cost=r[5],
            )
            for r in rows
        )
    )


def gather_report_data(
    connection: duckdb.DuckDBPyConnection,
    sql_dir: Path,
    forecast_config: ForecastConfig,
    costs_config: CostsConfig,
    tracking_uri: str,
    snapshot_table: str | None,
) -> ReportData:
    """Gather every section of the executive report.

    Args:
        connection: Open (read-only is sufficient) DuckDB connection.
        sql_dir: Directory containing the report SQL files.
        forecast_config: Supplies the MLflow experiment name to look up.
        costs_config: Supplies the cost-assumptions section.
        tracking_uri: A fully resolved MLflow tracking URI.
        snapshot_table: Feature snapshot to report lineage for; defaults to
            the most recently built one.

    Returns:
        The gathered data, ready for template rendering.
    """
    return ReportData(
        generated_at=datetime.now(UTC),
        snapshot=_gather_snapshot(connection, snapshot_table),
        forecast_accuracy=_gather_forecast_accuracy(
            tracking_uri, forecast_config.mlflow.experiment_name
        ),
        recommendations=_gather_recommendations(connection, sql_dir),
        simulation=_gather_simulation(connection, sql_dir),
        costs=CostsSummary(
            currency=costs_config.currency,
            unit_cost_ratio=costs_config.unit_cost_ratio,
            salvage_ratio=costs_config.salvage_ratio,
            holding_cost_ratio=costs_config.holding_cost_ratio,
            stockout_penalty_ratio=costs_config.stockout_penalty_ratio,
            understock_cost_ratio=costs_config.understock_cost_ratio,
            overstock_cost_ratio=costs_config.overstock_cost_ratio,
            critical_fractile=costs_config.critical_fractile,
        ),
    )
