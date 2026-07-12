"""Ingestion of the M5 (Walmart) dataset into the DemandPilot schema.

Source: https://www.kaggle.com/competitions/m5-forecasting-accuracy (download
with ``scripts/download_m5.py``). The wide daily sales matrix is unpivoted to
one row per (store, sku, date); weekly ``sell_prices`` are joined via the
Walmart week key. Rows before a SKU's first priced week are dropped — the M5
convention is that the item was not yet on sale (ADR-013).
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from demandpilot.data.db import Database
from demandpilot.exceptions import IngestionError
from demandpilot.sqlrender import SqlRenderer

logger = logging.getLogger(__name__)

REQUIRED_FILES: tuple[str, ...] = (
    "calendar.csv",
    "sell_prices.csv",
    "sales_train_evaluation.csv",
)

_INGEST_TEMPLATE = "ingest_m5.sql.j2"
_STATS_TABLE = "_ingest_stats"


@dataclass(frozen=True)
class IngestionSummary:
    """Row counts produced by one ingestion run."""

    stores: int
    skus: int
    calendar_days: int
    sales_rows: int
    dropped_pre_launch_rows: int


class M5Ingestor:
    """Loads the raw M5 CSV files into the DemandPilot star schema."""

    def __init__(self, db: Database, renderer: SqlRenderer, raw_dir: Path) -> None:
        """Create an ingestor.

        Args:
            db: Target database (schema must already be applied).
            renderer: SQL template renderer over the project ``sql/`` directory.
            raw_dir: Directory containing the raw M5 CSV files.
        """
        self._db = db
        self._renderer = renderer
        self._raw_dir = raw_dir

    def ingest(self) -> IngestionSummary:
        """Run the full ingestion and return row-count statistics.

        Re-running replaces previously ingested data (idempotent).

        Returns:
            Summary of ingested row counts.

        Raises:
            IngestionError: If required raw files are missing.
            DatabaseError: If the ingestion SQL fails.
        """
        self._check_raw_files()
        sql = self._renderer.render(_INGEST_TEMPLATE, raw_dir=self._raw_dir.as_posix())
        logger.info("Ingesting M5 data from %s", self._raw_dir)
        self._db.execute_script(sql, description="M5 ingestion")
        summary = self._read_summary()
        logger.info(
            "Ingested M5: %d stores, %d skus, %d calendar days, %d sales rows "
            "(%d pre-launch rows dropped)",
            summary.stores,
            summary.skus,
            summary.calendar_days,
            summary.sales_rows,
            summary.dropped_pre_launch_rows,
        )
        return summary

    def _check_raw_files(self) -> None:
        """Raise IngestionError listing any missing raw files."""
        missing = [name for name in REQUIRED_FILES if not (self._raw_dir / name).is_file()]
        if missing:
            raise IngestionError(
                f"Missing M5 raw files in {self._raw_dir}: {', '.join(missing)}. "
                "Download them with scripts/download_m5.py (requires Kaggle credentials)."
            )

    def _read_summary(self) -> IngestionSummary:
        """Read and drop the statistics table left behind by the ingestion SQL."""
        with self._db.connect() as connection:
            row = connection.execute(f"""
                SELECT
                    (SELECT COUNT(*) FROM stores),
                    (SELECT COUNT(*) FROM skus),
                    (SELECT COUNT(*) FROM calendar),
                    (SELECT COUNT(*) FROM sales),
                    (SELECT unpivoted_rows - kept_rows FROM {_STATS_TABLE})
                """).fetchone()
            connection.execute(f"DROP TABLE IF EXISTS {_STATS_TABLE}")
        if row is None:  # pragma: no cover - COUNT queries always return a row
            raise IngestionError("Ingestion statistics query returned no rows")
        return IngestionSummary(
            stores=row[0],
            skus=row[1],
            calendar_days=row[2],
            sales_rows=row[3],
            dropped_pre_launch_rows=row[4],
        )
