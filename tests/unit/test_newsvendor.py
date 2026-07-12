"""Tests for the newsvendor domain math."""

import pytest

from demandpilot.core.newsvendor import critical_fractile


def test_symmetric_costs_give_median():
    assert critical_fractile(1.0, 1.0) == pytest.approx(0.5)


def test_expensive_stockouts_push_fractile_up():
    assert critical_fractile(9.0, 1.0) == pytest.approx(0.9)


def test_expensive_overstock_pushes_fractile_down():
    assert critical_fractile(1.0, 3.0) == pytest.approx(0.25)


@pytest.mark.parametrize("cu,co", [(0.0, 1.0), (-1.0, 1.0), (1.0, 0.0), (1.0, -2.0)])
def test_non_positive_costs_rejected(cu, co):
    with pytest.raises(ValueError):
        critical_fractile(cu, co)
