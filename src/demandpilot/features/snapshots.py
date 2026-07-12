"""Materializes versioned feature-store snapshots with a lineage manifest.

See ADR-011. ``feature_store`` is a view (always current, never versioned);
``build()`` here creates the leakage-safe feature views from config and then
freezes their output into ``feature_store_v{N}``, recording enough lineage
(git commit, config hash, row count, date range) that a model's training data
can always be traced back to the exact code and configuration that produced it.
"""

import hashlib
import logging
import subprocess
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import duckdb

from demandpilot.config.models import FeaturesConfig
from demandpilot.data.db import Database
from demandpilot.exceptions import FeatureError
from demandpilot.features.generator import FeatureSqlGenerator
from demandpilot.sqlrender import SqlRenderer

logger = logging.getLogger(__name__)

_FEATURE_STORE_SQL_FILE = "feature_store.sql"
_SNAPSHOT_TABLE_PREFIX = "feature_store_v"


@dataclass(frozen=True)
class SnapshotInfo:
    """One row of the ``feature_snapshots`` manifest."""

    version: int
    table_name: str
    created_at: datetime
    git_commit: str | None
    config_hash: str
    row_count: int
    min_date: date | None
    max_date: date | None


def latest_snapshot_table(connection: duckdb.DuckDBPyConnection) -> str:
    """Return the most recently built snapshot table name.

    Shared by the forecasting and optimization layers so both resolve "the
    current snapshot" the same way.

    Raises:
        FeatureError: If no snapshot has ever been built.
    """
    row = connection.execute(
        "SELECT table_name FROM feature_snapshots ORDER BY version DESC LIMIT 1"
    ).fetchone()
    if row is None:
        raise FeatureError("No feature snapshots found — run `demandpilot build-features` first.")
    return str(row[0])


class FeatureSnapshotBuilder:
    """Builds the feature views from config, then materializes a snapshot."""

    def __init__(self, db: Database, sql_dir: Path, root: Path) -> None:
        """Create a builder.

        Args:
            db: Target database (base schema must already be applied).
            sql_dir: Directory containing SQL files and templates.
            root: Project root, used to resolve the current git commit.
        """
        self._db = db
        self._sql_dir = sql_dir
        self._root = root
        self._generator = FeatureSqlGenerator(SqlRenderer(sql_dir))

    def build(self, features_config: FeaturesConfig) -> SnapshotInfo:
        """Generate the feature views and materialize the next snapshot.

        Args:
            features_config: Validated feature engineering configuration.

        Returns:
            Lineage information for the newly created snapshot.

        Raises:
            SqlRenderError: If the rolling-feature SQL fails to render.
            DatabaseError: If creating the feature views fails.
            FeatureError: If materializing the snapshot table fails.
        """
        rolling_sql = self._generator.render(features_config)
        self._db.execute_script(rolling_sql, description="generated rolling_features view")

        feature_store_sql = (self._sql_dir / _FEATURE_STORE_SQL_FILE).read_text(encoding="utf-8")
        self._db.execute_script(feature_store_sql, description=_FEATURE_STORE_SQL_FILE)

        config_hash = _hash_config(features_config)
        git_commit = _current_git_commit(self._root)
        created_at = datetime.now(UTC)

        with self._db.connect() as connection:
            version_row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM feature_snapshots"
            ).fetchone()
            if version_row is None:  # pragma: no cover - aggregate SELECT always returns a row
                raise FeatureError("Next snapshot version query returned no rows")
            version = int(version_row[0])

            table_name = f"{_SNAPSHOT_TABLE_PREFIX}{version}"
            try:
                connection.execute(f"CREATE TABLE {table_name} AS SELECT * FROM feature_store")
            except duckdb.Error as exc:
                raise FeatureError(f"Failed to materialize snapshot {table_name}: {exc}") from exc

            stats_row = connection.execute(
                f"SELECT COUNT(*), MIN(date), MAX(date) FROM {table_name}"
            ).fetchone()
            if stats_row is None:  # pragma: no cover - aggregate SELECT always returns a row
                raise FeatureError(f"Snapshot statistics query for {table_name} returned no rows")
            row_count, min_date, max_date = stats_row
            connection.execute(
                """
                INSERT INTO feature_snapshots
                    (version, table_name, created_at, git_commit, config_hash,
                     row_count, min_date, max_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    version,
                    table_name,
                    created_at,
                    git_commit,
                    config_hash,
                    row_count,
                    min_date,
                    max_date,
                ],
            )

        info = SnapshotInfo(
            version=version,
            table_name=table_name,
            created_at=created_at,
            git_commit=git_commit,
            config_hash=config_hash,
            row_count=row_count,
            min_date=min_date,
            max_date=max_date,
        )
        logger.info(
            "Built feature snapshot %s: %d rows [%s .. %s], config_hash=%s, git_commit=%s",
            table_name,
            row_count,
            min_date,
            max_date,
            config_hash,
            git_commit,
        )
        return info


def _hash_config(config: FeaturesConfig) -> str:
    """Stable short hash of a feature config, for manifest lineage."""
    payload = config.model_dump_json().encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _current_git_commit(root: Path) -> str | None:
    """Return the current git commit SHA at ``root``, or None if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None
