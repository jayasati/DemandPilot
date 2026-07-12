"""End-to-end feature engineering tests: generated SQL, snapshots, leakage."""

import pytest

from demandpilot.config import load_config
from demandpilot.data import Database, M5Ingestor, apply_schema
from demandpilot.features import FeatureSnapshotBuilder
from demandpilot.sqlrender import SqlRenderer

pytestmark = pytest.mark.integration


@pytest.fixture
def ingested_db(tmp_path, repo_root, m5_fixture_dir):
    db = Database(tmp_path / "test.duckdb")
    apply_schema(db, repo_root / "sql")
    M5Ingestor(db, SqlRenderer(repo_root / "sql"), m5_fixture_dir).ingest()
    return db


@pytest.fixture
def features_config(repo_root):
    return load_config(repo_root).features


@pytest.fixture
def builder(repo_root):
    def _make(db):
        return FeatureSnapshotBuilder(db, repo_root / "sql", repo_root)

    return _make


def test_build_creates_first_snapshot(ingested_db, builder, features_config):
    info = builder(ingested_db).build(features_config)
    assert info.version == 1
    assert info.table_name == "feature_store_v1"
    assert info.config_hash
    with ingested_db.connect(read_only=True) as con:
        (count,) = con.execute(f"SELECT COUNT(*) FROM {info.table_name}").fetchone()
    assert count == info.row_count > 0


def test_build_twice_increments_version(ingested_db, builder, features_config):
    b = builder(ingested_db)
    first = b.build(features_config)
    second = b.build(features_config)
    assert second.version == first.version + 1
    assert second.table_name == "feature_store_v2"
    assert first.config_hash == second.config_hash


def test_manifest_records_lineage(ingested_db, builder, features_config):
    info = builder(ingested_db).build(features_config)
    with ingested_db.connect(read_only=True) as con:
        row = con.execute(
            "SELECT version, table_name, config_hash, row_count "
            "FROM feature_snapshots WHERE version = ?",
            [info.version],
        ).fetchone()
    assert row == (info.version, info.table_name, info.config_hash, info.row_count)


def test_snapshot_row_count_matches_sales(ingested_db, builder, features_config):
    info = builder(ingested_db).build(features_config)
    with ingested_db.connect(read_only=True) as con:
        (sales_count,) = con.execute("SELECT COUNT(*) FROM sales").fetchone()
    assert info.row_count == sales_count


def test_snapshot_has_no_current_day_leakage(ingested_db, builder, features_config):
    """The 7-day rolling mean must not include the current row's target."""
    info = builder(ingested_db).build(features_config)
    with ingested_db.connect(read_only=True) as con:
        rows = con.execute(f"""
            SELECT date, units_sold, units_sold_roll_mean_7
            FROM {info.table_name}
            WHERE store_id = 'CA_1' AND sku_id = 'HOBBIES_1_001'
            ORDER BY date
            LIMIT 10
            """).fetchall()
    # First row has no history at all: every window ends before it.
    assert rows[0][2] is None
    # Second row's "rolling mean" is exactly the first row's value — not its own.
    assert rows[1][2] == pytest.approx(rows[0][1])


def test_snapshot_lag_1_never_equals_current_row(ingested_db, builder, features_config):
    """A structural leakage check: lag_1 at date d must equal units_sold at d-1, never at d."""
    info = builder(ingested_db).build(features_config)
    with ingested_db.connect(read_only=True) as con:
        rows = con.execute(f"""
            SELECT units_sold, units_sold_lag_1
            FROM {info.table_name}
            WHERE store_id = 'CA_1' AND sku_id = 'HOBBIES_1_001'
              AND units_sold_lag_1 IS NOT NULL
            ORDER BY date
            """).fetchall()
    mismatches = [r for r in rows if r[1] == r[0]]
    # Coincidental equality is possible for individual rows (small integer domain);
    # requiring not-all-equal rules out the systematic bug of lag_1 aliasing units_sold.
    assert len(mismatches) < len(rows)
