"""Naming convention for generated feature columns.

Shared by the feature SQL generator (``demandpilot.features.generator``,
ADR-010) and the forecasting dataset assembler
(``demandpilot.forecasting.dataset``, ADR-014/015), so both agree on column
names without duplicating the naming logic.
"""

from demandpilot.config.models import FeaturesConfig


def lag_column_name(column: str, lag: int) -> str:
    """Column name for a lag feature, e.g. ``units_sold_lag_7``."""
    return f"{column}_lag_{lag}"


def rolling_column_name(column: str, aggregation: str, window: int) -> str:
    """Column name for a rolling-window feature, e.g. ``units_sold_roll_mean_7``."""
    return f"{column}_roll_{aggregation}_{window}"


def history_derived_columns(config: FeaturesConfig) -> list[str]:
    """All lag and rolling-window column names generated for ``config``.

    These are the "history-derived" columns (ADR-014): they only ever use
    information from strictly before the row's own date, so they're valid
    inputs at any forecast horizon once bound to a forecast origin.
    """
    columns = [lag_column_name(config.lag_features.column, lag) for lag in config.lag_features.lags]
    columns += [
        rolling_column_name(config.rolling_features.column, aggregation, window)
        for window in config.rolling_features.windows
        for aggregation in config.rolling_features.aggregations
    ]
    return columns
