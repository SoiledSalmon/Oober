"""
Orchestrates multi-window simulation runs comparing JointOpt against SeqBaseline.

This module is part of the Oober joint price-and-match
optimisation system. It handles the generation of demand traces,
executes solvers over sequential windows, and accumulates performance statistics.
"""

from typing import Any

import networkx as nx
import numpy as np

try:
    from .city_graph import build_city_graph
    from .config import (
        DEFAULT_DELTA,
        DEFAULT_FAIRNESS_TOLERANCE,
        DEFAULT_NUM_ZONES,
        DRIVER_MAF_MAX,
        DRIVER_MAF_MEAN,
        DRIVER_MAF_MIN,
        DRIVER_MAF_STD,
        RIDER_WTP_MAX,
        RIDER_WTP_MEAN,
        RIDER_WTP_MIN,
        RIDER_WTP_STD,
    )
    from .feasibility_filter import build_feasibility_graph
    from .ilp_engine import solve_joint_opt
    from .metrics import (
        compute_earnings_variance,
        compute_matching_rate,
        compute_price_deviation,
        compute_wait_time,
    )
    from .sequential_baseline import solve_sequential_baseline
    from .type_defs import (
        Assignment,
        Driver,
        OptimizationResult,
        PriceMemory,
        Rider,
    )
except ImportError:
    from city_graph import build_city_graph
    from config import (
        DEFAULT_DELTA,
        DEFAULT_FAIRNESS_TOLERANCE,
        DEFAULT_NUM_ZONES,
        DRIVER_MAF_MAX,
        DRIVER_MAF_MEAN,
        DRIVER_MAF_MIN,
        DRIVER_MAF_STD,
        RIDER_WTP_MAX,
        RIDER_WTP_MEAN,
        RIDER_WTP_MIN,
        RIDER_WTP_STD,
    )
    from feasibility_filter import build_feasibility_graph
    from ilp_engine import solve_joint_opt
    from metrics import (
        compute_earnings_variance,
        compute_matching_rate,
        compute_price_deviation,
        compute_wait_time,
    )
    from sequential_baseline import solve_sequential_baseline
    from type_defs import (
        Assignment,
        Driver,
        OptimizationResult,
        PriceMemory,
        Rider,
    )

__all__ = [
    "generate_time_window_data",
    "run_simulation",
    "run_simulation_with_trace",
]

# Constants
ROUNDING_PRECISION = 2  # Rounding precision for WTP and MAF values
# Denominator offset to safeguard against division by zero
DIVISION_SAFEGUARD_DENOMINATOR_OFFSET = 1e-9
PERCENTAGE_SCALER = 100  # Scaler to convert fractions to percentages
SOLVER_TIME_PRECISION = 4  # Decimal rounding precision for solver execution times
# Upper bound limit for random number generator seed generation
MASTER_SEED_LIMIT = 2**31


def generate_time_window_data(
    num_riders: int,
    num_drivers: int,
    num_zones: int = DEFAULT_NUM_ZONES,
    seed: int | None = None,
) -> tuple[list[Rider], list[Driver]]:
    """Generates synthetic riders and drivers for one time window.

    Args:
        num_riders: Number of riders to generate.
        num_drivers: Number of drivers to generate.
        num_zones: Number of zones in the city graph.
        seed: Seed for random number generation.

    Returns:
        tuple[list[Rider], list[Driver]]: A tuple containing:
            - list[Rider]: The generated riders.
            - list[Driver]: The generated drivers.
    """
    rng = np.random.default_rng(seed)

    # Generate riders
    riders: list[Rider] = []
    wtp_values = np.clip(
        rng.normal(RIDER_WTP_MEAN, RIDER_WTP_STD, size=num_riders),
        RIDER_WTP_MIN,
        RIDER_WTP_MAX,
    )
    for i in range(num_riders):
        origin = int(rng.integers(0, num_zones))
        dest = int(rng.integers(0, num_zones))
        while dest == origin:
            dest = int(rng.integers(0, num_zones))
        riders.append(
            {
                "id": i,
                "origin_zone": origin,
                "dest_zone": dest,
                "wtp": round(float(wtp_values[i]), ROUNDING_PRECISION),
            }
        )

    # Generate drivers
    drivers: list[Driver] = []
    maf_values = np.clip(
        rng.normal(DRIVER_MAF_MEAN, DRIVER_MAF_STD, size=num_drivers),
        DRIVER_MAF_MIN,
        DRIVER_MAF_MAX,
    )
    for i in range(num_drivers):
        drivers.append(
            {
                "id": i,
                "current_zone": int(rng.integers(0, num_zones)),
                "maf": round(float(maf_values[i]), ROUNDING_PRECISION),
            }
        )

    return riders, drivers


