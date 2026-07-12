"""End-to-end forecasting tests: dataset assembly, split, training, backtest."""

import math
from datetime import timedelta

import mlflow
import polars as pl
import pytest
from mlflow.tracking import MlflowClient

from demandpilot.config import load_config
from demandpilot.config.models import (
    CostsConfig,
    ForecastConfig,
    ForecastMlflowConfig,
    ModelConfig,
    TrainConfig,
)
from demandpilot.data import Database, M5Ingestor, apply_schema
from demandpilot.exceptions import ForecastError
from demandpilot.features import FeatureSnapshotBuilder
from demandpilot.forecasting import (
    ForecastingPipeline,
    HorizonDatasetAssembler,
    assemble_multi_horizon,
)
from demandpilot.sqlrender import SqlRenderer

pytestmark = pytest.mark.integration

_TEST_MODEL_PARAMS = {
    "num_leaves": 7,
    "learning_rate": 0.1,
    "n_estimators": 15,
    "max_depth": -1,
    "min_child_samples": 5,
    "subsample": 1.0,
    "colsample_bytree": 1.0,
    "random_state": 42,
}


@pytest.fixture
def snapshot_db(tmp_path, repo_root, m5_fixture_dir):
    db = Database(tmp_path / "test.duckdb")
    apply_schema(db, repo_root / "sql")
    M5Ingestor(db, SqlRenderer(repo_root / "sql"), m5_fixture_dir).ingest()
    features_config = load_config(repo_root).features
    info = FeatureSnapshotBuilder(db, repo_root / "sql", repo_root).build(features_config)
    return db, features_config, info.table_name


def _small_forecast_config(
    *,
    horizon_days: int = 5,
    test_size_days: int = 3,
    validation_size_days: int = 3,
    origin_stride_days: int = 1,
    register_model: bool = False,
    experiment_name: str = "test-forecast",
    model_name: str = "test-model",
) -> ForecastConfig:
    return ForecastConfig(
        target_column="units_sold",
        date_column="date",
        id_columns=["store_id", "sku_id"],
        horizon_days=horizon_days,
        frequency="D",
        strategy="direct",
        quantiles=[0.1, 0.5, 0.9],
        metrics=["pinball", "coverage", "wape", "bias", "rmse"],
        train=TrainConfig(
            test_size_days=test_size_days,
            validation_size_days=validation_size_days,
            cv_folds=1,
            origin_stride_days=origin_stride_days,
        ),
        model=ModelConfig(
            type="lightgbm",
            objective="quantile",
            params=_TEST_MODEL_PARAMS,
            early_stopping_rounds=5,
        ),
        mlflow=ForecastMlflowConfig(
            experiment_name=experiment_name,
            register_model=register_model,
            model_name=model_name,
        ),
    )


def _costs_config() -> CostsConfig:
    return CostsConfig(
        currency="USD",
        unit_cost_ratio=0.65,
        salvage_ratio=0.35,
        holding_cost_ratio=0.02,
        stockout_penalty_ratio=0.10,
    )


def test_assemble_multi_horizon_produces_expected_columns(snapshot_db, repo_root):
    db, features_config, table = snapshot_db
    assembler = HorizonDatasetAssembler(SqlRenderer(repo_root / "sql"))
    with db.connect(read_only=True) as con:
        dataset = assemble_multi_horizon(con, assembler, features_config, table, 3, 1)
    assert {"origin_date", "target_date", "horizon", "target"}.issubset(dataset.columns)
    assert set(dataset["horizon"].unique().to_list()) == {1, 2, 3}


def test_assembled_target_matches_actual_future_sales(snapshot_db, repo_root):
    db, features_config, table = snapshot_db
    assembler = HorizonDatasetAssembler(SqlRenderer(repo_root / "sql"))
    with db.connect(read_only=True) as con:
        dataset = assemble_multi_horizon(con, assembler, features_config, table, 2, 1)
        row = (
            dataset.filter(
                (pl.col("store_id") == "CA_1")
                & (pl.col("sku_id") == "HOBBIES_1_001")
                & (pl.col("horizon") == 1)
            )
            .sort("origin_date")
            .row(0, named=True)
        )
        expected = con.execute(
            "SELECT units_sold FROM sales WHERE store_id = ? AND sku_id = ? AND date = ?",
            ["CA_1", "HOBBIES_1_001", row["target_date"]],
        ).fetchone()[0]
    assert row["target"] == expected
    assert row["target_date"] - row["origin_date"] == timedelta(days=1)


def test_future_known_columns_come_from_target_date(snapshot_db, repo_root):
    """Calendar features must reflect the TARGET day, not the origin day."""
    db, features_config, table = snapshot_db
    assembler = HorizonDatasetAssembler(SqlRenderer(repo_root / "sql"))
    with db.connect(read_only=True) as con:
        dataset = assemble_multi_horizon(con, assembler, features_config, table, 3, 1)
        row = (
            dataset.filter(
                (pl.col("store_id") == "CA_1")
                & (pl.col("sku_id") == "HOBBIES_1_001")
                & (pl.col("horizon") == 3)
            )
            .sort("origin_date")
            .row(0, named=True)
        )
        expected_dow = con.execute(
            "SELECT day_of_week FROM calendar WHERE date = ?", [row["target_date"]]
        ).fetchone()[0]
    assert row["day_of_week"] == expected_dow


