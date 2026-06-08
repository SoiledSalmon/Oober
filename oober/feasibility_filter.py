"""
Two-Sided Acceptance Filter (Person A)

Implements the core two-sided acceptance constraint from the report.
For every (rider, driver) candidate pair, checks whether there exists a
price that satisfies both the rider's Willingness-To-Pay (WTP) and the
driver's Minimum Acceptable Fare (MAF). If MAF_d > WTP_r, the pair is
infeasible and discarded. Returns the bipartite graph of only feasible pairs.
"""

import networkx as nx

from city_graph import get_travel_cost


def build_feasibility_graph(
    riders: list[dict],       # each dict: {id, origin_zone, dest_zone, wtp}
    drivers: list[dict],      # each dict: {id, current_zone, maf}
    city_graph: nx.DiGraph
) -> nx.Graph:
    """
    Builds a bipartite graph G = (R ∪ D, E).

    Nodes:
      - Rider nodes labeled as ('rider', rider_id)
      - Driver nodes labeled as ('driver', driver_id)
      - Rider nodes have bipartite=0, driver nodes have bipartite=1

    Edge (r, d) exists ONLY IF riders[r]['wtp'] >= drivers[d]['maf'].

    Edge attributes:
      - 'travel_cost': get_travel_cost(city_graph, driver.current_zone, rider.origin_zone)
      - 'price_lb': drivers[d]['maf']       (lower bound of feasible price interval)
      - 'price_ub': riders[r]['wtp']        (upper bound of feasible price interval)

    Args:
        riders: List of rider dicts with keys {id, origin_zone, dest_zone, wtp}.
        drivers: List of driver dicts with keys {id, current_zone, maf}.
        city_graph: nx.DiGraph with edge attribute 'cost'.

    Returns:
        nx.Graph (bipartite) with rider and driver nodes and feasible edges.
    """
    raise NotImplementedError("TODO: Person A — implement feasibility filter")
