"""
Metrics Module

Computes evaluation metrics for ride-hailing assignments, including wait time,
driver earnings variance, price deviation, and matching rate.
"""

from typing import Any
import numpy as np
import networkx as nx

__all__ = [
    "compute_wait_time",
    "compute_earnings_variance",
    "compute_price_deviation",
    "compute_matching_rate",
]


def compute_wait_time(
    assignments: list[tuple[int, int, float]],
    feasibility_graph: nx.Graph,
) -> float:
    """Computes the total wait time (travel cost) for matched pairs.

    Args:
        assignments: List of matched (rider_id, driver_id, price) triples.
        feasibility_graph: Bipartite graph containing travel_cost edge attributes.

    Returns:
        The sum of travel costs for all matches.
    """
    total_wait = 0.0

    for rider_id, driver_id, _ in assignments:
        total_wait += feasibility_graph[
            ('rider', rider_id)
        ][
            ('driver', driver_id)
        ]['travel_cost']

    return total_wait


def compute_earnings_variance(
    assignments: list[tuple[int, int, float]],
    drivers: list[dict[str, Any]],
) -> float:
    """Variance is computed over matched drivers in the current window.

    Cross-window driver equity is tracked separately via the earnings history
    record.

    Args:
        assignments: List of matched (rider_id, driver_id, price) triples.
        drivers: List of driver dictionaries with keys including 'id'.

    Returns:
        The variance of driver earnings over matched drivers, or 0.0 if fewer
        than 2 drivers are matched.
    """
    earnings = {}

    for _, driver_id, price in assignments:
        earnings[driver_id] = earnings.get(driver_id, 0) + price

    matched_earnings = list(earnings.values())

    if len(matched_earnings) < 2:
        return 0.0

    return float(np.var(matched_earnings))


def compute_price_deviation(
    assignments: list[tuple[int, int, float]],
    price_memory: dict[tuple[int, int], float],
    riders: list[dict[str, Any]],
    delta: float,
) -> float:
    """Computes the fraction of matched rides violating the price stability delta.

    Args:
        assignments: List of matched (rider_id, driver_id, price) triples.
        price_memory: Maps (origin_zone, dest_zone) corridors to previous prices.
        riders: List of rider dictionaries.
        delta: Maximum fractional price deviation allowed.

    Returns:
        The fraction of assignments exceeding delta.
    """
    rider_lookup = {
        rider['id']: rider
        for rider in riders
    }

    violations = 0
    checked = 0

    for rider_id, _, price in assignments:
        rider = rider_lookup[rider_id]

        corridor = (
            rider['origin_zone'],
            rider['dest_zone']
        )

        if corridor not in price_memory:
            continue

        prev_price = price_memory[corridor]

        checked += 1

        if abs(price - prev_price) > delta * prev_price:
            violations += 1

    return violations / checked if checked else 0.0


def compute_matching_rate(
    assignments: list[tuple[int, int, float]],
    total_riders: int,
) -> float:
    """Computes the match rate (matched riders / total riders).

    Args:
        assignments: List of matched (rider_id, driver_id, price) triples.
        total_riders: Total number of riders requesting a ride.

    Returns:
        The matching rate.
    """
    if total_riders == 0:
        return 0.0

    return len(assignments) / total_riders