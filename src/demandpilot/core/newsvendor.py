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


def realized_cost_breakdown(
    order_quantity: float,
    actual_demand: float,
    understock_cost_ratio: float,
    overstock_cost_ratio: float,
    sell_price: float,
) -> tuple[float, float]:
    """Realized newsvendor cost for one decision, split by cause.

    ``understock_cost = Cu * max(D - Q, 0) * sell_price``;
    ``overstock_cost = Co * max(Q - D, 0) * sell_price`` — scaled by
    ``sell_price`` since cost ratios are expressed per unit of sell price
    (ADR-012). Exactly one of the two is nonzero for any given decision.

    Args:
        order_quantity: The quantity ordered (``Q``).
        actual_demand: The realized demand (``D``).
        understock_cost_ratio: ``Cu`` as a ratio of sell price.
        overstock_cost_ratio: ``Co`` as a ratio of sell price.
        sell_price: The unit's sell price on the day demand was realized.

    Returns:
        ``(understock_cost, overstock_cost)``, in the same currency as
        ``sell_price``.
    """
    understock_units = max(actual_demand - order_quantity, 0.0)
    overstock_units = max(order_quantity - actual_demand, 0.0)
    return (
        sell_price * understock_cost_ratio * understock_units,
        sell_price * overstock_cost_ratio * overstock_units,
    )


def realized_cost(
    order_quantity: float,
    actual_demand: float,
    understock_cost_ratio: float,
    overstock_cost_ratio: float,
    sell_price: float,
) -> float:
    """Total realized newsvendor cost for one decision, in currency units.

    The sum of :func:`realized_cost_breakdown`'s two components. Used by
    Volume 5's historical policy replay to compare policies in real
    currency, not dimensionless ratios.

    Args:
        order_quantity: The quantity ordered (``Q``).
        actual_demand: The realized demand (``D``).
        understock_cost_ratio: ``Cu`` as a ratio of sell price.
        overstock_cost_ratio: ``Co`` as a ratio of sell price.
        sell_price: The unit's sell price on the day demand was realized.

    Returns:
        The realized cost, in the same currency as ``sell_price``.
    """
    understock_cost, overstock_cost = realized_cost_breakdown(
        order_quantity, actual_demand, understock_cost_ratio, overstock_cost_ratio, sell_price
    )
    return understock_cost + overstock_cost
