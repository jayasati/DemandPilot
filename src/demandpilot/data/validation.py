"""Post-ingestion data validation.

The ``sales`` fact table carries no PK/FK constraints for ingest performance
at M5 scale (~59M rows — see ADR-013), so integrity is enforced here instead.
Every check is a single SQL statement returning one number; a check passes
when that number matches its expectation (zero violations, or a positive
count for non-emptiness).
"""

import logging
from dataclasses import dataclass

import duckdb

from demandpilot.data.db import Database
from demandpilot.exceptions import DatabaseError, DataValidationError

logger = logging.getLogger(__name__)

# (name, sql, mode) — mode "zero": result must be 0; mode "positive": result must be > 0.
_CHECKS: tuple[tuple[str, str, str], ...] = (
    ("stores_non_empty", "SELECT COUNT(*) FROM stores", "positive"),
    ("skus_non_empty", "SELECT COUNT(*) FROM skus", "positive"),
    ("calendar_non_empty", "SELECT COUNT(*) FROM calendar", "positive"),
    ("prices_non_empty", "SELECT COUNT(*) FROM prices", "positive"),
    ("sales_non_empty", "SELECT COUNT(*) FROM sales", "positive"),
    (
        "sales_key_unique",
        """
        SELECT COUNT(*) FROM (
            SELECT store_id, sku_id, date FROM sales
            GROUP BY store_id, sku_id, date HAVING COUNT(*) > 1
        )
        """,
        "zero",
    ),
    (
        "prices_key_unique",
        """
        SELECT COUNT(*) FROM (
            SELECT store_id, sku_id, wm_yr_wk FROM prices
            GROUP BY store_id, sku_id, wm_yr_wk HAVING COUNT(*) > 1
        )
        """,
        "zero",
    ),
    ("no_negative_units", "SELECT COUNT(*) FROM sales WHERE units_sold < 0", "zero"),
    (
        "positive_prices",
        "SELECT COUNT(*) FROM sales WHERE sell_price IS NULL OR sell_price <= 0",
        "zero",
    ),
    (
        "sales_stores_exist",
        "SELECT COUNT(*) FROM sales WHERE store_id NOT IN (SELECT store_id FROM stores)",
        "zero",
    ),
    (
        "sales_skus_exist",
        "SELECT COUNT(*) FROM sales WHERE sku_id NOT IN (SELECT sku_id FROM skus)",
        "zero",
    ),
    (
        "sales_dates_in_calendar",
        "SELECT COUNT(*) FROM sales WHERE date NOT IN (SELECT date FROM calendar)",
        "zero",
    ),
    (
        "calendar_contiguous",
        """
        SELECT DATEDIFF('day', MIN(date), MAX(date)) + 1 - COUNT(*) FROM calendar
        """,
        "zero",
    ),
)


@dataclass(frozen=True)
class ValidationCheck:
    """Outcome of a single validation check."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ValidationReport:
    """Outcome of a full validation run."""

    checks: tuple[ValidationCheck, ...]

    @property
    def passed(self) -> bool:
        """Whether every check passed."""
        return all(check.passed for check in self.checks)

    @property
    def failures(self) -> tuple[ValidationCheck, ...]:
        """The failing checks."""
        return tuple(check for check in self.checks if not check.passed)

    def raise_if_failed(self) -> None:
        """Raise :class:`DataValidationError` if any check failed."""
        if not self.passed:
            summary = "; ".join(f"{c.name}: {c.detail}" for c in self.failures)
            raise DataValidationError(f"Data validation failed ({summary})")


class DataValidator:
    """Runs the integrity check suite against an ingested database."""

    def __init__(self, db: Database) -> None:
        """Create a validator for ``db``."""
        self._db = db

    def run(self) -> ValidationReport:
        """Execute all checks and return the report.

        Returns:
            A report with one entry per check.

        Raises:
            DatabaseError: If a check query itself cannot be executed.
        """
        results: list[ValidationCheck] = []
        with self._db.connect(read_only=True) as connection:
            for name, sql, mode in _CHECKS:
                try:
                    row = connection.execute(sql).fetchone()
                except duckdb.Error as exc:
                    raise DatabaseError(f"Validation check '{name}' failed to run: {exc}") from exc
                value = int(row[0]) if row is not None and row[0] is not None else 0
                if mode == "zero":
                    passed = value == 0
                    detail = "ok" if passed else f"{value} violating rows"
                else:
                    passed = value > 0
                    detail = f"{value} rows" if passed else "table is empty"
                results.append(ValidationCheck(name=name, passed=passed, detail=detail))
                logger.debug("Validation %s: %s (%s)", name, "PASS" if passed else "FAIL", detail)
        report = ValidationReport(checks=tuple(results))
        logger.info(
            "Data validation: %d/%d checks passed",
            sum(c.passed for c in report.checks),
            len(report.checks),
        )
        return report
