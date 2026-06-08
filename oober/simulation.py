"""
Simulation Harness (Person B)

Generates synthetic demand traces and orchestrates the full multi-window
simulation loop for both JointOpt and SeqBaseline. Collects per-window metrics.
"""

import numpy as np

from city_graph import build_city_graph
from feasibility_filter import build_feasibility_graph
from ilp_engine import solve_joint_opt
from sequential_baseline import solve_sequential_baseline
from metrics import (
    compute_wait_time,
    compute_earnings_variance,
    compute_price_deviation,
    compute_matching_rate,
)


def generate_time_window_data(
    num_riders: int,       # e.g., randomly between 15-30 per window
    num_drivers: int,      # e.g., randomly between 20-35 per window
    num_zones: int = 10,
    seed: int = None
) -> tuple[list[dict], list[dict]]:
    """
    Generates synthetic riders and drivers for one time window.

    Riders: each has {id, origin_zone, dest_zone, wtp}
      - origin_zone, dest_zone: random integers in [0, num_zones)
      - wtp: drawn from Normal(mean=50, std=15), clipped to [20, 100]

    Drivers: each has {id, current_zone, maf}
      - current_zone: random integer in [0, num_zones)
      - maf: drawn from Normal(mean=30, std=8), clipped to [10, 60]

    Note: calibrate so ~60-70% of (rider, driver) pairs are feasible
    (i.e., wtp >= maf for most pairs). The Normal distributions above
    achieve this since E[wtp]=50 > E[maf]=30.

    Args:
        num_riders: Number of riders to generate.
        num_drivers: Number of drivers to generate.
        num_zones: Number of city zones for zone assignment.
        seed: Random seed for reproducibility (None for random).

    Returns:
        (riders_list, drivers_list) tuple.
    """
    raise NotImplementedError("TODO: Person B — implement data generator")


def run_simulation(
    num_windows: int = 10,      # use 10 for demo speed (report uses 20)
    riders_per_window: tuple = (15, 30),
    drivers_per_window: tuple = (20, 35),
    delta: float = 0.10,
    fairness_tolerance: float = 0.30,
    num_zones: int = 10,
    seed: int = 42
) -> dict:
    """
    Runs the full multi-window simulation for BOTH JointOpt and SeqBaseline.

    For each window t = 0, 1, ..., num_windows-1:
      1. Generate rider/driver data
      2. Build city graph (reuse same graph across windows)
      3. Run JointOpt → collect metrics
      4. Run SeqBaseline (same input data) → collect metrics
      5. Update price_memory and earnings_history from JointOpt results

    Args:
        num_windows: Number of time windows to simulate.
        riders_per_window: (min, max) range for rider count per window.
        drivers_per_window: (min, max) range for driver count per window.
        delta: Price stability threshold for ILP.
        fairness_tolerance: Earnings fairness tolerance for ILP.
        num_zones: Number of zones in the city graph.
        seed: Master random seed.

    Returns:
        dict with keys:
          'joint_opt': {
              'wait_times': [float per window],
              'earnings_variances': [float per window],
              'price_deviations': [float per window],
              'matching_rates': [float per window],
              'solve_times': [float per window]
          },
          'seq_baseline': {
              'wait_times': [...],
              'earnings_variances': [...],
              'price_deviations': [...],
              'matching_rates': [...],
              'solve_times': [...]
          },
          'summary': {
              'joint_opt_avg_wait': float,
              'seq_baseline_avg_wait': float,
              'wait_time_improvement_pct': float,
              ... (one entry per metric)
          }
    """
    raise NotImplementedError("TODO: Person B — implement simulation loop")
