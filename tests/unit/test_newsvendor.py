"""Tests for the newsvendor domain math."""

import pytest

from demandpilot.core.newsvendor import critical_fractile, safety_stock


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


def test_safety_stock_positive_when_order_above_median():
    assert safety_stock(order_quantity=12.0, median_demand=10.0) == pytest.approx(2.0)


def test_safety_stock_negative_when_order_below_median():
    assert safety_stock(order_quantity=7.0, median_demand=10.0) == pytest.approx(-3.0)


def test_safety_stock_zero_when_order_equals_median():
    assert safety_stock(order_quantity=10.0, median_demand=10.0) == pytest.approx(0.0)
