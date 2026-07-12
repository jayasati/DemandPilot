"""Database schema management.

The schema is defined by the ordered list of static SQL files below; applying
them is idempotent (all DDL uses ``IF NOT EXISTS`` / ``CREATE OR REPLACE``).
"""

import logging
from pathlib import Path

from demandpilot.data.db import Database
from demandpilot.exceptions import DatabaseError

logger = logging.getLogger(__name__)

# Order matters: views depend on the base tables.
SCHEMA_FILES: tuple[str, ...] = (
    "create_tables.sql",
    "rolling_features.sql",
    "feature_store.sql",
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