def _update_price_memory(
    price_memory: PriceMemory,
    assignments: list[Assignment],
    riders: list[Rider],
) -> None:
    """Update price_memory in-place from assignments for the current window."""
    rider_lookup = {r["id"]: r for r in riders}
    for rider_id, _driver_id, price in assignments:
        rider = rider_lookup[rider_id]
        corridor = (rider["origin_zone"], rider["dest_zone"])
        price_memory[corridor] = price


def _update_earnings_history(
    earnings_history: dict[int, float],
    assignments: list[Assignment],
) -> None:
    """Update cumulative earnings_history in-place from assignments."""
    for _rider_id, driver_id, price in assignments:
        earnings_history[driver_id] = (
            earnings_history.get(driver_id, 0.0) + price
        )


def _safe_improvement_pct(
    baseline_val: float,
    jointopt_val: float,
    higher_is_better: bool = False,
) -> float:
    """Compute improvement percentage."""
    denom = max(abs(baseline_val), DIVISION_SAFEGUARD_DENOMINATOR_OFFSET)
    if higher_is_better:
        return (jointopt_val - baseline_val) / denom * PERCENTAGE_SCALER
    return (baseline_val - jointopt_val) / denom * PERCENTAGE_SCALER


def _init_metrics_storage() -> dict[str, list[float]]:
    """Initialize lists to store per-window metric evaluation values."""
    return {
        "wait_times": [],
        "earnings_variances": [],
        "price_deviations": [],
        "matching_rates": [],
        "solve_times": [],
    }


def _run_joint_opt_with_fallback(
    feas_graph: nx.Graph,
    price_memory: PriceMemory,
    earnings_history: dict[int, float],
    delta: float,
    fairness_tolerance: float,
    window_id: int,
    riders: list[Rider],
    drivers: list[Driver],
    city_graph: nx.DiGraph,
) -> OptimizationResult:
    """Run JointOpt solver, and fall back to SeqBaseline on solver errors or failures."""
    try:
        jo_result = solve_joint_opt(
            feasibility_graph=feas_graph,
            price_memory=price_memory,
            delta=delta,
            fairness_tolerance=fairness_tolerance,
            window_id=window_id,
        )
    except Exception as exc:
        print(
            f"[WARN] JointOpt failed on window {window_id} with exception: {exc}"
        )
        jo_result = {
            "assignments": [],
            "total_wait_cost": 0.0,
            "matched_count": 0,
            "solver_status": "Error",
            "solve_time_sec": 0.0,
        }

    if jo_result["solver_status"] not in ("Optimal", "Feasible", "Relaxed"):
        print(
            f"[WARN] JointOpt status {jo_result['solver_status']} "
            f"on window {window_id}. Falling back."
        )
        fallback_res = solve_sequential_baseline(
            riders=riders,
            drivers=drivers,
            city_graph=city_graph,
            price_memory=price_memory,
        )
        return {
            "assignments": fallback_res["assignments"],
            "total_wait_cost": fallback_res["total_wait_cost"],
            "matched_count": fallback_res["matched_count"],
            "solver_status": "Fallback",
            "solve_time_sec": fallback_res["solve_time_sec"],
        }
    return jo_result


def _record_window_metrics(
    result: OptimizationResult,
    drivers: list[Driver],
    price_memory: PriceMemory,
    riders: list[Rider],
    delta: float,
    metrics: dict[str, list[float]],
    feas_graph: nx.Graph,
    num_riders: int,
) -> tuple[float, float, float, float]:
    """Compute metrics for a solver result and record them in the metrics dict."""
    wait = compute_wait_time(result["assignments"], feas_graph)
    ev = compute_earnings_variance(result["assignments"])
    pd = compute_price_deviation(
        result["assignments"], price_memory, riders, delta
    )
    mr = compute_matching_rate(result["assignments"], num_riders)

    metrics["wait_times"].append(wait)
    metrics["earnings_variances"].append(ev)
    metrics["price_deviations"].append(pd)
    metrics["matching_rates"].append(mr)
    metrics["solve_times"].append(result["solve_time_sec"])

    return wait, ev, pd, mr


