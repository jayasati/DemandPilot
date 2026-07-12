"""Thin wrapper around a DuckDB database file.

Connection policy (see ADR-001): pipelines are the sole writer; interactive
consumers (dashboard) must connect with ``read_only=True``. Tests should use a
file under ``tmp_path`` rather than ``:memory:``, because every ``connect()``
call on an in-memory path opens a fresh, empty database.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb

from demandpilot.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class Database:
    """Handle to a DuckDB database file."""

    def __init__(self, path: Path) -> None:
        """Create a handle for the database at ``path`` (not opened yet).

        Args:
            path: Location of the DuckDB file; parent directories are created
                on first connect.
        """
        self._path = path

    @property
    def path(self) -> Path:
        """Location of the DuckDB file."""
        return self._path

    @contextmanager
    def connect(self, *, read_only: bool = False) -> Iterator[duckdb.DuckDBPyConnection]:
        """Open a connection, yielding it and closing it on exit.

        Args:
            read_only: Open the database in read-only mode (required for
                consumers that run concurrently with the writing pipeline).

        Yields:
            An open DuckDB connection.

        Raises:
            DatabaseError: If the database cannot be opened.
        """
        if not read_only:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            connection = duckdb.connect(str(self._path), read_only=read_only)
        except duckdb.Error as exc:
            raise DatabaseError(f"Cannot open DuckDB database at {self._path}: {exc}") from exc
        try:
            yield connection
        finally:
            connection.close()

    def execute_script(self, sql: str, *, description: str = "SQL script") -> None:
        """Execute a multi-statement SQL script in a single connection.

        Args:
            sql: SQL text; may contain multiple ``;``-separated statements.
            description: Human-readable label used in logs and errors.

        Raises:
            DatabaseError: If execution fails.
        """
        with self.connect() as connection:
            try:
                connection.execute(sql)
            except duckdb.Error as exc:
                raise DatabaseError(f"Failed executing {description}: {exc}") from exc
        logger.info("Executed %s against %s", description, self._path)
