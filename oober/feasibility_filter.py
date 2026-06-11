"""
Two-Sided Acceptance Filter (Person A)

Implements the core two-sided acceptance constraint from the report.
For every (rider, driver) candidate pair, checks whether there exists a
price that satisfies both the rider's Willingness-To-Pay (WTP) and the
driver's Minimum Acceptable Fare (MAF). If MAF_d > WTP_r, the pair is
infeasible and discarded. Returns the bipartite graph of only feasible pairs.
"""
from typing import Any
import networkx as nx

try:
    from .city_graph import get_travel_cost
except ImportError:
    from city_graph import get_travel_cost

__all__ = ["build_feasibility_graph"]


def _add_rider_nodes(graph: nx.Graph, riders: list[dict[str, Any]]) -> None:
    """Add rider nodes to the bipartite graph."""
    for rider in riders:
        graph.add_node(
            ("rider", rider["id"]),
            bipartite=0,
            data=rider
        )


def _add_driver_nodes(graph: nx.Graph, drivers: list[dict[str, Any]]) -> None:
    """Add driver nodes to the bipartite graph."""
    for driver in drivers:
        graph.add_node(
            ("driver", driver["id"]),
            bipartite=1,
            data=driver
        )


def _add_feasible_edges(
    graph: nx.Graph,
    riders: list[dict[str, Any]],
    drivers: list[dict[str, Any]],
    city_graph: nx.DiGraph,
) -> None:
    """Add feasible edges satisfying the two-sided acceptance condition."""
    for rider in riders:
        for driver in drivers:
            # Two-sided feasibility condition
            if rider["wtp"] >= driver["maf"]:
                travel_cost = get_travel_cost(
                    city_graph,
                    driver["current_zone"],
                    rider["origin_zone"]
                )
                graph.add_edge(
                    ("rider", rider["id"]),
                    ("driver", driver["id"]),
                    travel_cost=travel_cost,
                    price_lb=driver["maf"],
                    price_ub=rider["wtp"],
                    origin_zone=rider["origin_zone"],
                    dest_zone=rider["dest_zone"]
                )


def build_feasibility_graph(
    riders: list[dict[str, Any]],
    drivers: list[dict[str, Any]],
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
      - 'travel_cost': get_travel_cost(city_graph,
                                       driver.current_zone,
                                       rider.origin_zone)

      - 'price_lb': drivers[d]['maf']
      - 'price_ub': riders[r]['wtp']

    Args:
        riders: List of rider dictionaries.
        drivers: List of driver dictionaries.
        city_graph: City graph with travel costs.

    Returns:
        nx.Graph (bipartite)
    """
    G = nx.Graph()
    _add_rider_nodes(G, riders)
    _add_driver_nodes(G, drivers)
    _add_feasible_edges(G, riders, drivers, city_graph)
    return G