def _run_single_window_simulation(
    window_seed: int,
    window_id: int,
    riders_per_window: tuple[int, int],
    drivers_per_window: tuple[int, int],
    num_zones: int,
    city_graph: nx.DiGraph,
    jo_price_memory: PriceMemory,
    jo_earnings_history: dict[int, float],
    sb_price_memory: PriceMemory,
    sb_earnings_history: dict[int, float],
    delta: float,
    fairness_tolerance: float,
    jo_metrics: dict[str, list[float]],
    sb_metrics: dict[str, list[float]],
    return_trace: bool,
) -> dict[str, Any] | None:
    """Run a single step of the multi-window simulation, updating metrics and state."""
    win_rng = np.random.default_rng(window_seed)
    num_riders = int(
        win_rng.integers(riders_per_window[0], riders_per_window[1] + 1)
    )
    num_drivers = int(
        win_rng.integers(drivers_per_window[0], drivers_per_window[1] + 1)
    )

    riders, drivers = generate_time_window_data(
        num_riders=num_riders,
        num_drivers=num_drivers,
        num_zones=num_zones,
        seed=window_seed + 1,
    )
    feas_graph = build_feasibility_graph(riders, drivers, city_graph)

    jo_result = _run_joint_opt_with_fallback(
        feas_graph,
        jo_price_memory,
        jo_earnings_history,
        delta,
        fairness_tolerance,
        window_id,
        riders,
        drivers,
        city_graph,
    )
    sb_result = solve_sequential_baseline(
        riders=riders,
        drivers=drivers,
        city_graph=city_graph,
        price_memory=sb_price_memory,
    )

    jo_w, jo_ev, jo_pd, jo_mr = _record_window_metrics(
        jo_result,
        drivers,
        jo_price_memory,
        riders,
        delta,
        jo_metrics,
        feas_graph,
        num_riders,
    )
    sb_w, sb_ev, sb_pd, sb_mr = _record_window_metrics(
        sb_result,
        drivers,
        sb_price_memory,
        riders,
        delta,
        sb_metrics,
        feas_graph,
        num_riders,
    )

    _update_price_memory(jo_price_memory, jo_result["assignments"], riders)
    _update_earnings_history(jo_earnings_history, jo_result["assignments"])
    _update_price_memory(sb_price_memory, sb_result["assignments"], riders)
    _update_earnings_history(sb_earnings_history, sb_result["assignments"])

    if return_trace:
        return {
            "window_id": window_id,
            "riders": riders,
            "drivers": drivers,
            "joint_opt_assignments": [
                [rid, did, pr] for rid, did, pr in jo_result["assignments"]
            ],
            "seq_baseline_assignments": [
                [rid, did, pr] for rid, did, pr in sb_result["assignments"]
            ],
            "joint_opt_wait_time": jo_w,
            "joint_opt_earnings_variance": jo_ev,
            "joint_opt_price_deviation": jo_pd,
            "joint_opt_matching_rate": jo_mr,
            "joint_opt_solve_time": jo_result["solve_time_sec"],
            "joint_opt_solver_status": jo_result["solver_status"],
            "seq_baseline_wait_time": sb_w,
            "seq_baseline_earnings_variance": sb_ev,
            "seq_baseline_price_deviation": sb_pd,
            "seq_baseline_matching_rate": sb_mr,
            "seq_baseline_solve_time": sb_result["solve_time_sec"],
        }
    return None


