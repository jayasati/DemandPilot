"""Chronological train/validation/test split of an assembled dataset.

Splits and backtests must respect time order (see
docs/CODE_REVIEW_CHECKLIST.md) — never shuffled, so no future origin date can
leak into an earlier partition.
"""

from dataclasses import dataclass

import polars as pl

from demandpilot.config.models import TrainConfig
from demandpilot.exceptions import ForecastError


@dataclass(frozen=True)
class DatasetSplit:
    """A chronological train/validation/test partition of an assembled dataset."""

    train: pl.DataFrame
    validation: pl.DataFrame
    test: pl.DataFrame


def chronological_split(dataset: pl.DataFrame, train_config: TrainConfig) -> DatasetSplit:
    """Split ``dataset`` into train/validation/test by ``origin_date``.

    The most recent ``test_size_days`` distinct origin dates become the test
    set, the ``validation_size_days`` before that become validation, and every
    earlier origin date becomes training.

    Args:
        dataset: Assembled dataset with an ``origin_date`` column.
        train_config: Split sizes, in distinct origin-date days.

    Returns:
        The three partitions.

    Raises:
        ForecastError: If there are not enough distinct origin dates for the
            configured split sizes.
    """
    origin_dates = sorted(dataset["origin_date"].unique().to_list())
    required = train_config.test_size_days + train_config.validation_size_days
    if len(origin_dates) <= required:
        raise ForecastError(
            f"Not enough distinct origin dates ({len(origin_dates)}) for the configured "
            f"split (test={train_config.test_size_days} + "
            f"validation={train_config.validation_size_days} = {required}); "
            f"need at least {required + 1}."
        )

    test_start = origin_dates[-train_config.test_size_days]
    validation_start = origin_dates[-required]

    train = dataset.filter(pl.col("origin_date") < validation_start)
    validation = dataset.filter(
        (pl.col("origin_date") >= validation_start) & (pl.col("origin_date") < test_start)
    )
    test = dataset.filter(pl.col("origin_date") >= test_start)
    return DatasetSplit(train=train, validation=validation, test=test)
