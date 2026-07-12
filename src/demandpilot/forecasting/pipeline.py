"""Orchestrates one full forecasting run.

Assembles the multi-horizon dataset from a feature snapshot (ADR-008/014/015),
splits it chronologically, trains one quantile model per quantile (config
quantiles union the cost-implied critical fractile — ADR-012), evaluates on
the held-out test set, and logs everything to MLflow (ADR-011 lineage: the
snapshot table name is logged as a run param so a run always traces back to
the exact data it trained on).

The five core metrics (pinball, coverage, wape, bias, rmse) are always
computed — they're cheap pure functions — regardless of which subset
``forecast.yaml``'s ``metrics`` list names; that list documents which ones
downstream reporting (Volume 6) surfaces, not which are computed.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import duckdb
import mlflow
import mlflow.lightgbm
import numpy as np

from demandpilot.config.models import CostsConfig, FeaturesConfig, ForecastConfig
from demandpilot.core.metrics import bias, coverage, pinball_loss, rmse, wape
from demandpilot.exceptions import ForecastError
from demandpilot.forecasting.dataset import HorizonDatasetAssembler, assemble_multi_horizon
from demandpilot.forecasting.model import QuantileForecaster, QuantileModel
from demandpilot.forecasting.split import chronological_split
from demandpilot.sqlrender import SqlRenderer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuantileMetrics:
    """Metrics for one trained quantile model, evaluated on the test set."""

    quantile: float
    pinball: float
    coverage: float


@dataclass(frozen=True)
class BacktestReport:
    """Outcome of one full training + backtest run."""

    snapshot_table: str
    horizon_days: int
    n_train_rows: int
    n_validation_rows: int
    n_test_rows: int
    quantile_metrics: tuple[QuantileMetrics, ...]
    wape: float
    bias: float
    rmse: float
    mlflow_run_id: str | None


def _latest_snapshot_table(connection: duckdb.DuckDBPyConnection) -> str:
    """Return the most recently built snapshot table name.

    Raises:
        ForecastError: If no snapshot has ever been built.
    """
    row = connection.execute(
        "SELECT table_name FROM feature_snapshots ORDER BY version DESC LIMIT 1"
    ).fetchone()
    if row is None:
        raise ForecastError("No feature snapshots found — run `demandpilot build-features` first.")
    return str(row[0])


class ForecastingPipeline:
    """Runs one end-to-end assemble + train + backtest + MLflow-logging pass."""

    def __init__(self, sql_dir: Path) -> None:
        """Create a pipeline.

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
        snapshot_table: str | None = None,
    ) -> BacktestReport:
        """Assemble, split, train, evaluate, and log one forecasting run.

        Args:
            connection: Open (read-only is sufficient) DuckDB connection.
            features_config: Validated feature engineering configuration.
            forecast_config: Validated forecasting configuration.
            costs_config: Validated cost configuration (supplies the
                cost-implied critical fractile — ADR-012).
            snapshot_table: Feature snapshot to train on; defaults to the
                most recently built one.

        Returns:
            The backtest report, including the MLflow run id.

        Raises:
            ForecastError: If no snapshot exists, or the dataset has too few
                distinct origin dates for the configured split sizes.
        """
        table = snapshot_table or _latest_snapshot_table(connection)
        logger.info("Assembling multi-horizon dataset from %s", table)
        dataset = assemble_multi_horizon(
            connection,
            self._assembler,
            features_config,
            table,
            forecast_config.horizon_days,
            forecast_config.train.origin_stride_days,
        )
        logger.info(
            "Assembled %d rows across %d horizons", dataset.height, forecast_config.horizon_days
        )

        split = chronological_split(dataset, forecast_config.train)
        logger.info(
            "Split: %d train / %d validation / %d test rows",
            split.train.height,
            split.validation.height,
            split.test.height,
        )

        quantiles = sorted({*forecast_config.quantiles, costs_config.critical_fractile})
        categorical_columns = tuple(
            col for col in features_config.categorical_features if col in dataset.columns
        )
        forecaster = QuantileForecaster(forecast_config.model, categorical_columns)
        models = forecaster.fit(split.train, split.validation, quantiles)
        predictions = forecaster.predict(models, split.test)

        y_test = split.test["target"].to_numpy().astype(np.float64)
        quantile_metrics = tuple(
            QuantileMetrics(
                quantile=q,
                pinball=pinball_loss(y_test, predictions[q], q),
                coverage=coverage(y_test, predictions[q]),
            )
            for q in quantiles
        )
        median_prediction = predictions[0.5]
        wape_value = wape(y_test, median_prediction)
        bias_value = bias(y_test, median_prediction)
        rmse_value = rmse(y_test, median_prediction)

        run_id = self._log_to_mlflow(
            forecast_config=forecast_config,
            snapshot_table=table,
            quantiles=quantiles,
            models=models,
            n_train_rows=split.train.height,
            n_validation_rows=split.validation.height,
            n_test_rows=split.test.height,
            quantile_metrics=quantile_metrics,
            wape_value=wape_value,
            bias_value=bias_value,
            rmse_value=rmse_value,
        )

        return BacktestReport(
            snapshot_table=table,
            horizon_days=forecast_config.horizon_days,
            n_train_rows=split.train.height,
            n_validation_rows=split.validation.height,
            n_test_rows=split.test.height,
            quantile_metrics=quantile_metrics,
            wape=wape_value,
            bias=bias_value,
            rmse=rmse_value,
            mlflow_run_id=run_id,
        )

    def _log_to_mlflow(
        self,
        forecast_config: ForecastConfig,
        snapshot_table: str,
        quantiles: list[float],
        models: list[QuantileModel],
        n_train_rows: int,
        n_validation_rows: int,
        n_test_rows: int,
        quantile_metrics: tuple[QuantileMetrics, ...],
        wape_value: float,
        bias_value: float,
        rmse_value: float,
    ) -> str | None:
        """Log params, metrics, and models for this run; return the MLflow run id."""
        mlflow.set_experiment(forecast_config.mlflow.experiment_name)
        with mlflow.start_run() as run:
            mlflow.log_param("snapshot_table", snapshot_table)
            mlflow.log_param("horizon_days", forecast_config.horizon_days)
            mlflow.log_param("origin_stride_days", forecast_config.train.origin_stride_days)
            mlflow.log_param("quantiles", quantiles)
            mlflow.log_params({f"model__{k}": v for k, v in forecast_config.model.params.items()})
            mlflow.log_metric("n_train_rows", n_train_rows)
            mlflow.log_metric("n_validation_rows", n_validation_rows)
            mlflow.log_metric("n_test_rows", n_test_rows)
            mlflow.log_metric("wape", wape_value)
            mlflow.log_metric("bias", bias_value)
            mlflow.log_metric("rmse", rmse_value)
            for qm in quantile_metrics:
                tag = str(qm.quantile).replace(".", "_")
                mlflow.log_metric(f"pinball_q{tag}", qm.pinball)
                mlflow.log_metric(f"coverage_q{tag}", qm.coverage)

            if forecast_config.mlflow.register_model:
                for model in models:
                    tag = str(model.quantile).replace(".", "_")
                    mlflow.lightgbm.log_model(
                        model.booster,
                        artifact_path=f"model_q{tag}",
                        registered_model_name=f"{forecast_config.mlflow.model_name}-q{tag}",
                    )
            return str(run.info.run_id)
