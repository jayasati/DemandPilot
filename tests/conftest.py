"""Shared fixtures.

``m5_fixture_dir`` writes a tiny, fully deterministic dataset in the exact M5
CSV format (2 stores x 3 items x 56 days). It exists only to exercise the
ingestion code path — see docs/TESTING.md for the fixture policy.
"""

import csv
import logging
import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

START_DATE = date(2011, 1, 29)  # d_1, a Saturday, as in the real M5 calendar
N_DAYS = 56
EVENT_DAY_INDEX = 9  # 0-based; this day gets a National event (a holiday)

STORES = (("CA_1", "CA"), ("TX_1", "TX"))
ITEMS = (
    ("HOBBIES_1_001", "HOBBIES_1", "HOBBIES"),
    ("HOBBIES_1_002", "HOBBIES_1", "HOBBIES"),
    ("FOODS_3_001", "FOODS_3", "FOODS"),
)
# (store_id, item_id) -> first week index with a price; others start at week 0.
LATE_LAUNCH = {("TX_1", "FOODS_3_001"): 2}
LATE_LAUNCH_DROPPED_DAYS = 14  # 2 weeks x 7 days without a price


def units_for(item_idx: int, store_idx: int, day_idx: int) -> int:
    """Deterministic units_sold used by both the fixture and assertions."""
    return (item_idx * 3 + store_idx * 2 + day_idx) % 7


def price_for(item_idx: int, store_idx: int) -> float:
    """Deterministic sell price per (item, store)."""
    return 1.0 + item_idx + 0.25 * store_idx


def build_m5_fixture(dest: Path) -> None:
    """Write calendar.csv, sell_prices.csv, and sales_train_evaluation.csv."""
    dest.mkdir(parents=True, exist_ok=True)
    days = [START_DATE + timedelta(days=i) for i in range(N_DAYS)]
    week_keys = [11101 + i // 7 for i in range(N_DAYS)]

    with (dest / "calendar.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "date",
                "wm_yr_wk",
                "weekday",
                "wday",
                "month",
                "year",
                "d",
                "event_name_1",
                "event_type_1",
                "event_name_2",
                "event_type_2",
                "snap_CA",
                "snap_TX",
                "snap_WI",
            ]
        )
        for i, day in enumerate(days):
            event_name = "TestFest" if i == EVENT_DAY_INDEX else ""
            event_type = "National" if i == EVENT_DAY_INDEX else ""
            writer.writerow(
                [
                    day.isoformat(),
                    week_keys[i],
                    day.strftime("%A"),
                    (i % 7) + 1,
                    day.month,
                    day.year,
                    f"d_{i + 1}",
                    event_name,
                    event_type,
                    "",
                    "",
                    int(day.day <= 10),
                    int(5 <= day.day <= 15),
                    int(day.day >= 20),
                ]
            )

    with (dest / "sell_prices.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["store_id", "item_id", "wm_yr_wk", "sell_price"])
        all_weeks = sorted(set(week_keys))
        for store_idx, (store_id, _state) in enumerate(STORES):
            for item_idx, (item_id, _dept, _cat) in enumerate(ITEMS):
                first_week = LATE_LAUNCH.get((store_id, item_id), 0)
                for week in all_weeks[first_week:]:
                    writer.writerow([store_id, item_id, week, price_for(item_idx, store_idx)])

    with (dest / "sales_train_evaluation.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]
            + [f"d_{i + 1}" for i in range(N_DAYS)]
        )
        for store_idx, (store_id, state_id) in enumerate(STORES):
            for item_idx, (item_id, dept_id, cat_id) in enumerate(ITEMS):
                writer.writerow(
                    [
                        f"{item_id}_{store_id}_evaluation",
                        item_id,
                        dept_id,
                        cat_id,
                        store_id,
                        state_id,
                    ]
                    + [units_for(item_idx, store_idx, day_idx) for day_idx in range(N_DAYS)]
                )


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def m5_fixture_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dest = tmp_path_factory.mktemp("m5_raw")
    build_m5_fixture(dest)
    return dest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """A throwaway project root with real configs/ and sql/ copied in."""
    shutil.copytree(REPO_ROOT / "configs", tmp_path / "configs")
    shutil.copytree(REPO_ROOT / "sql", tmp_path / "sql")
    return tmp_path


@pytest.fixture
def reset_logging():
    """Close file handlers after a test so Windows can delete tmp dirs."""
    yield
    root = logging.getLogger()
    for logger in [root, logging.getLogger("demandpilot")]:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
