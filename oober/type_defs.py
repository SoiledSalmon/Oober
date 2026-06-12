"""
Type definitions and aliases for the Oober project.

This module is part of the Oober joint price-and-match
optimisation system. It defines standard structured types
such as Rider, Driver, and Assignment to ensure PEP 484 compliance.
"""

from typing import TypedDict


class Rider(TypedDict):
    id: int
    origin_zone: int
    dest_zone: int
    wtp: float


class Driver(TypedDict):
    id: int
    current_zone: int
    maf: float


PriceMemory = dict[tuple[int, int], float]

Assignment = tuple[int, int, float]


class OptimizationResult(TypedDict):
    assignments: list[Assignment]
    total_wait_cost: float
    matched_count: int
    solver_status: str
    solve_time_sec: float
