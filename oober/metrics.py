"""
Computes evaluation metrics for ride-hailing assignments and system performance.

This module is part of the Oober joint price-and-match
optimisation system. It provides functions to compute wait time,
driver earnings variance, price deviation, and matching rates.
"""

from typing import Any

import networkx as nx
import numpy as np

try:
    from .type_defs import Assignment, PriceMemory, Rider
except ImportError:
    from type_defs import Assignment, PriceMemory, Rider

__all__ = [
    "compute_wait_time",
    "compute_earnings_variance",
    "compute_price_deviation",
    "compute_matching_rate",
]

# Constants
# Minimum number of matched drivers required to calculate variance
MIN_DRIVERS_FOR_VARIANCE = 2
# Absolute buffer value when computing price stability violations
STABILITY_BUFFER = 0.01


def compute_wait_time(
    assignments: list[Assignment],
    feasibility_graph: nx.Graph,
) -> float:
    """Computes the total wait time (travel cost) for matched pairs.

    Args:
        assignments: List of matched (rider_id, driver_id, price) triples.
        feasibility_graph: Bipartite graph containing travel_cost edge attributes.

    Returns:
        float: The sum of travel costs for all matches.

    Notes:
        Encodes the total wait time metric:
        sum_{(r,d) in A} travel_cost_{rd}
        where A is the set of matched rider-driver pairs.
    """
    total_wait = 0.0

    for rider_id, driver_id, _ in assignments:
        total_wait += feasibility_graph[("rider", rider_id)][
            ("driver", driver_id)
        ]["travel_cost"]

    return total_wait


def compute_earnings_variance(
    assignments: list[Assignment],
    # Deprecated/unused parameter for backward compatibility
    drivers: list[dict[str, Any]] | None = None,
) -> float:
    """Variance is computed over matched drivers in the current window.

    Cross-window driver equity is tracked separately via the earnings history
    record.

    Args:
        assignments: List of matched (rider_id, driver_id, price) triples.
        drivers: List of driver dictionaries with keys including 'id'.

    Returns:
        float: The variance of driver earnings over matched drivers, or 0.0 if fewer
            than 2 drivers are matched.

    Notes:
        Encodes the driver earnings variance metric:
        Var(E_d) for all matched drivers d, where E_d is the earnings of driver d in the current window.
        Returns 0.0 if there are fewer than 2 matched drivers.
    """
    earnings = {}

    for _, driver_id, price in assignments:
        earnings[driver_id] = earnings.get(driver_id, 0) + price

    matched_earnings = list(earnings.values())

    if len(matched_earnings) < MIN_DRIVERS_FOR_VARIANCE:
        return 0.0

    return float(np.var(matched_earnings))


def compute_price_deviation(
    assignments: list[Assignment],
    price_memory: PriceMemory,
    riders: list[Rider],
    delta: float,
) -> float:
    """Computes the fraction of matched rides violating the price stability delta.

    Args:
        assignments: List of matched (rider_id, driver_id, price) triples.
        price_memory: Maps (origin_zone, dest_zone) corridors to previous prices.
        riders: List of rider dictionaries.
        delta: Maximum fractional price deviation allowed.

    Returns:
        float: The fraction of assignments exceeding delta.

    Notes:
        Encodes the price deviation violation metric:
        sum_{ (r,d,p) in A, corridor(r) in PriceMemory } I(|p - prev_price| > delta * prev_price + 0.01) / N
        where I is the indicator function and N is the number of checked assignments.
    """
    rider_lookup = {rider["id"]: rider for rider in riders}

    violations = 0
    checked = 0

    for rider_id, _, price in assignments:
        rider = rider_lookup[rider_id]

        corridor = (rider["origin_zone"], rider["dest_zone"])

        if corridor not in price_memory:
            continue

        prev_price = price_memory[corridor]

        checked += 1

        if abs(price - prev_price) > delta * prev_price + STABILITY_BUFFER:
            violations += 1

    return violations / checked if checked else 0.0


def compute_matching_rate(
    assignments: list[Assignment],
    total_riders: int,
) -> float:
    """Computes the match rate (matched riders / total riders).

    Args:
        assignments: List of matched (rider_id, driver_id, price) triples.
        total_riders: Total number of riders requesting a ride.

    Returns:
        float: The matching rate.

    Notes:
        Encodes the matching rate metric:
        |A| / |R|
        where A is the set of assignments and R is the set of all riders in the time window.
    """
    if total_riders == 0:
        return 0.0

    return len(assignments) / total_riders