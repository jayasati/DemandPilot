"""Newsvendor recommendation builder.

Translates quantile forecasts into order-quantity recommendations with cost
rationale (ADR-003, ADR-012). Recommendations are computed retrospectively —
"as of" the most recent origin date for which a lead-time-ahead OUTCOME
already exists in the feature snapshot, not a forecast into genuinely
unobserved future dates (ADR-016). Reuses the exact assembly and training
machinery from ``demandpilot.forecasting`` so a recommendation is built from
the same leakage-safe, future-known-vs-history-derived feature split.
"""

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import cast

import duckdb
import polars as pl

from demandpilot.config.models import CostsConfig, FeaturesConfig, ForecastConfig
from demandpilot.core.newsvendor import safety_stock
from demandpilot.exceptions import OptimizationError
from demandpilot.features.snapshots import latest_snapshot_table
from demandpilot.forecasting.dataset import HorizonDatasetAssembler
from demandpilot.forecasting.model import QuantileForecaster
from demandpilot.sqlrender import SqlRenderer

logger = logging.getLogger(__name__)

RECOMMENDATIONS_TABLE = "recommendations"


@dataclass(frozen=True)
class Recommendation:
    """One store/SKU order-quantity recommendation with its cost rationale."""

    store_id: str
    sku_id: str
    origin_date: date
    target_date: date
    lead_time_days: int
    order_quantity: float
    median_forecast: float
    safety_stock: float
    critical_fractile: float
    understock_cost_ratio: float
    overstock_cost_ratio: float
    actual_demand: float


@dataclass(frozen=True)
class RecommendationReport:
    """Outcome of one recommendation-building run."""

    snapshot_table: str
    lead_time_days: int
    recommendation_date: date
    recommendations: tuple[Recommendation, ...]