def _compile_summary_metrics(
    jo_metrics: dict[str, list[float]],
    sb_metrics: dict[str, list[float]],
) -> dict[str, float]:
    """Compile average summary statistics and calculate improvement percentages."""

    def _avg(values: list[float]) -> float:
        return sum(values) / max(len(values), 1)

    jo_avg_wait = _avg(jo_metrics["wait_times"])
    sb_avg_wait = _avg(sb_metrics["wait_times"])
    jo_avg_ev = _avg(jo_metrics["earnings_variances"])
    sb_avg_ev = _avg(sb_metrics["earnings_variances"])
    jo_avg_pd = _avg(jo_metrics["price_deviations"])
    sb_avg_pd = _avg(sb_metrics["price_deviations"])
    jo_avg_mr = _avg(jo_metrics["matching_rates"])
    sb_avg_mr = _avg(sb_metrics["matching_rates"])
    jo_avg_st = _avg(jo_metrics["solve_times"])
    sb_avg_st = _avg(sb_metrics["solve_times"])

    return {
        "joint_opt_avg_wait": jo_avg_wait,
        "seq_baseline_avg_wait": sb_avg_wait,
        "wait_time_improvement_pct": _safe_improvement_pct(
            sb_avg_wait, jo_avg_wait
        ),
        "joint_opt_avg_earnings_variance": jo_avg_ev,
        "seq_baseline_avg_earnings_variance": sb_avg_ev,
        "earnings_variance_improvement_pct": _safe_improvement_pct(
            sb_avg_ev, jo_avg_ev
        ),
        "joint_opt_avg_price_deviation": jo_avg_pd,
        "seq_baseline_avg_price_deviation": sb_avg_pd,
        "price_deviation_improvement_pct": _safe_improvement_pct(
            sb_avg_pd, jo_avg_pd
        ),
        "joint_opt_avg_matching_rate": jo_avg_mr,
        "seq_baseline_avg_matching_rate": sb_avg_mr,
        "matching_rate_improvement_pct": _safe_improvement_pct(
            sb_avg_mr, jo_avg_mr, higher_is_better=True
        ),
        "joint_opt_avg_solve_time": jo_avg_st,
        "seq_baseline_avg_solve_time": sb_avg_st,
    }


def _execute_simulation(
    num_windows: int = 10,
    riders_per_window: tuple[int, int] = (15, 30),
    drivers_per_window: tuple[int, int] = (20, 35),
    delta: float = DEFAULT_DELTA,
    fairness_tolerance: float = DEFAULT_FAIRNESS_TOLERANCE,
    num_zones: int = DEFAULT_NUM_ZONES,
    seed: int = 42,
    return_trace: bool = False,
) -> dict[str, Any]:
    """Core simulation runner that handles execution and detailed traces."""
    master_rng = np.random.default_rng(seed)
    city_graph = build_city_graph(num_zones=num_zones, seed=seed)

    graph_data = None
    if return_trace:
        graph_data = {
            "nodes": list(city_graph.nodes()),
            "edges": [
                {"source": int(u), "target": int(v), "cost": float(d["cost"])}
                for u, v, d in city_graph.edges(data=True)
            ],
        }

    jo_price_memory: PriceMemory = {}
    jo_earnings_history = {}
    sb_price_memory: PriceMemory = {}
    sb_earnings_history = {}
    jo_metrics = _init_metrics_storage()
    sb_metrics = _init_metrics_storage()
    window_traces: list[dict[str, Any]] = []

    for window_id in range(num_windows):
        window_seed = int(master_rng.integers(0, MASTER_SEED_LIMIT))
        trace = _run_single_window_simulation(
            window_seed,
            window_id,
            riders_per_window,
            drivers_per_window,
            num_zones,
            city_graph,
            jo_price_memory,
            jo_earnings_history,
            sb_price_memory,
            sb_earnings_history,
            delta,
            fairness_tolerance,
            jo_metrics,
            sb_metrics,
            return_trace,
        )
        if trace is not None:
            window_traces.append(trace)

    summary = _compile_summary_metrics(jo_metrics, sb_metrics)
    res = {
        "joint_opt": jo_metrics,
        "seq_baseline": sb_metrics,
        "summary": summary,
    }
    if return_trace:
        res["graph"] = graph_data
        res["windows"] = window_traces
    return res


