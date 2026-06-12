"""
Implements a sequential surge-then-match baseline matching algorithm.

This module is part of the Oober joint price-and-match
optimisation system. It implements the surge-then-match pipeline
where prices are set via corridor surge pricing, and matches are greedily assigned.
"""

import time
from typing import Any

import networkx as nx

try:
    from .city_graph import get_travel_cost
    from .config import DEFAULT_MAX_HOPS
    from .feasibility_filter import build_feasibility_graph
    from .type_defs import Driver, OptimizationResult, PriceMemory, Rider
except ImportError:
    from city_graph import get_travel_cost
    from config import DEFAULT_MAX_HOPS
    from feasibility_filter import build_feasibility_graph
    from type_defs import Driver, OptimizationResult, PriceMemory, Rider

__all__ = ["solve_sequential_baseline"]

# Constants
# Base surge multiplier when supply equals or exceeds demand
SURGE_PRICING_BASE_MULTIPLIER = 1.0
# Scaling factor for the demand-to-supply ratio in surge pricing
SURGE_MULTIPLIER_SCALING_FACTOR = 0.15
# Lower bound for supply/drivers count to safeguard against division by zero
SUPPLY_GUARD = 1


def _count_drivers_within_hops(
    city_graph: nx.DiGraph,
    drivers: list[Driver],
    origin_zone: int,
    max_hops: int = DEFAULT_MAX_HOPS,
) -> int:
    """Count drivers whose zone is reachable from *their* zone to ``origin_zone``
    within ``max_hops`` hops (unweighted shortest path length).

    We use the **reverse graph** so that a single BFS from ``origin_zone``
    gives us all zones that can reach it within ``max_hops`` hops.

    Args:
        city_graph: The city DiGraph with travel costs.
        drivers: List of active driver dictionaries.
        origin_zone: Starting zone index.
        max_hops: Maximum path distance/hops.

    Returns:
        int: Total number of drivers within max_hops of origin_zone.
    """
    reverse_graph = city_graph.reverse(copy=False)
    try:
        reachable = nx.single_source_shortest_path_length(
            reverse_graph, origin_zone, cutoff=max_hops
        )
    except nx.NodeNotFound:
        return 0

    reachable_zones = set(reachable.keys())
    return sum(1 for d in drivers if d["current_zone"] in reachable_zones)