def _train_validation_split(
    dataset: pl.DataFrame, validation_size_days: int
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Two-way chronological split for early-stopping only.

    Unlike ``demandpilot.forecasting.split.chronological_split`` (which
    carves out a held-out test set for backtesting), this only needs a
    validation slice to early-stop the model that will then predict on the
    current rows — there is no separate "test" partition here.

    Raises:
        OptimizationError: If there are too few distinct origin dates.
    """
    origin_dates = sorted(dataset["origin_date"].unique().to_list())
    if len(origin_dates) <= validation_size_days:
        raise OptimizationError(
            f"Not enough distinct origin dates ({len(origin_dates)}) for a validation "
            f"window of {validation_size_days} days; need at least {validation_size_days + 1}."
        )
    validation_start = origin_dates[-validation_size_days]
    train = dataset.filter(pl.col("origin_date") < validation_start)
    validation = dataset.filter(pl.col("origin_date") >= validation_start)
    return train, validation


class RecommendationBuilder:
    """Builds newsvendor order-quantity recommendations from a feature snapshot."""

    def __init__(self, sql_dir: Path) -> None:
        """Create a builder.

        Args:
            sql_dir: Directory containing SQL files and templates.
        """
        self._assembler = HorizonDatasetAssembler(SqlRenderer(sql_dir))

    def build(
        self,
        connection: duckdb.DuckDBPyConnection,
        features_config: FeaturesConfig,
        forecast_config: ForecastConfig,
        costs_config: CostsConfig,
        lead_time_days: int,
        snapshot_table: str | None = None,
    ) -> RecommendationReport:
        """Build recommendations for every series at the most recent known origin.

        Args:
            connection: Open (read-only is sufficient) DuckDB connection.
            features_config: Validated feature engineering configuration.
            forecast_config: Validated forecasting configuration (supplies
                LightGBM hyperparameters and the validation window size).
            costs_config: Validated cost configuration (supplies the
                cost-implied critical fractile — ADR-012).
            lead_time_days: Horizon to recommend for (typically
                ``configs/simulation.yaml``'s ``lead_time_days``).
            snapshot_table: Feature snapshot to use; defaults to the most
                recently built one.

        Returns:
            The recommendation report.

        Raises:
            FeatureError: If no snapshot exists.
            OptimizationError: If there is no data at ``lead_time_days``, or
                too few origin dates for the validation window.
        """
        table = snapshot_table or latest_snapshot_table(connection)
        dataset = self._assembler.assemble(
            connection, features_config, table, lead_time_days, origin_stride_days=1
        )
        if dataset.height == 0:
            raise OptimizationError(
                f"No rows available at lead_time_days={lead_time_days} in {table} — "
                "the snapshot may not span enough days for this lead time."
            )

        # Polars' Series.max() is typed broadly; the origin_date column is a Date
        # dtype and the dataset is non-empty at this point, so this is always a date.
        max_origin = cast(date, dataset["origin_date"].max())
        current_rows = dataset.filter(pl.col("origin_date") == max_origin)
        training_rows = dataset.filter(pl.col("origin_date") < max_origin)
        train, validation = _train_validation_split(
            training_rows, forecast_config.train.validation_size_days
        )
        logger.info(
            "Recommendation dataset: %d train / %d validation / %d current rows (as of %s)",
            train.height,
            validation.height,
            current_rows.height,
            max_origin,
        )

        quantiles = sorted({0.5, costs_config.critical_fractile})
        categorical_columns = tuple(
            col for col in features_config.categorical_features if col in dataset.columns
        )
        forecaster = QuantileForecaster(forecast_config.model, categorical_columns)
        models = forecaster.fit(train, validation, quantiles)
        predictions = forecaster.predict(models, current_rows)

        median_forecast = predictions[0.5]
        order_quantity = predictions[costs_config.critical_fractile]

        recommendations = tuple(
            Recommendation(
                store_id=row["store_id"],
                sku_id=row["sku_id"],
                origin_date=row["origin_date"],
                target_date=row["target_date"],
                lead_time_days=lead_time_days,
                order_quantity=float(order_quantity[i]),
                median_forecast=float(median_forecast[i]),
                safety_stock=safety_stock(float(order_quantity[i]), float(median_forecast[i])),
                critical_fractile=costs_config.critical_fractile,
                understock_cost_ratio=costs_config.understock_cost_ratio,
                overstock_cost_ratio=costs_config.overstock_cost_ratio,
                actual_demand=float(row["target"]),
            )
            for i, row in enumerate(current_rows.iter_rows(named=True))
        )
        logger.info(
            "Built %d recommendations as of %s (lead_time_days=%d, critical_fractile=%.3f)",
            len(recommendations),
            max_origin,
            lead_time_days,
            costs_config.critical_fractile,
        )
        return RecommendationReport(
            snapshot_table=table,
            lead_time_days=lead_time_days,
            recommendation_date=max_origin,
            recommendations=recommendations,
        )


def persist_recommendations(
    connection: duckdb.DuckDBPyConnection, report: RecommendationReport
) -> None:
    """Materialize a recommendation report into the ``recommendations`` table.

    Replaces the table wholesale (``CREATE OR REPLACE``) rather than keeping
    history — a recommendation set is a live operational output refreshed on
    each run, unlike the fully-versioned feature snapshots it's built from
    (ADR-011, ADR-016). The schema is inferred from the report's own fields
    rather than hand-declared in ``sql/create_tables.sql``, so it can never
    drift out of sync with :class:`Recommendation`.

    Args:
        connection: Open (writable) DuckDB connection.
        report: The report to persist.

    Raises:
        OptimizationError: If the table cannot be created.
    """
    frame = pl.DataFrame(
        [{**vars(r), "snapshot_table": report.snapshot_table} for r in report.recommendations]
    )
    try:
        connection.register("_recommendations_df", frame.to_arrow())
        connection.execute(
            f"CREATE OR REPLACE TABLE {RECOMMENDATIONS_TABLE} AS SELECT * FROM _recommendations_df"
        )
    except duckdb.Error as exc:
        raise OptimizationError(f"Failed to persist recommendations: {exc}") from exc
    finally:
        connection.unregister("_recommendations_df")
    logger.info("Persisted %d rows to %s", frame.height, RECOMMENDATIONS_TABLE)
