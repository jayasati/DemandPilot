"""End-to-end recommendation tests: build, cost rationale, persistence."""

import pytest

from demandpilot.config import load_config
from demandpilot.config.models import (
    CostsConfig,
    ForecastConfig,
    ForecastMlflowConfig,
    ModelConfig,
    TrainConfig,
)
from demandpilot.data import Database, M5Ingestor, apply_schema
from demandpilot.exceptions import OptimizationError
from demandpilot.features import FeatureSnapshotBuilder
from demandpilot.optimization import (
    RECOMMENDATIONS_TABLE,
    RecommendationBuilder,
    persist_recommendations,
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


def _small_forecast_config(*, validation_size_days: int = 3) -> ForecastConfig:
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
            test_size_days=3,
            validation_size_days=validation_size_days,
            cv_folds=1,
            origin_stride_days=1,
        ),
        model=ModelConfig(
            type="lightgbm",
            objective="quantile",
            params=_TEST_MODEL_PARAMS,
            early_stopping_rounds=5,
        ),
        mlflow=ForecastMlflowConfig(
            experiment_name="test-recommend",
            register_model=False,
            model_name="test-recommend-model",
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


def test_build_produces_one_recommendation_per_series(snapshot_db, repo_root):
    db, features_config, table = snapshot_db
    builder = RecommendationBuilder(repo_root / "sql")
    with db.connect(read_only=True) as con:
        report = builder.build(
            con, features_config, _small_forecast_config(), _costs_config(), 3, table
        )

    assert report.snapshot_table == table
    assert report.lead_time_days == 3
    assert len(report.recommendations) > 0
    # All recommendations share the same "as of" origin date.
    assert {r.origin_date for r in report.recommendations} == {report.recommendation_date}
    for r in report.recommendations:
        assert (r.target_date - r.origin_date).days == 3


def test_cost_rationale_is_consistent_with_config(snapshot_db, repo_root):
    db, features_config, table = snapshot_db
    costs = _costs_config()
    builder = RecommendationBuilder(repo_root / "sql")
    with db.connect(read_only=True) as con:
        report = builder.build(con, features_config, _small_forecast_config(), costs, 3, table)

    for r in report.recommendations:
        assert r.critical_fractile == pytest.approx(costs.critical_fractile)
        assert r.understock_cost_ratio == pytest.approx(costs.understock_cost_ratio)
        assert r.overstock_cost_ratio == pytest.approx(costs.overstock_cost_ratio)
        assert r.safety_stock == pytest.approx(r.order_quantity - r.median_forecast)


def test_actual_demand_matches_sales(snapshot_db, repo_root):
    db, features_config, table = snapshot_db
    builder = RecommendationBuilder(repo_root / "sql")
    with db.connect(read_only=True) as con:
        report = builder.build(
            con, features_config, _small_forecast_config(), _costs_config(), 3, table
        )
        for r in report.recommendations:
            expected = con.execute(
                "SELECT units_sold FROM sales WHERE store_id = ? AND sku_id = ? AND date = ?",
                [r.store_id, r.sku_id, r.target_date],
            ).fetchone()[0]
            assert r.actual_demand == pytest.approx(expected)


def test_defaults_to_latest_snapshot(snapshot_db, repo_root):
    db, features_config, _first_table = snapshot_db
    second = FeatureSnapshotBuilder(db, repo_root / "sql", repo_root).build(features_config)
    builder = RecommendationBuilder(repo_root / "sql")
    with db.connect(read_only=True) as con:
        report = builder.build(con, features_config, _small_forecast_config(), _costs_config(), 3)
    assert report.snapshot_table == second.table_name


def test_lead_time_beyond_data_range_raises(snapshot_db, repo_root):
    db, features_config, table = snapshot_db
    builder = RecommendationBuilder(repo_root / "sql")
    with (
        db.connect(read_only=True) as con,
        pytest.raises(OptimizationError, match="No rows available"),
    ):
        builder.build(con, features_config, _small_forecast_config(), _costs_config(), 1000, table)


def test_persist_recommendations_writes_matching_table(snapshot_db, repo_root):
    db, features_config, table = snapshot_db
    builder = RecommendationBuilder(repo_root / "sql")
    with db.connect() as con:
        report = builder.build(
            con, features_config, _small_forecast_config(), _costs_config(), 3, table
        )
        persist_recommendations(con, report)
        count = con.execute(f"SELECT COUNT(*) FROM {RECOMMENDATIONS_TABLE}").fetchone()[0]
        snapshot_col = con.execute(
            f"SELECT DISTINCT snapshot_table FROM {RECOMMENDATIONS_TABLE}"
        ).fetchall()
    assert count == len(report.recommendations)
    assert snapshot_col == [(table,)]


def test_persist_recommendations_replaces_previous_run(snapshot_db, repo_root):
    db, features_config, table = snapshot_db
    builder = RecommendationBuilder(repo_root / "sql")
    with db.connect() as con:
        first = builder.build(
            con, features_config, _small_forecast_config(), _costs_config(), 3, table
        )
        persist_recommendations(con, first)
        second = builder.build(
            con,
            features_config,
            _small_forecast_config(validation_size_days=4),
            _costs_config(),
            3,
            table,
        )
        persist_recommendations(con, second)
        count = con.execute(f"SELECT COUNT(*) FROM {RECOMMENDATIONS_TABLE}").fetchone()[0]
    assert count == len(second.recommendations)