def solve_sequential_baseline(
    riders: list[Rider],
    drivers: list[Driver],
    city_graph: nx.DiGraph,
    price_memory: PriceMemory,
) -> OptimizationResult:
    """Sequential surge-then-match baseline.

    Step 1 — Surge Pricing:
      For each unique (origin_zone, dest_zone) corridor in riders:
        demand = number of riders on that corridor
        supply = number of drivers within 2 hops of that corridor's origin
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
        riders: List of Rider dicts with keys {id, origin_zone, dest_zone, wtp}.
        drivers: List of Driver dicts with keys {id, current_zone, maf}.
        city_graph: nx.DiGraph with edge attribute 'cost'.
        price_memory: Dict mapping (origin_zone, dest_zone) corridors to last price.

    Returns:
        OptimizationResult: Structured dict containing assignments and performance metrics.

    Notes:
        Encodes the surge price formula:
        surge_price[corridor] = base_price * (1.0 + 0.15 * (demand / max(supply, 1)))
        where base_price is the average driver MAF, demand is the zone demand,
        and supply is the driver count within max_hops.
    """
    start_time = time.perf_counter()

    # ── Step 1: Surge Pricing ────────────────────────────────────────────────

    # Compute base price as mean MAF across all drivers
    base_price = sum(d["maf"] for d in drivers) / max(
        len(drivers), SUPPLY_GUARD
    )

    # Count demand per corridor
    corridor_demand: dict[tuple[int, int], int] = {}
    zone_demand: dict[int, int] = {}
    for r in riders:
        corridor = (r["origin_zone"], r["dest_zone"])
        corridor_demand[corridor] = corridor_demand.get(corridor, 0) + 1
        zone_demand[r["origin_zone"]] = (
            zone_demand.get(r["origin_zone"], 0) + 1
        )

    # Compute surge price per corridor using zone-level demand
    surge_price: dict[tuple[int, int], float] = {}
    for corridor in corridor_demand.keys():
        origin_zone = corridor[0]
        demand = zone_demand.get(origin_zone, 0)
        supply = _count_drivers_within_hops(
            city_graph, drivers, origin_zone, max_hops=DEFAULT_MAX_HOPS
        )
        surge_multiplier = (
            SURGE_PRICING_BASE_MULTIPLIER
            + SURGE_MULTIPLIER_SCALING_FACTOR
            * (demand / max(supply, SUPPLY_GUARD))
        )
        surge_price[corridor] = base_price * surge_multiplier

    # Build the feasibility graph to leverage shared travel costs and candidate filtering
    feasibility_graph = build_feasibility_graph(riders, drivers, city_graph)

    # ── Step 2: Greedy Matching ──────────────────────────────────────────────

    # Sort riders by WTP descending (highest willingness first)
    sorted_riders = sorted(riders, key=lambda r: r["wtp"], reverse=True)

    assigned_driver_ids: set[int] = set()
    assignments: list[tuple[int, int, float]] = []
    total_wait_cost: float = 0.0

    for rider in sorted_riders:
        corridor = (rider["origin_zone"], rider["dest_zone"])
        price = surge_price[corridor]

        # Rider must be willing to pay the surge price
        if rider["wtp"] < price:
            continue

        # Find the nearest available driver whose MAF <= price
        best_driver = None
        best_cost = float("inf")

        r_node = ("rider", rider["id"])
        if r_node in feasibility_graph:
            for d_node in feasibility_graph.neighbors(r_node):
                did = d_node[1]
                if did in assigned_driver_ids:
                    continue

                driver_data = feasibility_graph.nodes[d_node]["data"]
                if driver_data["maf"] > price:
                    continue

                travel_cost = feasibility_graph[r_node][d_node]["travel_cost"]
                if travel_cost < best_cost:
                    best_cost = travel_cost
                    best_driver = driver_data

        if best_driver is not None:
            assignments.append((rider["id"], best_driver["id"], price))
            total_wait_cost += best_cost
            assigned_driver_ids.add(best_driver["id"])

    solve_time = time.perf_counter() - start_time

    return {
        "assignments": assignments,
        "total_wait_cost": total_wait_cost,
        "matched_count": len(assignments),
        "solver_status": "Greedy",
        "solve_time_sec": solve_time,
    }


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from city_graph import build_city_graph

    print("=== Sequential Baseline — Standalone Test ===\n")

    g = build_city_graph(num_zones=6, seed=99)

    riders_test: list[Rider] = [
        {"id": 0, "origin_zone": 0, "dest_zone": 3, "wtp": 60.0},
        {"id": 1, "origin_zone": 1, "dest_zone": 4, "wtp": 45.0},
        {"id": 2, "origin_zone": 2, "dest_zone": 5, "wtp": 80.0},
        {"id": 3, "origin_zone": 0, "dest_zone": 3, "wtp": 25.0},
        {"id": 4, "origin_zone": 3, "dest_zone": 1, "wtp": 55.0},
    ]

    drivers_test: list[Driver] = [
        {"id": 0, "current_zone": 0, "maf": 20.0},
        {"id": 1, "current_zone": 2, "maf": 35.0},
        {"id": 2, "current_zone": 4, "maf": 25.0},
        {"id": 3, "current_zone": 1, "maf": 30.0},
        {"id": 4, "current_zone": 5, "maf": 40.0},
    ]

    result = solve_sequential_baseline(riders_test, drivers_test, g, price_memory={})

    print(f"Status: {result['solver_status']}")
    print(f"Matched: {result['matched_count']} / {len(riders_test)}")
    print(f"Total wait cost: {result['total_wait_cost']:.1f}")
    print(f"Solve time: {result['solve_time_sec']*1000:.1f} ms")
    print("\nAssignments:")
    for rid, did, price in result["assignments"]:
        print(f"  Rider {rid} -> Driver {did}  @ price {price:.2f}")

    print("\n[OK] sequential_baseline.py tests complete.")
