"""Data layer: DuckDB access, schema management, ingestion, and validation."""

from demandpilot.data.db import Database
from demandpilot.data.m5 import IngestionSummary, M5Ingestor
from demandpilot.data.schema import apply_schema
from demandpilot.data.validation import DataValidator, ValidationCheck, ValidationReport

__all__ = [
    "DataValidator",
    "Database",
    "IngestionSummary",
    "M5Ingestor",
    "ValidationCheck",
    "ValidationReport",
    "apply_schema",
]
