"""
City Graph Module (Person B)

Represents the service area as a weighted directed graph. Nodes are zones
(e.g., Zone 0-9). Edge weights are travel costs (proxy for travel time).
Exposes a travel cost query function used by the ILP engine to populate
bipartite edge weights.
"""

import networkx as nx
import numpy as np


def build_city_graph(num_zones: int = 10, seed: int = 42) -> nx.DiGraph:
    """
    Creates a synthetic directed weighted city graph.

    Nodes: 0 to num_zones-1 (each representing a zone)
    Edges: randomly connected with travel cost weights in range [5, 50].
           Each node connects to ~3-5 others randomly to ensure reasonable
           density so that most zone-pairs have a valid path.

    Args:
        num_zones: Number of zones (nodes) in the city graph.
        seed: Random seed for reproducibility.

    Returns:
        nx.DiGraph with edge attribute 'cost'.
    """
    raise NotImplementedError("TODO: Person B — implement city graph construction")


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
    raise NotImplementedError("TODO: Person B — implement travel cost query")
