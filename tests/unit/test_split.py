"""Tests for the chronological train/validation/test split."""

from datetime import date, timedelta

import polars as pl
import pytest

from demandpilot.config.models import TrainConfig
from demandpilot.exceptions import ForecastError
from demandpilot.forecasting.split import chronological_split


def _dataset(n_days: int) -> pl.DataFrame:
    start = date(2020, 1, 1)
    dates = [start + timedelta(days=i) for i in range(n_days)]
    return pl.DataFrame({"origin_date": dates, "value": list(range(n_days))})


def _train_config(**overrides: int) -> TrainConfig:
    base = {"test_size_days": 3, "validation_size_days": 2, "cv_folds": 1, "origin_stride_days": 1}
    base.update(overrides)
    return TrainConfig(**base)


def test_split_sizes_match_configured_day_counts():
    dataset = _dataset(20)
    split = chronological_split(dataset, _train_config())
    assert split.test["origin_date"].n_unique() == 3
    assert split.validation["origin_date"].n_unique() == 2
    assert split.train["origin_date"].n_unique() == 20 - 3 - 2


def test_split_is_chronological_with_no_overlap():
    dataset = _dataset(20)
    split = chronological_split(dataset, _train_config())
    assert split.train["origin_date"].max() < split.validation["origin_date"].min()
    assert split.validation["origin_date"].max() < split.test["origin_date"].min()


def test_split_test_set_is_the_most_recent_dates():
    dataset = _dataset(20)
    split = chronological_split(dataset, _train_config())
    all_dates = sorted(dataset["origin_date"].unique().to_list())
    assert sorted(split.test["origin_date"].unique().to_list()) == all_dates[-3:]


def test_split_handles_multiple_rows_per_origin_date():
    dataset = pl.concat([_dataset(10), _dataset(10)])  # e.g. two horizons stacked
    split = chronological_split(dataset, _train_config())
    assert split.train.height + split.validation.height + split.test.height == dataset.height


def test_insufficient_origin_dates_raises():
    dataset = _dataset(4)  # needs at least test(3) + validation(2) + 1 = 6
    with pytest.raises(ForecastError, match="Not enough distinct origin dates"):
        chronological_split(dataset, _train_config())