def run_simulation(
    num_windows: int = 10,
    riders_per_window: tuple[int, int] = (15, 30),
    drivers_per_window: tuple[int, int] = (20, 35),
    delta: float = DEFAULT_DELTA,
    fairness_tolerance: float = DEFAULT_FAIRNESS_TOLERANCE,
    num_zones: int = DEFAULT_NUM_ZONES,
    seed: int = 42,
) -> dict[str, Any]:
    """Runs the full multi-window simulation for BOTH JointOpt and SeqBaseline.

    Args:
        num_windows: Number of time windows to run.
        riders_per_window: Bounds (min, max) for riders generated per window.
        drivers_per_window: Bounds (min, max) for drivers generated per window.
        delta: Price stability threshold.
        fairness_tolerance: Earnings fairness tolerance.
        num_zones: Number of city zones.
        seed: Master random seed.

    Returns:
        dict[str, Any]: Compiled summary metrics comparing both approaches.
    """
    return _execute_simulation(
        num_windows=num_windows,
        riders_per_window=riders_per_window,
        drivers_per_window=drivers_per_window,
        delta=delta,
        fairness_tolerance=fairness_tolerance,
        num_zones=num_zones,
        seed=seed,
        return_trace=False,
    )


def run_simulation_with_trace(
    num_windows: int = 10,
    riders_per_window: tuple[int, int] = (15, 30),
    drivers_per_window: tuple[int, int] = (20, 35),
    delta: float = DEFAULT_DELTA,
    fairness_tolerance: float = DEFAULT_FAIRNESS_TOLERANCE,
    num_zones: int = DEFAULT_NUM_ZONES,
    seed: int = 42,
) -> dict[str, Any]:
    """Extended simulation that returns trace data for dashboard visualization.

    Args:
        num_windows: Number of time windows to run.
        riders_per_window: Bounds (min, max) for riders generated per window.
        drivers_per_window: Bounds (min, max) for drivers generated per window.
        delta: Price stability threshold.
        fairness_tolerance: Earnings fairness tolerance.
        num_zones: Number of city zones.
        seed: Master random seed.

    Returns:
        dict[str, Any]: Compiled summary metrics and step-by-step trace data.
    """
    return _execute_simulation(
        num_windows=num_windows,
        riders_per_window=riders_per_window,
        drivers_per_window=drivers_per_window,
        delta=delta,
        fairness_tolerance=fairness_tolerance,
        num_zones=num_zones,
        seed=seed,
        return_trace=True,
    )


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Simulation Harness — Standalone Test ===\n")

    # Quick test of data generator
    print("--- Data Generator ---")
    riders_list, drivers_list = generate_time_window_data(
        num_riders=20, num_drivers=25, num_zones=10, seed=42
    )
    print(
        f"Generated {len(riders_list)} riders and {len(drivers_list)} drivers"
    )

    wtp_vals = [r["wtp"] for r in riders_list]
    maf_vals = [d["maf"] for d in drivers_list]
    print(
        f"WTP range: [{min(wtp_vals):.1f}, {max(wtp_vals):.1f}], "
        f"mean={np.mean(wtp_vals):.1f}"
    )
    print(
        f"MAF range: [{min(maf_vals):.1f}, {max(maf_vals):.1f}], "
        f"mean={np.mean(maf_vals):.1f}"
    )

    # Count feasible pairs
    feasible = sum(
        1 for r in riders_list for d in drivers_list if r["wtp"] >= d["maf"]
    )
    total = len(riders_list) * len(drivers_list)
    print(f"Feasible pairs: {feasible}/{total} ({100*feasible/total:.0f}%)")

    # Full simulation test
    print("\n--- Full Simulation (3 windows) ---")
    try:
        results = run_simulation(num_windows=3, num_zones=8, seed=42)
        summary = results["summary"]
        print(
            f"Wait time improvement: {summary['wait_time_improvement_pct']:.1f}%"
        )
        print(
            f"Earnings var improvement: {summary['earnings_variance_improvement_pct']:.1f}%"
        )
        print(
            f"Price dev improvement: {summary['price_deviation_improvement_pct']:.1f}%"
        )
        print(
            f"Matching rate improvement: {summary['matching_rate_improvement_pct']:.1f}%"
        )
        print("\n[OK] simulation.py tests complete.")
    except NotImplementedError as exc:
        print(f"\n[SKIP] Full simulation requires Person A/C modules: {exc}")
        print(
            "[OK] Data generator verified. Full sim will work once all stubs are done."
        )
