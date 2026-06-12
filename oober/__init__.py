"""
Package initializer for the oober optimization codebase.

This module is part of the Oober joint price-and-match
optimisation system. It exports the core graph, filtering,
optimization, metrics, simulation, and type definitions.
"""

from .city_graph import build_city_graph, get_travel_cost
from .feasibility_filter import build_feasibility_graph
from .ilp_engine import solve_joint_opt
from .metrics import (
    compute_earnings_variance,
    compute_matching_rate,
    compute_price_deviation,
    compute_wait_time,
)
from .sequential_baseline import solve_sequential_baseline
from .simulation import run_simulation, run_simulation_with_trace
from .type_defs import Assignment, Driver, OptimizationResult, PriceMemory, Rider

__all__ = [
    "Assignment",
    "Driver",
    "OptimizationResult",
    "PriceMemory",
    "Rider",
    "build_city_graph",
    "build_feasibility_graph",
    "compute_earnings_variance",
    "compute_matching_rate",
    "compute_price_deviation",
    "compute_wait_time",
    "get_travel_cost",
    "run_simulation",
    "run_simulation_with_trace",
    "solve_joint_opt",
    "solve_sequential_baseline",
]