def test_history_derived_columns_come_from_origin_date(snapshot_db, repo_root):
    """lag_1 must reflect history before the ORIGIN day, not the target day."""
    db, features_config, table = snapshot_db
    assembler = HorizonDatasetAssembler(SqlRenderer(repo_root / "sql"))
    with db.connect(read_only=True) as con:
        dataset = assemble_multi_horizon(con, assembler, features_config, table, 2, 1)
        row = (
            dataset.filter(
                (pl.col("store_id") == "CA_1")
                & (pl.col("sku_id") == "HOBBIES_1_001")
                & (pl.col("horizon") == 1)
                & pl.col("units_sold_lag_1").is_not_null()
            )
            .sort("origin_date")
            .row(0, named=True)
        )
        expected_lag = con.execute(
            "SELECT units_sold FROM sales WHERE store_id = ? AND sku_id = ? AND date = ?",
            ["CA_1", "HOBBIES_1_001", row["origin_date"] - timedelta(days=1)],
        ).fetchone()[0]
    assert row["units_sold_lag_1"] == expected_lag


def test_origin_stride_subsamples_origins(snapshot_db, repo_root):
    db, features_config, table = snapshot_db
    assembler = HorizonDatasetAssembler(SqlRenderer(repo_root / "sql"))
    with db.connect(read_only=True) as con:
        full = assemble_multi_horizon(con, assembler, features_config, table, 1, 1)
        strided = assemble_multi_horizon(con, assembler, features_config, table, 1, 7)
    assert 0 < strided.height < full.height


def test_forecasting_pipeline_end_to_end(snapshot_db, repo_root, tmp_path):
    db, features_config, table = snapshot_db
    mlflow.set_tracking_uri(f"sqlite:///{(tmp_path / 'mlruns' / 'mlflow.db').as_posix()}")
    pipeline = ForecastingPipeline(repo_root / "sql")
    with db.connect(read_only=True) as con:
        report = pipeline.run(
            con, features_config, _small_forecast_config(), _costs_config(), table
        )

    assert report.snapshot_table == table
    assert report.n_train_rows > 0
    assert report.n_validation_rows > 0
    assert report.n_test_rows > 0
    assert report.mlflow_run_id is not None
    quantile_levels = {qm.quantile for qm in report.quantile_metrics}
    assert {0.1, 0.5, 0.9}.issubset(quantile_levels)
    for qm in report.quantile_metrics:
        assert qm.pinball >= 0
        assert 0.0 <= qm.coverage <= 1.0
    assert report.rmse >= 0
    assert not math.isnan(report.wape)


def test_forecasting_pipeline_defaults_to_latest_snapshot(snapshot_db, repo_root, tmp_path):
    db, features_config, _first_table = snapshot_db
    second = FeatureSnapshotBuilder(db, repo_root / "sql", repo_root).build(features_config)
    mlflow.set_tracking_uri(f"sqlite:///{(tmp_path / 'mlruns' / 'mlflow.db').as_posix()}")
    pipeline = ForecastingPipeline(repo_root / "sql")
    with db.connect(read_only=True) as con:
        report = pipeline.run(con, features_config, _small_forecast_config(), _costs_config())
    assert report.snapshot_table == second.table_name


def test_forecasting_pipeline_raises_without_any_snapshot(repo_root, tmp_path, m5_fixture_dir):
    db = Database(tmp_path / "test.duckdb")
    apply_schema(db, repo_root / "sql")
    M5Ingestor(db, SqlRenderer(repo_root / "sql"), m5_fixture_dir).ingest()
    features_config = load_config(repo_root).features
    mlflow.set_tracking_uri(f"sqlite:///{(tmp_path / 'mlruns' / 'mlflow.db').as_posix()}")
    pipeline = ForecastingPipeline(repo_root / "sql")
    with (
        db.connect(read_only=True) as con,
        pytest.raises(ForecastError, match="No feature snapshots"),
    ):
        pipeline.run(con, features_config, _small_forecast_config(), _costs_config())


def test_forecasting_pipeline_registers_models_when_configured(snapshot_db, repo_root, tmp_path):
    db, features_config, table = snapshot_db
    mlflow.set_tracking_uri(f"sqlite:///{(tmp_path / 'mlruns' / 'mlflow.db').as_posix()}")
    forecast_config = _small_forecast_config(
        register_model=True,
        experiment_name="test-forecast-registered",
        model_name="test-model-registered",
    )
    pipeline = ForecastingPipeline(repo_root / "sql")
    with db.connect(read_only=True) as con:
        pipeline.run(con, features_config, forecast_config, _costs_config(), table)

    registered_names = {rm.name for rm in MlflowClient().search_registered_models()}
    assert any(name.startswith("test-model-registered-q") for name in registered_names)
