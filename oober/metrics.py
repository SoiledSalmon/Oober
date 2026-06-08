"""
Evaluation Metrics (Person C)

Pure calculation functions. Takes raw assignment output and computes the four
evaluation metrics. No side effects, easy to unit test.
"""

import numpy as np
import networkx as nx


def compute_wait_time(
    assignments: list[tuple],
    feasibility_graph: nx.Graph
) -> float:
    """
    Sum of travel_cost values for all matched (r, d) pairs.

    Args:
        assignments: List of (rider_id, driver_id, price) tuples.
        feasibility_graph: Bipartite nx.Graph with 'travel_cost' edge attribute.

    Returns:
        Total wait cost as a float.
    """
    raise NotImplementedError("TODO: Person C — implement wait time metric")


def compute_earnings_variance(
    assignments: list[tuple],
    drivers: list[dict]
) -> float:
    """
    For each driver in assignments, compute their total earnings (sum of prices).
    Return variance of per-driver earnings list.
    Drivers with no assignment contribute 0 earnings.

    Args:
        assignments: List of (rider_id, driver_id, price) tuples.
        drivers: List of driver dictionaries to include unmatched drivers.

    Returns:
        Variance of per-driver earnings as a float.
    """
    raise NotImplementedError("TODO: Person C — implement earnings variance metric")


def compute_price_deviation(
    assignments: list[tuple],
    price_memory: dict,
    riders: list[dict],
    delta: float
) -> float:
    """
    For each assignment (r, d, price), look up corridor = (rider.origin, rider.dest).
    If corridor exists in price_memory:
      Check if |price - prev_price| > delta * prev_price
    Return fraction of assignments that violate the delta threshold.

    Args:
        assignments: List of (rider_id, driver_id, price) tuples.
        price_memory: Dict mapping (origin_zone, dest_zone) to previous price.
        riders: List of rider dicts with keys {id, origin_zone, dest_zone, wtp}.
        delta: Price stability threshold (fraction of previous price).

    Returns:
        Fraction of assignments violating the delta threshold (0.0 to 1.0).
    """
    raise NotImplementedError("TODO: Person C — implement price deviation metric")


def compute_matching_rate(assignments: list[tuple], total_riders: int) -> float:
    """
    Return len(assignments) / total_riders.

    Args:
        assignments: List of (rider_id, driver_id, price) tuples.
        total_riders: Total number of riders in the time window.

    Returns:
        Matching rate as a float (0.0 to 1.0).
    """
    raise NotImplementedError("TODO: Person C — implement matching rate metric")
