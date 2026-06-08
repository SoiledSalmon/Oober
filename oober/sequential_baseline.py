"""
Sequential Baseline — SeqBaseline (Person B)

Implements the standard surge-then-match pipeline for comparison.
Step 1: Compute a single surge price per corridor based on demand-supply ratio.
Step 2: Greedily assign drivers to riders who can afford the surge price.
"""

import time

import networkx as nx

from city_graph import get_travel_cost


def solve_sequential_baseline(
    riders: list[dict],
    drivers: list[dict],
    city_graph: nx.DiGraph,
    price_memory: dict
) -> dict:
    """
    Sequential surge-then-match baseline.

    Step 1 — Surge Pricing:
      For each unique (origin_zone, dest_zone) corridor in riders:
        demand = number of riders on that corridor
        supply = number of drivers within 2 zones of that corridor's origin
        surge_multiplier = max(1.0, demand / max(supply, 1))
        base_price = average MAF of all drivers
        surge_price[corridor] = base_price * surge_multiplier

    Step 2 — Greedy Matching:
      For each rider (sorted by WTP descending):
        corridor = (rider.origin_zone, rider.dest_zone)
        price = surge_price[corridor]
        If rider.wtp >= price:
          Find nearest available driver whose maf <= price
          Assign them; mark both as unavailable

    Args:
        riders: List of rider dicts with keys {id, origin_zone, dest_zone, wtp}.
        drivers: List of driver dicts with keys {id, current_zone, maf}.
        city_graph: nx.DiGraph with edge attribute 'cost'.
        price_memory: Dict mapping (origin_zone, dest_zone) corridors to last price.

    Returns:
        dict with keys:
          'assignments': list of (rider_id, driver_id, price) tuples
          'total_wait_cost': float
          'matched_count': int
          'solver_status': 'Greedy'
          'solve_time_sec': float
    """
    raise NotImplementedError("TODO: Person B — implement sequential baseline")
