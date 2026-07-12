"""Structured exception hierarchy for DemandPilot.

Every error raised by this package derives from :class:`DemandPilotError`, so
callers can catch one type at the boundary (CLI, dashboard) and rely on layered
subclasses for anything finer. Infrastructure exceptions (``duckdb.Error``,
``yaml.YAMLError``, ...) must never leak past the layer that produced them —
wrap them with ``raise ... from exc``. See docs/EXCEPTION_STRATEGY.md.
"""


class DemandPilotError(Exception):
    """Base class for all DemandPilot errors."""


class ConfigError(DemandPilotError):
    """Configuration is missing, unparsable, or fails validation."""


class DatabaseError(DemandPilotError):
    """A DuckDB operation failed."""


class SqlRenderError(DemandPilotError):
    """A SQL template could not be found or rendered."""


class DataError(DemandPilotError):
    """Base class for errors in the data layer."""


class IngestionError(DataError):
    """Raw data could not be ingested (missing files, malformed input)."""


class DataValidationError(DataError):
    """Ingested data failed one or more validation checks."""
