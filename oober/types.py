"""
Proxy wrapper for standard library types module to prevent shadowing conflicts.
"""

import os
import sys
from typing import TypedDict

# Find the directory containing this file
oober_dir = os.path.dirname(os.path.abspath(__file__))

# Temporarily remove oober directory from search path to import standard types
saved_path = sys.path.copy()
sys.path = [
    p
    for p in sys.path
    if p and os.path.abspath(p) != os.path.abspath(oober_dir)
]

# Import standard library types module
import types as _stdlib_types

# Restore original search path
sys.path = saved_path

# Populate globals with standard types attributes
globals().update(
    {
        k: v
        for k, v in _stdlib_types.__dict__.items()
        if not k.startswith("__")
    }
)


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
