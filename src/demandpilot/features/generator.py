"""Generates the leakage-safe ``rolling_features`` view SQL from configuration.

This is the single source of truth promised by ADR-010: lag and rolling-window
expressions come from ``configs/features.yaml`` (already validated — lags and
windows are Pydantic-checked to be >= 1), never hand-duplicated in SQL. The
1-PRECEDING upper bound on every window is hardcoded in the template
regardless of config, structurally enforcing the ADR-008 leakage rule.
"""

from demandpilot.config.models import FeaturesConfig
from demandpilot.sqlrender import SqlRenderer

_AGGREGATION_SQL: dict[str, str] = {
    "mean": "AVG",
    "std": "STDDEV",
    "min": "MIN",
    "max": "MAX",
    "sum": "SUM",
}

_TEMPLATE_NAME = "rolling_features.sql.j2"


class FeatureSqlGenerator:
    """Renders the ``rolling_features`` view SQL from a validated config."""

    def __init__(self, renderer: SqlRenderer) -> None:
        """Create a generator.

        Args:
            renderer: SQL template renderer over the project ``sql/`` directory.
        """
        self._renderer = renderer

    def render(self, config: FeaturesConfig) -> str:
        """Render the ``CREATE OR REPLACE VIEW rolling_features`` statement.

        Args:
            config: Validated feature engineering configuration.

        Returns:
            The rendered SQL text.

        Raises:
            SqlRenderError: If the underlying template is missing or fails to render.
        """
        select_columns = [f"    {col}" for col in (*config.group_columns, config.date_column)]

        lag_column = config.lag_features.column
        for lag in config.lag_features.lags:
            select_columns.append(f"    LAG({lag_column}, {lag}) OVER w AS {lag_column}_lag_{lag}")

        roll_column = config.rolling_features.column
        for window in config.rolling_features.windows:
            for aggregation in config.rolling_features.aggregations:
                agg_sql = _AGGREGATION_SQL[aggregation]
                alias = f"{roll_column}_roll_{aggregation}_{window}"
                select_columns.append(
                    f"    {agg_sql}({roll_column}) "
                    f"OVER (w ROWS BETWEEN {window} PRECEDING AND 1 PRECEDING) AS {alias}"
                )

        return self._renderer.render(
            _TEMPLATE_NAME,
            select_columns_sql=",\n".join(select_columns),
            group_columns_sql=", ".join(config.group_columns),
            date_column=config.date_column,
        )
