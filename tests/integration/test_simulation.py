"""End-to-end simulation tests: policy replay, cost breakdown, persistence."""

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
from demandpilot.exceptions import SimulationError
from demandpilot.features import FeatureSnapshotBuilder
from demandpilot.simulation import (
    SIMULATION_RESULTS_TABLE,
    SimulationEngine,
    persist_simulation_results,
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


def _small_forecast_config() -> ForecastConfig:
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
            experiment_name="test-simulate", register_model=False, model_name="test-simulate-model"
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


def _simulation_config(**overrides: object) -> SimulationConfig:
    base: dict[str, object] = {
        "policy": "newsvendor",
        "service_level": 0.9,
        "lead_time_days": 3,
        "review_period_days": 1,
        "demand_distribution": "empirical",
        "n_simulations": 200,
        "random_seed": 42,
    }
    base.update(overrides)
    return SimulationConfig(**base)  # type: ignore[arg-type]


@pytest.mark.parametrize("distribution", ["empirical", "normal", "poisson"])
def test_run_produces_paired_decisions_for_every_distribution(snapshot_db, repo_root, distribution):
    db, features_config, table = snapshot_db
    engine = SimulationEngine(repo_root / "sql")
    with db.connect(read_only=True) as con:
        comparison = engine.run(
            con,
            features_config,
            _small_forecast_config(),
            _costs_config(),
            _simulation_config(demand_distribution=distribution),
            table,
        )
    assert comparison.ml_metrics.n_decisions > 0
    assert comparison.ml_metrics.n_decisions == comparison.baseline_metrics.n_decisions
    # Every decision is paired: same count of ml_quantile and classical_baseline rows.
    policies = [d.policy for d in comparison.decisions]
    assert policies.count("ml_quantile") == policies.count("classical_baseline")


def test_cost_breakdown_sums_to_total(snapshot_db, repo_root):
    db, features_config, table = snapshot_db
    engine = SimulationEngine(repo_root / "sql")
    with db.connect(read_only=True) as con:
        comparison = engine.run(
            con,
            features_config,
            _small_forecast_config(),
            _costs_config(),
            _simulation_config(),
            table,
        )
    for metrics in (comparison.ml_metrics, comparison.baseline_metrics):
        assert metrics.total_understock_cost + metrics.total_overstock_cost == pytest.approx(
            metrics.total_cost
        )
    for d in comparison.decisions:
        assert d.understock_cost + d.overstock_cost == pytest.approx(d.cost)
        # Exactly one of the two components is nonzero (can't simultaneously over- and understock).
        assert d.understock_cost == pytest.approx(0.0) or d.overstock_cost == pytest.approx(0.0)


def test_savings_equals_baseline_minus_ml_cost(snapshot_db, repo_root):
    db, features_config, table = snapshot_db
    engine = SimulationEngine(repo_root / "sql")
    with db.connect(read_only=True) as con:
        comparison = engine.run(
            con,
            features_config,
            _small_forecast_config(),
            _costs_config(),
            _simulation_config(),
            table,
        )
    assert comparison.savings == pytest.approx(
        comparison.baseline_metrics.total_cost - comparison.ml_metrics.total_cost
    )


def test_review_period_reduces_decision_count(snapshot_db, repo_root):
    db, features_config, table = snapshot_db
    engine = SimulationEngine(repo_root / "sql")
    with db.connect(read_only=True) as con:
        daily = engine.run(
            con,
            features_config,
            _small_forecast_config(),
            _costs_config(),
            _simulation_config(review_period_days=1),
            table,
        )
        sparse = engine.run(
            con,
            features_config,
            _small_forecast_config(),
            _costs_config(),
            _simulation_config(review_period_days=2),
            table,
        )
    assert sparse.ml_metrics.n_decisions <= daily.ml_metrics.n_decisions


def test_lead_time_beyond_data_range_raises(snapshot_db, repo_root):
    db, features_config, table = snapshot_db
    engine = SimulationEngine(repo_root / "sql")
    with (
        db.connect(read_only=True) as con,
        pytest.raises(SimulationError, match="No rows available"),
    ):
        engine.run(
            con,
            features_config,
            _small_forecast_config(),
            _costs_config(),
            _simulation_config(lead_time_days=1000),
            table,
        )


def test_review_period_larger_than_test_window_raises(snapshot_db, repo_root):
    """A review_period_days coarser than the whole test window leaves nothing
    aligned to the epoch cadence — must fail clearly, not return an empty result."""
    db, features_config, table = snapshot_db
    engine = SimulationEngine(repo_root / "sql")
    with (
        db.connect(read_only=True) as con,
        pytest.raises(SimulationError, match="No test rows survive"),
    ):
        engine.run(
            con,
            features_config,
            _small_forecast_config(),
            _costs_config(),
            _simulation_config(review_period_days=10_000),
            table,
        )


def test_persist_writes_matching_table(snapshot_db, repo_root):
    db, features_config, table = snapshot_db
    engine = SimulationEngine(repo_root / "sql")
    with db.connect() as con:
        comparison = engine.run(
            con,
            features_config,
            _small_forecast_config(),
            _costs_config(),
            _simulation_config(),
            table,
        )
        persist_simulation_results(con, comparison)
        count = con.execute(f"SELECT COUNT(*) FROM {SIMULATION_RESULTS_TABLE}").fetchone()[0]
    assert count == len(comparison.decisions)
