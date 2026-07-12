"""Database schema management.

The schema is defined by the ordered list of static SQL files below; applying
them is idempotent (all DDL uses ``IF NOT EXISTS`` / ``CREATE OR REPLACE``).

``rolling_features`` and ``feature_store`` are NOT part of this static schema:
they are config-driven (ADR-010) and DuckDB binds views eagerly (a view
referencing a not-yet-existing view fails at CREATE time), so they must be
created together, after config is available. See
``demandpilot.features.FeatureSnapshotBuilder`` / the ``build-features`` CLI
command.
"""

import logging
from pathlib import Path

from demandpilot.data.db import Database
from demandpilot.exceptions import DatabaseError

logger = logging.getLogger(__name__)

# Order matters: views depend on the base tables.
SCHEMA_FILES: tuple[str, ...] = (
    "create_tables.sql",
    "feature_snapshots.sql",
    "views.sql",
)


def apply_schema(db: Database, sql_dir: Path) -> None:
    """Create all tables and views defined by the schema SQL files.

    Args:
        db: Target database.
        sql_dir: Directory containing the schema SQL files.

    Raises:
        DatabaseError: If a schema file is missing or fails to execute.
    """
    for filename in SCHEMA_FILES:
        path = sql_dir / filename
        try:
            sql = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise DatabaseError(f"Schema file not found: {path}") from exc
        db.execute_script(sql, description=filename)
    logger.info("Schema applied from %s (%d files)", sql_dir, len(SCHEMA_FILES))
