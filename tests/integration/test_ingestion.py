"""End-to-end ingestion tests against a real DuckDB file."""

from datetime import date, timedelta

import pytest

from demandpilot.data import Database, DataValidator, M5Ingestor, apply_schema
from demandpilot.exceptions import DataValidationError, IngestionError
from demandpilot.sqlrender import SqlRenderer
from tests.conftest import (
    EVENT_DAY_INDEX,
    ITEMS,
    LATE_LAUNCH_DROPPED_DAYS,
    N_DAYS,
    START_DATE,
    STORES,
    units_for,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def ingested_db(tmp_path, repo_root, m5_fixture_dir):
    db = Database(tmp_path / "test.duckdb")
    apply_schema(db, repo_root / "sql")
    renderer = SqlRenderer(repo_root / "sql")
    summary = M5Ingestor(db, renderer, m5_fixture_dir).ingest()
    return db, summary


def test_summary_counts(ingested_db):
    _, summary = ingested_db
    assert summary.stores == len(STORES)
    assert summary.skus == len(ITEMS)
    assert summary.calendar_days == N_DAYS
    assert summary.dropped_pre_launch_rows == LATE_LAUNCH_DROPPED_DAYS
    assert summary.sales_rows == len(STORES) * len(ITEMS) * N_DAYS - LATE_LAUNCH_DROPPED_DAYS


def test_validation_passes(ingested_db):
    db, _ = ingested_db
    report = DataValidator(db).run()
    assert report.passed, [c.name for c in report.failures]


def test_units_match_source_matrix(ingested_db):
    db, _ = ingested_db
    day_idx = 33
    day = START_DATE + timedelta(days=day_idx)
    with db.connect(read_only=True) as con:
        value = con.execute(
            "SELECT units_sold FROM sales WHERE store_id = ? AND sku_id = ? AND date = ?",
            ["TX_1", "HOBBIES_1_002", day],
        ).fetchone()[0]
    assert value == units_for(item_idx=1, store_idx=1, day_idx=day_idx)


def test_holiday_flag_derived_from_event_type(ingested_db):
    db, _ = ingested_db
    event_day = START_DATE + timedelta(days=EVENT_DAY_INDEX)
    with db.connect(read_only=True) as con:
        is_holiday, is_event = con.execute(
            "SELECT is_holiday, is_event FROM calendar WHERE date = ?", [event_day]
        ).fetchone()
        holiday_count = con.execute("SELECT COUNT(*) FROM calendar WHERE is_holiday").fetchone()[0]
    assert is_holiday and is_event
    assert holiday_count == 1


def test_pre_launch_rows_dropped(ingested_db):
    db, _ = ingested_db
    launch = START_DATE + timedelta(days=14)  # third week: first priced week
    with db.connect(read_only=True) as con:
        before, after = con.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE date < ?),
                COUNT(*) FILTER (WHERE date >= ?)
            FROM sales WHERE store_id = 'TX_1' AND sku_id = 'FOODS_3_001'
            """,
            [launch, launch],
        ).fetchone()
    assert before == 0
    assert after == N_DAYS - LATE_LAUNCH_DROPPED_DAYS


def test_reingest_is_idempotent(ingested_db, repo_root, m5_fixture_dir):
    db, first = ingested_db
    second = M5Ingestor(db, SqlRenderer(repo_root / "sql"), m5_fixture_dir).ingest()
    assert second == first


def test_feature_store_has_no_current_day_leakage(ingested_db):
    """The 7-day rolling mean must not include the current row's target."""
    db, _ = ingested_db
    with db.connect(read_only=True) as con:
        rows = con.execute("""
            SELECT date, units_sold, units_sold_roll_mean_7
            FROM feature_store
            WHERE store_id = 'CA_1' AND sku_id = 'HOBBIES_1_001'
            ORDER BY date
            LIMIT 10
            """).fetchall()
    # First row has no history at all: every window ends before it.
    assert rows[0][2] is None
    # Second row's "rolling mean" is exactly the first row's value — not its own.
    assert rows[1][2] == pytest.approx(rows[0][1])


def test_missing_raw_files_raise(tmp_path, repo_root):
    db = Database(tmp_path / "test.duckdb")
    apply_schema(db, repo_root / "sql")
    with pytest.raises(IngestionError, match=r"calendar\.csv"):
        M5Ingestor(db, SqlRenderer(repo_root / "sql"), tmp_path / "empty").ingest()


def test_validator_catches_negative_units(ingested_db):
    db, _ = ingested_db
    with db.connect() as con:
        con.execute(
            "UPDATE sales SET units_sold = -5 "
            "WHERE store_id = 'CA_1' AND sku_id = 'HOBBIES_1_001' AND date = ?",
            [date(2011, 1, 29)],
        )
    report = DataValidator(db).run()
    assert not report.passed
    assert "no_negative_units" in {c.name for c in report.failures}
    with pytest.raises(DataValidationError, match="no_negative_units"):
        report.raise_if_failed()
