"""End-to-end reporting tests: gathering, rendering, graceful-empty sections."""

import mlflow
import pytest

from demandpilot.config import load_config
from demandpilot.config.models import (
    CostsConfig,
    ForecastConfig,
    ForecastMlflowConfig,
    ModelConfig,
    SimulationConfig,
    TrainConfig,
)
from demandpilot.data import Database, M5Ingestor, apply_schema
from demandpilot.features import FeatureSnapshotBuilder
from demandpilot.forecasting import ForecastingPipeline
from demandpilot.optimization import RecommendationBuilder, persist_recommendations
from demandpilot.reporting import ReportBuilder
from demandpilot.simulation import SimulationEngine, persist_simulation_results
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


def _small_forecast_config(*, experiment_name: str = "test-report") -> ForecastConfig:
    return ForecastConfig(
        target_column="units_sold",
        date_column="date",
        id_columns=["store_id", "sku_id"],
        horizon_days=5,
        frequency="D",
        strategy="direct",
        quantiles=[0.1, 0.5, 0.9],
        metrics=["pinball", "coverage", "wape", "bias", "rmse"],
        train=TrainConfig(
            test_size_days=3, validation_size_days=3, cv_folds=1, origin_stride_days=1
        ),
        model=ModelConfig(
            type="lightgbm",
            objective="quantile",
            params=_TEST_MODEL_PARAMS,
            early_stopping_rounds=5,
        ),
        mlflow=ForecastMlflowConfig(
            experiment_name=experiment_name, register_model=False, model_name="test-report-model"
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


def _simulation_config() -> SimulationConfig:
    return SimulationConfig(
        policy="newsvendor",
        service_level=0.9,
        lead_time_days=3,
        review_period_days=1,
        demand_distribution="empirical",
        n_simulations=200,
        random_seed=42,
    )


def test_report_renders_gracefully_before_any_downstream_command(snapshot_db, repo_root, tmp_path):
    db, _features_config, table = snapshot_db
    tracking_uri = f"sqlite:///{(tmp_path / 'mlruns' / 'mlflow.db').as_posix()}"
    builder = ReportBuilder(repo_root / "sql")
    output_path = tmp_path / "reports" / "executive_report.html"
    with db.connect(read_only=True) as con:
        result_path = builder.build(
            con, _small_forecast_config(), _costs_config(), tracking_uri, output_path, table
        )

    assert result_path == output_path
    html = output_path.read_text(encoding="utf-8")
    assert "DemandPilot Executive Report" in html
    assert table in html
    assert "run <code>demandpilot train</code>" in html
    assert "run <code>demandpilot recommend</code>" in html
    assert "run <code>demandpilot simulate</code>" in html


def test_report_includes_all_sections_once_populated(snapshot_db, repo_root, tmp_path):
    db, features_config, table = snapshot_db
    tracking_uri = f"sqlite:///{(tmp_path / 'mlruns' / 'mlflow.db').as_posix()}"
    mlflow.set_tracking_uri(tracking_uri)
    forecast_config = _small_forecast_config()
    costs_config = _costs_config()

    with db.connect(read_only=True) as con:
        ForecastingPipeline(repo_root / "sql").run(
            con, features_config, forecast_config, costs_config, table
        )
    with db.connect() as con:
        rec_report = RecommendationBuilder(repo_root / "sql").build(
            con, features_config, forecast_config, costs_config, 3, table
        )
        persist_recommendations(con, rec_report)
        comparison = SimulationEngine(repo_root / "sql").run(
            con, features_config, forecast_config, costs_config, _simulation_config(), table
        )
        persist_simulation_results(con, comparison)

    builder = ReportBuilder(repo_root / "sql")
    output_path = tmp_path / "reports" / "executive_report.html"
    with db.connect(read_only=True) as con:
        builder.build(con, forecast_config, costs_config, tracking_uri, output_path, table)

    html = output_path.read_text(encoding="utf-8")
    assert "run <code>demandpilot train</code>" not in html
    assert "run <code>demandpilot recommend</code>" not in html
    assert "run <code>demandpilot simulate</code>" not in html
    assert "ml_quantile" in html
    assert "classical_baseline" in html
    # Cost assumptions are always shown, using real numbers from CostsConfig.
    assert f"{costs_config.critical_fractile:.1%}" in html


def test_report_output_directory_is_created(snapshot_db, repo_root, tmp_path):
    db, _features_config, table = snapshot_db
    tracking_uri = f"sqlite:///{(tmp_path / 'mlruns' / 'mlflow.db').as_posix()}"
    builder = ReportBuilder(repo_root / "sql")
    nested_output = tmp_path / "deep" / "nested" / "report.html"
    with db.connect(read_only=True) as con:
        builder.build(
            con, _small_forecast_config(), _costs_config(), tracking_uri, nested_output, table
        )
    assert nested_output.is_file()


def test_report_defaults_to_latest_snapshot(snapshot_db, repo_root, tmp_path):
    db, features_config, _first_table = snapshot_db
    second = FeatureSnapshotBuilder(db, repo_root / "sql", repo_root).build(features_config)
    tracking_uri = f"sqlite:///{(tmp_path / 'mlruns' / 'mlflow.db').as_posix()}"
    builder = ReportBuilder(repo_root / "sql")
    output_path = tmp_path / "report.html"
    with db.connect(read_only=True) as con:
        builder.build(con, _small_forecast_config(), _costs_config(), tracking_uri, output_path)
    html = output_path.read_text(encoding="utf-8")
    assert second.table_name in html
