"""Newsvendor (single-period stochastic inventory) domain math.

The optimal order quantity under asymmetric over/understock costs is the
demand quantile at the *critical fractile* ``Cu / (Cu + Co)``, where ``Cu`` is
the unit cost of understocking (lost margin + goodwill penalty) and ``Co`` the
unit cost of overstocking (unrecovered cost + holding). See
docs/adr/003-newsvendor.md and docs/adr/012-cost-coupled-quantiles.md.

The order-quantity policy itself is a quantile forecast at the critical
fractile (Volume 3's ``QuantileForecaster`` produces it directly — no further
numerical optimization is needed once the demand distribution is estimated);
this module holds the surrounding pure math.
"""


def critical_fractile(understock_cost: float, overstock_cost: float) -> float:
    """Return the newsvendor critical fractile ``Cu / (Cu + Co)``.

    Args:
        understock_cost: Cost of missing one unit of demand (``Cu``). Must be
            strictly positive — otherwise stocking anything is never optimal
            and the model degenerates.
        overstock_cost: Cost of one unsold unit (``Co``). Must be strictly
            positive — otherwise the optimal order is unbounded.

    Returns:
        The optimal service level, strictly between 0 and 1.

    Raises:
        ValueError: If either cost is not strictly positive.
    """
    if understock_cost <= 0:
        raise ValueError(f"understock_cost must be > 0, got {understock_cost}")
    if overstock_cost <= 0:
        raise ValueError(f"overstock_cost must be > 0, got {overstock_cost}")
    return understock_cost / (understock_cost + overstock_cost)


def safety_stock(order_quantity: float, median_demand: float) -> float:
    """Order quantity above (or below) the median demand forecast.

    A positive value means the critical fractile sits above the median (the
    economics favor guarding against stockouts more than overstock); a
    negative value means the reverse — deliberately stocking less than the
    expected case because overstock is the costlier mistake. Both are valid
    outcomes of the newsvendor economics, not error conditions.

    Args:
        order_quantity: The recommended order quantity (the critical-fractile
            demand forecast).
        median_demand: The median (P50) demand forecast for the same period.

    Returns:
        ``order_quantity - median_demand``.
    """
    return order_quantity - median_demand
