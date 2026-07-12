"""Command-line entry point (``demandpilot <command>``).

Commands:
    init-db        Create all tables and views in the DuckDB database.
    ingest-m5      Load the raw M5 CSVs, then validate the result.
    build-features Generate feature SQL from config and materialize a snapshot.
    validate       Re-run the data validation suite against the database.
"""

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from demandpilot import __version__
from demandpilot.config import DemandPilotConfig, load_config
from demandpilot.data import Database, DataValidator, M5Ingestor, apply_schema
from demandpilot.exceptions import DemandPilotError
from demandpilot.features import FeatureSnapshotBuilder
from demandpilot.logging_setup import setup_logging
from demandpilot.sqlrender import SqlRenderer

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    parser = argparse.ArgumentParser(
        prog="demandpilot",
        description="DemandPilot — retail demand forecasting and inventory optimization.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Project root containing configs/ and sql/ (default: DEMANDPILOT_ROOT or cwd).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Create all tables and views.")

    ingest = subparsers.add_parser("ingest-m5", help="Ingest the raw M5 dataset and validate it.")
    ingest.add_argument(
        "--raw-dir",
        type=Path,
        default=None,
        help="Directory with the M5 CSVs (default: paths.m5_raw_dir from app.yaml).",
    )

    subparsers.add_parser(
        "build-features", help="Generate feature SQL from config and materialize a snapshot."
    )

    subparsers.add_parser("validate", help="Run the data validation suite.")
    return parser


def _run_init_db(config: DemandPilotConfig) -> int:
    """Apply the schema SQL files."""
    db = Database(config.app.paths.duckdb_path)
    apply_schema(db, config.app.paths.sql_dir)
    logger.info("Database initialized at %s", db.path)
    return 0


def _run_ingest_m5(config: DemandPilotConfig, raw_dir: Path | None) -> int:
    """Ingest M5 raw data, then validate."""
    db = Database(config.app.paths.duckdb_path)
    renderer = SqlRenderer(config.app.paths.sql_dir)
    ingestor = M5Ingestor(db, renderer, raw_dir or config.app.paths.m5_raw_dir)
    ingestor.ingest()
    DataValidator(db).run().raise_if_failed()
    return 0


def _run_build_features(config: DemandPilotConfig) -> int:
    """Generate the feature views from config and materialize a new snapshot."""
    db = Database(config.app.paths.duckdb_path)
    builder = FeatureSnapshotBuilder(db, config.app.paths.sql_dir, config.root)
    info = builder.build(config.features)
    logger.info(
        "Feature snapshot %s ready: %d rows [%s .. %s]",
        info.table_name,
        info.row_count,
        info.min_date,
        info.max_date,
    )
    return 0


def _run_validate(config: DemandPilotConfig) -> int:
    """Run validation checks and report the outcome."""
    report = DataValidator(Database(config.app.paths.duckdb_path)).run()
    for check in report.checks:
        logger.info("%-24s %s (%s)", check.name, "PASS" if check.passed else "FAIL", check.detail)
    report.raise_if_failed()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code: 0 on success, 1 on any DemandPilot error.
    """
    args = _build_parser().parse_args(argv)
    try:
        config = load_config(args.root)
        setup_logging(config.app.paths.configs_dir / "logging.yaml", config.root)
        if args.command == "init-db":
            return _run_init_db(config)
        if args.command == "ingest-m5":
            return _run_ingest_m5(config, args.raw_dir)
        if args.command == "build-features":
            return _run_build_features(config)
        return _run_validate(config)
    except DemandPilotError as exc:
        # Logging may not be configured yet if config loading failed.
        logging.getLogger(__name__).error("%s", exc)
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
