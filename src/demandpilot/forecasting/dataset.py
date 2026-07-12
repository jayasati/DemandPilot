"""Assembles direct multi-horizon training datasets from a feature snapshot.

See ADR-008 (target-shift formulation) and ADR-014 (future-known vs.
history-derived feature split): history-derived columns (lags/rolling stats)
come from the ORIGIN row — information available at forecast time; calendar,
price, and dimension columns come from the TARGET row — known in advance for
that future date. This lets one row carry e.g. "the target day is a Saturday"
even though the origin day is not.
"""

import duckdb
import polars as pl

from demandpilot.config.models import FeaturesConfig
from demandpilot.features.naming import history_derived_columns
from demandpilot.sqlrender import SqlRenderer

_TEMPLATE_NAME = "assemble_horizon_dataset.sql.j2"


class HorizonDatasetAssembler:
    """Renders and executes the self-join that assembles one horizon's dataset."""

    def __init__(self, renderer: SqlRenderer) -> None:
        """Create an assembler.

        Args:
            renderer: SQL template renderer over the project ``sql/`` directory.
        """
        self._renderer = renderer

    def render(
        self,
        config: FeaturesConfig,
        snapshot_table: str,
        horizon: int,
        origin_stride_days: int,
    ) -> str:
        """Render the self-join SQL for one horizon.

        Args:
            config: Validated feature engineering configuration.
            snapshot_table: Name of the materialized ``feature_store_v{N}`` table.
            horizon: Number of days ahead of the origin the target falls on.
            origin_stride_days: Subsample origins to 1-in-N calendar days.

        Returns:
            The rendered SQL text.

        Raises:
            SqlRenderError: If the underlying template is missing or fails to render.
        """
        group_columns = config.group_columns
        history_columns = history_derived_columns(config)
        future_columns = [*config.calendar_features, *config.numeric_features]
        extra_categorical = [col for col in config.categorical_features if col not in group_columns]

        select_parts = [f"    orig.{col}" for col in group_columns]
        select_parts.append(f"    orig.{config.date_column} AS origin_date")
        select_parts.append(f"    tgt.{config.date_column} AS target_date")
        select_parts.append(f"    {horizon} AS horizon")
        select_parts += [f"    orig.{col}" for col in history_columns]
        select_parts += [f"    tgt.{col}" for col in (*future_columns, *extra_categorical)]
        select_parts.append(f"    tgt.{config.target} AS target")

        join_condition = " AND ".join(f"orig.{col} = tgt.{col}" for col in group_columns)

        return self._renderer.render(
            _TEMPLATE_NAME,
            select_columns_sql=",\n".join(select_parts),
            snapshot_table=snapshot_table,
            join_condition_sql=join_condition,
            date_column=config.date_column,
            horizon=horizon,
            origin_stride_days=origin_stride_days,
        )

    def assemble(
        self,
        connection: duckdb.DuckDBPyConnection,
        config: FeaturesConfig,
        snapshot_table: str,
        horizon: int,
        origin_stride_days: int,
    ) -> pl.DataFrame:
        """Render and execute the self-join, returning a Polars DataFrame.

        Raises:
            SqlRenderError: If the template fails to render.
            DatabaseError: If the query fails to execute.
        """
        sql = self.render(config, snapshot_table, horizon, origin_stride_days)
        return connection.execute(sql).pl()


def assemble_multi_horizon(
    connection: duckdb.DuckDBPyConnection,
    assembler: HorizonDatasetAssembler,
    config: FeaturesConfig,
    snapshot_table: str,
    horizon_days: int,
    origin_stride_days: int,
) -> pl.DataFrame:
    """Stack single-horizon datasets for horizons ``1..horizon_days``.

    ``horizon`` becomes a plain numeric feature, so one quantile model
    generalizes across every horizon (ADR-015) instead of training
    ``horizon_days`` separate models.

    Args:
        connection: Open DuckDB connection.
        assembler: The horizon dataset assembler.
        config: Validated feature engineering configuration.
        snapshot_table: Name of the materialized feature snapshot table.
        horizon_days: Maximum forecast horizon, in days.
        origin_stride_days: Subsample origins to 1-in-N calendar days.

    Returns:
        The concatenated dataset across all horizons.
    """
    frames = [
        assembler.assemble(connection, config, snapshot_table, horizon, origin_stride_days)
        for horizon in range(1, horizon_days + 1)
    ]
    return pl.concat(frames, how="vertical")
