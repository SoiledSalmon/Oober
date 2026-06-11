"""
City Graph Module (Person B)

Represents the service area as a weighted directed graph. Nodes are zones
(e.g., Zone 0-9). Edge weights are travel costs (proxy for travel time).
Exposes a travel cost query function used by the ILP engine to populate
bipartite edge weights.
"""

import networkx as nx
import numpy as np

__all__ = ["build_city_graph", "get_travel_cost"]


def _add_random_edges(graph: nx.DiGraph, num_zones: int, rng: np.random.Generator) -> None:
    """Add random outgoing edges (3 to 5 per node) with travel costs in [5, 50]."""
    for node in range(num_zones):
        num_edges = int(rng.integers(3, 6))
        possible_targets = [z for z in range(num_zones) if z != node]
        num_edges = min(num_edges, len(possible_targets))
        targets = rng.choice(possible_targets, size=num_edges, replace=False)
        for target in targets:
            cost = float(rng.integers(5, 51))  # uniform in [5, 50]
            graph.add_edge(node, int(target), cost=cost)


def _ensure_strong_connectivity(graph: nx.DiGraph, rng: np.random.Generator) -> None:
    """Guarantee reachability between all nodes by bridging SCCs with higher cost edges."""
    if not nx.is_strongly_connected(graph):
        sccs = list(nx.strongly_connected_components(graph))
        representatives = [next(iter(scc)) for scc in sccs]
        for i in range(len(representatives)):
            src = representatives[i]
            dst = representatives[(i + 1) % len(representatives)]
            if not graph.has_edge(src, dst):
                cost = float(rng.integers(40, 51))  # higher cost for bridges
                graph.add_edge(src, dst, cost=cost)


def build_city_graph(num_zones: int = 10, seed: int = 42) -> nx.DiGraph:
    """
    Creates a synthetic directed weighted city graph.

    Nodes: 0 to num_zones-1 (each representing a zone)
    Edges: randomly connected with travel cost weights in range [5, 50].
           Each node connects to ~3-5 others randomly to ensure reasonable
           density so that most zone-pairs have a valid path.

    After random edge generation, the graph is checked for strongly connected component
    reachability, adding bridging edges if necessary to guarantee connectivity.

    Args:
        num_zones: Number of zones (nodes) in the city graph.
        seed: Random seed for reproducibility.

    Returns:
        nx.DiGraph with edge attribute 'cost'.
    """
    rng = np.random.default_rng(seed)
    graph = nx.DiGraph()
    graph.add_nodes_from(range(num_zones))

    _add_random_edges(graph, num_zones, rng)
    _ensure_strong_connectivity(graph, rng)

    return graph


def get_travel_cost(graph: nx.DiGraph, origin_zone: int, dest_zone: int) -> float:
    """
    Returns shortest-path travel cost from origin_zone to dest_zone.

    Uses Dijkstra's algorithm (nx.shortest_path_length with weight='cost').
    Returns a large fallback cost (e.g., 999) if no path exists.

    Args:
        graph: The city DiGraph with 'cost' edge weights.
        origin_zone: Starting zone index.
        dest_zone: Destination zone index.

    Returns:
        Shortest-path travel cost as a float, or 999 if unreachable.
    """
    if origin_zone == dest_zone:
        return 0.0

    try:
        return float(nx.shortest_path_length(graph, origin_zone, dest_zone, weight="cost"))
    except nx.NetworkXNoPath:
        return 999.0
    except nx.NodeNotFound:
        return 999.0


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== City Graph Module — Standalone Test ===\n")

    g = build_city_graph(num_zones=10, seed=42)
    print(f"Nodes: {g.number_of_nodes()}")
    print(f"Edges: {g.number_of_edges()}")
    print(f"Strongly connected: {nx.is_strongly_connected(g)}")

    # Sample travel costs
    print("\nSample travel costs (Dijkstra shortest path):")
    test_pairs = [(0, 5), (3, 7), (9, 1), (4, 4), (2, 8)]
    for src, dst in test_pairs:
        cost = get_travel_cost(g, src, dst)
        print(f"  Zone {src} -> Zone {dst}: {cost:.1f}")

    # Verify all pairs are reachable (no 999s expected with connectivity guarantee)
    unreachable = 0
    for src in range(10):
        for dst in range(10):
            if src != dst and get_travel_cost(g, src, dst) >= 999:
                unreachable += 1
    print(f"\nUnreachable zone pairs: {unreachable} / 90")
    print("\n[OK] city_graph.py tests complete.")
