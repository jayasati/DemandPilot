"""Unit tests for the config-driven rolling-feature SQL generator (ADR-010)."""

from demandpilot.config.models import FeaturesConfig, LagFeaturesConfig, RollingFeaturesConfig
from demandpilot.features.generator import FeatureSqlGenerator
from demandpilot.sqlrender import SqlRenderer


def _config(**overrides: object) -> FeaturesConfig:
    base: dict[str, object] = {
        "target": "units_sold",
        "date_column": "date",
        "group_columns": ["store_id", "sku_id"],
        "lag_features": LagFeaturesConfig(column="units_sold", lags=[1, 3]),
        "rolling_features": RollingFeaturesConfig(
            column="units_sold", windows=[5], aggregations=["mean", "max"]
        ),
        "calendar_features": [],
        "categorical_features": [],
        "numeric_features": [],
    }
    base.update(overrides)
    return FeaturesConfig(**base)  # type: ignore[arg-type]


def _render(repo_root, config: FeaturesConfig) -> str:
    return FeatureSqlGenerator(SqlRenderer(repo_root / "sql")).render(config)


def test_renders_one_lag_expression_per_configured_lag(repo_root):
    sql = _render(repo_root, _config())
    assert "LAG(units_sold, 1) OVER w AS units_sold_lag_1" in sql
    assert "LAG(units_sold, 3) OVER w AS units_sold_lag_3" in sql


def test_renders_one_expression_per_window_aggregation_pair(repo_root):
    sql = _render(repo_root, _config())
    assert (
        "AVG(units_sold) OVER (w ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING) "
        "AS units_sold_roll_mean_5" in sql
    )
    assert (
        "MAX(units_sold) OVER (w ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING) "
        "AS units_sold_roll_max_5" in sql
    )


def test_never_includes_current_row(repo_root):
    sql = _render(repo_root, _config())
    assert "CURRENT ROW" not in sql.upper()
    assert "BETWEEN 5 PRECEDING AND 1 PRECEDING" in sql


def test_partitions_and_orders_by_group_and_date_columns(repo_root):
    sql = _render(repo_root, _config())
    assert "PARTITION BY store_id, sku_id ORDER BY date" in sql


def test_selects_group_and_date_columns(repo_root):
    sql = _render(repo_root, _config())
    assert "    store_id" in sql
    assert "    sku_id" in sql
    assert "    date" in sql


def test_repo_features_config_renders_without_error(repo_root):
    from demandpilot.config import load_config

    config = load_config(repo_root).features
    sql = _render(repo_root, config)
    for lag in config.lag_features.lags:
        assert f"units_sold_lag_{lag}" in sql
    for window in config.rolling_features.windows:
        for aggregation in config.rolling_features.aggregations:
            assert f"units_sold_roll_{aggregation}_{window}" in sql
