"""Tests for the shared feature-column naming helpers."""

from demandpilot.config import load_config
from demandpilot.features.naming import (
    history_derived_columns,
    lag_column_name,
    rolling_column_name,
)


def test_lag_column_name():
    assert lag_column_name("units_sold", 7) == "units_sold_lag_7"


def test_rolling_column_name():
    assert rolling_column_name("units_sold", "mean", 14) == "units_sold_roll_mean_14"


def test_history_derived_columns_covers_every_lag_and_window_aggregation_pair(repo_root):
    config = load_config(repo_root).features
    columns = history_derived_columns(config)
    for lag in config.lag_features.lags:
        assert lag_column_name(config.lag_features.column, lag) in columns
    for window in config.rolling_features.windows:
        for aggregation in config.rolling_features.aggregations:
            assert (
                rolling_column_name(config.rolling_features.column, aggregation, window) in columns
            )
    expected_count = len(config.lag_features.lags) + len(config.rolling_features.windows) * len(
        config.rolling_features.aggregations
    )
    assert len(columns) == expected_count
