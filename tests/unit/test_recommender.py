"""Unit tests for the recommender's early-stopping train/validation split."""

from datetime import date, timedelta

import polars as pl
import pytest

from demandpilot.exceptions import OptimizationError
from demandpilot.optimization.recommender import _train_validation_split


def _dataset(n_days: int) -> pl.DataFrame:
    start = date(2020, 1, 1)
    dates = [start + timedelta(days=i) for i in range(n_days)]
    return pl.DataFrame({"origin_date": dates, "value": list(range(n_days))})


def test_validation_is_the_most_recent_days():
    dataset = _dataset(10)
    train, validation = _train_validation_split(dataset, validation_size_days=3)
    all_dates = sorted(dataset["origin_date"].unique().to_list())
    assert sorted(validation["origin_date"].unique().to_list()) == all_dates[-3:]
    assert sorted(train["origin_date"].unique().to_list()) == all_dates[:-3]


def test_split_is_chronological_with_no_overlap():
    dataset = _dataset(10)
    train, validation = _train_validation_split(dataset, validation_size_days=3)
    assert train["origin_date"].max() < validation["origin_date"].min()


def test_split_covers_every_row():
    dataset = _dataset(10)
    train, validation = _train_validation_split(dataset, validation_size_days=3)
    assert train.height + validation.height == dataset.height


def test_insufficient_origin_dates_raises():
    dataset = _dataset(3)  # needs at least validation(3) + 1 = 4
    with pytest.raises(OptimizationError, match="Not enough distinct origin dates"):
        _train_validation_split(dataset, validation_size_days=3)
