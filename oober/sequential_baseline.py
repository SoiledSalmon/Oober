"""
Sequential Baseline — SeqBaseline (Person B)

Implements the standard surge-then-match pipeline for comparison.
Step 1: Compute a single surge price per corridor based on demand-supply ratio.
Step 2: Greedily assign drivers to riders who can afford the surge price.
"""

import time

import networkx as nx

from city_graph import get_travel_cost


def _count_drivers_within_hops(
    city_graph: nx.DiGraph,
    drivers: list[dict],
    origin_zone: int,
    max_hops: int = 2,
) -> int:
    """
    Count drivers whose zone is reachable from *their* zone to ``origin_zone``
    within ``max_hops`` hops (unweighted shortest path length).

    We use the **reverse graph** so that a single BFS from ``origin_zone``
    gives us all zones that can reach it within ``max_hops`` hops.
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
    riders: list[dict],
    drivers: list[dict],
    city_graph: nx.DiGraph,
    price_memory: dict,
) -> dict:
    """
    Sequential surge-then-match baseline.

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
    start_time = time.perf_counter()

    # ── Step 1: Surge Pricing ────────────────────────────────────────────────

    # Compute base price as mean MAF across all drivers
    base_price = sum(d["maf"] for d in drivers) / max(len(drivers), 1)

    # Count demand per corridor
    corridor_demand: dict[tuple[int, int], int] = {}
    for r in riders:
        corridor = (r["origin_zone"], r["dest_zone"])
        corridor_demand[corridor] = corridor_demand.get(corridor, 0) + 1

    # Compute surge price per corridor
    surge_price: dict[tuple[int, int], float] = {}
    for corridor, demand in corridor_demand.items():
        origin_zone = corridor[0]
        supply = _count_drivers_within_hops(city_graph, drivers, origin_zone, max_hops=2)
        surge_multiplier = max(1.0, demand / max(supply, 1))
        surge_price[corridor] = base_price * surge_multiplier

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

        for driver in drivers:
            if driver["id"] in assigned_driver_ids:
                continue
            if driver["maf"] > price:
                continue

            travel_cost = get_travel_cost(
                city_graph, driver["current_zone"], rider["origin_zone"]
            )
            if travel_cost < best_cost:
                best_cost = travel_cost
                best_driver = driver

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

    riders = [
        {"id": 0, "origin_zone": 0, "dest_zone": 3, "wtp": 60},
        {"id": 1, "origin_zone": 1, "dest_zone": 4, "wtp": 45},
        {"id": 2, "origin_zone": 2, "dest_zone": 5, "wtp": 80},
        {"id": 3, "origin_zone": 0, "dest_zone": 3, "wtp": 25},
        {"id": 4, "origin_zone": 3, "dest_zone": 1, "wtp": 55},
    ]

    drivers = [
        {"id": 0, "current_zone": 0, "maf": 20},
        {"id": 1, "current_zone": 2, "maf": 35},
        {"id": 2, "current_zone": 4, "maf": 25},
        {"id": 3, "current_zone": 1, "maf": 30},
        {"id": 4, "current_zone": 5, "maf": 40},
    ]

    result = solve_sequential_baseline(riders, drivers, g, price_memory={})

    print(f"Status: {result['solver_status']}")
    print(f"Matched: {result['matched_count']} / {len(riders)}")
    print(f"Total wait cost: {result['total_wait_cost']:.1f}")
    print(f"Solve time: {result['solve_time_sec']*1000:.1f} ms")
    print("\nAssignments:")
    for rid, did, price in result["assignments"]:
        print(f"  Rider {rid} -> Driver {did}  @ price {price:.2f}")

    print("\n[OK] sequential_baseline.py tests complete.")
