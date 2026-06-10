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
    rng = np.random.default_rng(seed)

    # --- Generate riders ---
    riders: list[dict] = []
    wtp_values = np.clip(rng.normal(50, 15, size=num_riders), 20, 100)

    for i in range(num_riders):
        origin = int(rng.integers(0, num_zones))
        dest = int(rng.integers(0, num_zones))
        # Avoid same-zone trips
        while dest == origin:
            dest = int(rng.integers(0, num_zones))

        riders.append({
            "id": i,
            "origin_zone": origin,
            "dest_zone": dest,
            "wtp": round(float(wtp_values[i]), 2),
        })

    # --- Generate drivers ---
    drivers: list[dict] = []
    maf_values = np.clip(rng.normal(30, 8, size=num_drivers), 10, 60)

    for i in range(num_drivers):
        drivers.append({
            "id": i,
            "current_zone": int(rng.integers(0, num_zones)),
            "maf": round(float(maf_values[i]), 2),
        })

    return riders, drivers


def _update_price_memory(
    price_memory: dict,
    assignments: list[tuple],
    riders: list[dict],
) -> None:
    """Update price_memory in-place from assignments for the current window."""
    rider_lookup = {r["id"]: r for r in riders}
    for rider_id, _driver_id, price in assignments:
        rider = rider_lookup[rider_id]
        corridor = (rider["origin_zone"], rider["dest_zone"])
        price_memory[corridor] = price


def _update_earnings_history(
    earnings_history: dict,
    assignments: list[tuple],
) -> None:
    """Update cumulative earnings_history in-place from assignments."""
    for _rider_id, driver_id, price in assignments:
        earnings_history[driver_id] = earnings_history.get(driver_id, 0.0) + price


def _safe_improvement_pct(
    baseline_val: float,
    jointopt_val: float,
    higher_is_better: bool = False,
) -> float:
    """
    Compute improvement percentage.

    For metrics where *lower* is better (wait time, variance, deviation):
        improvement = (baseline - jointopt) / baseline * 100

    For metrics where *higher* is better (matching rate):
        improvement = (jointopt - baseline) / baseline * 100
    """
    denom = max(abs(baseline_val), 1e-9)
    if higher_is_better:
        return (jointopt_val - baseline_val) / denom * 100
    return (baseline_val - jointopt_val) / denom * 100


def _execute_simulation(
    num_windows: int = 10,
    riders_per_window: tuple = (15, 30),
    drivers_per_window: tuple = (20, 35),
    delta: float = 0.10,
    fairness_tolerance: float = 0.30,
    num_zones: int = 10,
    seed: int = 42,
    return_trace: bool = False,
) -> dict:
    """
    Core simulation runner that handles both summary execution and detailed traces.
    """
    master_rng = np.random.default_rng(seed)

    # Build city graph once (reused across all windows)
    city_graph = build_city_graph(num_zones=num_zones, seed=seed)

    # Serialize graph topology if trace requested
    graph_data = None
    if return_trace:
        graph_data = {
            "nodes": list(city_graph.nodes()),
            "edges": [
                {"source": int(u), "target": int(v), "cost": float(d["cost"])}
                for u, v, d in city_graph.edges(data=True)
            ],
        }

    # Independent state for each system
    jo_price_memory: dict = {}
    jo_earnings_history: dict = {}
    sb_price_memory: dict = {}
    sb_earnings_history: dict = {}

    # Per-window metric storage
    jo_metrics: dict[str, list] = {
        "wait_times": [],
        "earnings_variances": [],
        "price_deviations": [],
        "matching_rates": [],
        "solve_times": [],
    }
    sb_metrics: dict[str, list] = {
        "wait_times": [],
        "earnings_variances": [],
        "price_deviations": [],
        "matching_rates": [],
        "solve_times": [],
    }

    window_traces: list[dict] = []

    for window_id in range(num_windows):
        # Derive a per-window seed for reproducibility
        window_seed = int(master_rng.integers(0, 2**31))

        # 1. Generate rider/driver data for this window
        win_rng = np.random.default_rng(window_seed)
        num_riders = int(win_rng.integers(riders_per_window[0], riders_per_window[1] + 1))
        num_drivers = int(win_rng.integers(drivers_per_window[0], drivers_per_window[1] + 1))

        riders, drivers = generate_time_window_data(
            num_riders=num_riders,
            num_drivers=num_drivers,
            num_zones=num_zones,
            seed=window_seed + 1,  # offset to avoid RNG correlation with win_rng
        )

        # 2. Build feasibility graph (shared input for both systems)
        feas_graph = build_feasibility_graph(riders, drivers, city_graph)

        # ── 3. Run JointOpt ──────────────────────────────────────────────────
        try:
            jo_result = solve_joint_opt(
                feasibility_graph=feas_graph,
                price_memory=jo_price_memory,
                earnings_history=jo_earnings_history,
                delta=delta,
                fairness_tolerance=fairness_tolerance,
                window_id=window_id,
            )
        except Exception as exc:
            # Graceful failure: treat as error to trigger fallback
            print(f"[WARN] JointOpt failed on window {window_id} with exception: {exc}")
            jo_result = {
                "assignments": [],
                "total_wait_cost": 0.0,
                "matched_count": 0,
                "solver_status": "Error",
                "solve_time_sec": 0.0,
            }

        # Handle non-success solver status and apply Hierarchical Fallback:
        # If solver failed even after internal relaxations, fall back to SeqBaseline
        if jo_result["solver_status"] not in ("Optimal", "Feasible", "Relaxed"):
            print(f"[WARN] JointOpt status {jo_result['solver_status']} on window {window_id}. "
                  f"Falling back to SeqBaseline.")
            
            fallback_res = solve_sequential_baseline(
                riders=riders,
                drivers=drivers,
                city_graph=city_graph,
                price_memory=jo_price_memory,
            )
            jo_result = {
                "assignments": fallback_res["assignments"],
                "total_wait_cost": fallback_res["total_wait_cost"],
                "matched_count": fallback_res["matched_count"],
                "solver_status": "Fallback",
                "solve_time_sec": fallback_res["solve_time_sec"],
            }

        # ── 4. Run SeqBaseline ───────────────────────────────────────────────
        sb_result = solve_sequential_baseline(
            riders=riders,
            drivers=drivers,
            city_graph=city_graph,
            price_memory=sb_price_memory,
        )

        # ── 5. Compute metrics ───────────────────────────────────────────────
        jo_wait = compute_wait_time(jo_result["assignments"], feas_graph)
        jo_ev = compute_earnings_variance(jo_result["assignments"], drivers)
        jo_pd = compute_price_deviation(
            jo_result["assignments"], jo_price_memory, riders, delta
        )
        jo_mr = compute_matching_rate(jo_result["assignments"], num_riders)

        sb_wait = compute_wait_time(sb_result["assignments"], feas_graph)
        sb_ev = compute_earnings_variance(sb_result["assignments"], drivers)
        sb_pd = compute_price_deviation(
            sb_result["assignments"], sb_price_memory, riders, delta
        )
        sb_mr = compute_matching_rate(sb_result["assignments"], num_riders)

        jo_metrics["wait_times"].append(jo_wait)
        jo_metrics["earnings_variances"].append(jo_ev)
        jo_metrics["price_deviations"].append(jo_pd)
        jo_metrics["matching_rates"].append(jo_mr)
        jo_metrics["solve_times"].append(jo_result["solve_time_sec"])

        sb_metrics["wait_times"].append(sb_wait)
        sb_metrics["earnings_variances"].append(sb_ev)
        sb_metrics["price_deviations"].append(sb_pd)
        sb_metrics["matching_rates"].append(sb_mr)
        sb_metrics["solve_times"].append(sb_result["solve_time_sec"])

        # ── 6. Update state (independent per system) ─────────────────────────
        _update_price_memory(jo_price_memory, jo_result["assignments"], riders)
        _update_earnings_history(jo_earnings_history, jo_result["assignments"])

        _update_price_memory(sb_price_memory, sb_result["assignments"], riders)
        _update_earnings_history(sb_earnings_history, sb_result["assignments"])

        # ── 7. Per-window trace ─────────────────────────────────────────────
        if return_trace:
            window_traces.append({
                "window_id": window_id,
                "riders": riders,
                "drivers": drivers,
                "joint_opt_assignments": [
                    [rid, did, price] for rid, did, price in jo_result["assignments"]
                ],
                "seq_baseline_assignments": [
                    [rid, did, price] for rid, did, price in sb_result["assignments"]
                ],
                "joint_opt_wait_time": jo_wait,
                "joint_opt_earnings_variance": jo_ev,
                "joint_opt_price_deviation": jo_pd,
                "joint_opt_matching_rate": jo_mr,
                "joint_opt_solve_time": jo_result["solve_time_sec"],
                "joint_opt_solver_status": jo_result["solver_status"],
                "seq_baseline_wait_time": sb_wait,
                "seq_baseline_earnings_variance": sb_ev,
                "seq_baseline_price_deviation": sb_pd,
                "seq_baseline_matching_rate": sb_mr,
                "seq_baseline_solve_time": sb_result["solve_time_sec"],
            })

    # ── Build summary statistics ─────────────────────────────────────────────

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

    summary = {
        # Wait time (lower is better)
        "joint_opt_avg_wait": jo_avg_wait,
        "seq_baseline_avg_wait": sb_avg_wait,
        "wait_time_improvement_pct": _safe_improvement_pct(sb_avg_wait, jo_avg_wait),
        # Earnings variance (lower is better)
        "joint_opt_avg_earnings_variance": jo_avg_ev,
        "seq_baseline_avg_earnings_variance": sb_avg_ev,
        "earnings_variance_improvement_pct": _safe_improvement_pct(sb_avg_ev, jo_avg_ev),
        # Price deviation (lower is better)
        "joint_opt_avg_price_deviation": jo_avg_pd,
        "seq_baseline_avg_price_deviation": sb_avg_pd,
        "price_deviation_improvement_pct": _safe_improvement_pct(sb_avg_pd, jo_avg_pd),
        # Matching rate (higher is better)
        "joint_opt_avg_matching_rate": jo_avg_mr,
        "seq_baseline_avg_matching_rate": sb_avg_mr,
        "matching_rate_improvement_pct": _safe_improvement_pct(
            sb_avg_mr, jo_avg_mr, higher_is_better=True
        ),
        # Solve times
        "joint_opt_avg_solve_time": jo_avg_st,
        "seq_baseline_avg_solve_time": sb_avg_st,
    }

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
    riders_per_window: tuple = (15, 30),
    drivers_per_window: tuple = (20, 35),
    delta: float = 0.10,
    fairness_tolerance: float = 0.30,
    num_zones: int = 10,
    seed: int = 42,
) -> dict:
    """
    Runs the full multi-window simulation for BOTH JointOpt and SeqBaseline.
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
    riders_per_window: tuple = (15, 30),
    drivers_per_window: tuple = (20, 35),
    delta: float = 0.10,
    fairness_tolerance: float = 0.30,
    num_zones: int = 10,
    seed: int = 42,
) -> dict:
    """
    Extended simulation that returns the same results as ``run_simulation()``
    plus full per-window trace data for the frontend dashboard.
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
    riders, drivers = generate_time_window_data(
        num_riders=20, num_drivers=25, num_zones=10, seed=42
    )
    print(f"Generated {len(riders)} riders and {len(drivers)} drivers")

    wtp_vals = [r["wtp"] for r in riders]
    maf_vals = [d["maf"] for d in drivers]
    print(f"WTP range: [{min(wtp_vals):.1f}, {max(wtp_vals):.1f}], mean={np.mean(wtp_vals):.1f}")
    print(f"MAF range: [{min(maf_vals):.1f}, {max(maf_vals):.1f}], mean={np.mean(maf_vals):.1f}")

    # Count feasible pairs
    feasible = sum(1 for r in riders for d in drivers if r["wtp"] >= d["maf"])
    total = len(riders) * len(drivers)
    print(f"Feasible pairs: {feasible}/{total} ({100*feasible/total:.0f}%)")

    # Full simulation test (will fail if Person A/C stubs are not implemented)
    print("\n--- Full Simulation (3 windows) ---")
    try:
        results = run_simulation(num_windows=3, num_zones=8, seed=42)
        summary = results["summary"]
        print(f"Wait time improvement: {summary['wait_time_improvement_pct']:.1f}%")
        print(f"Earnings var improvement: {summary['earnings_variance_improvement_pct']:.1f}%")
        print(f"Price dev improvement: {summary['price_deviation_improvement_pct']:.1f}%")
        print(f"Matching rate improvement: {summary['matching_rate_improvement_pct']:.1f}%")
        print("\n[OK] simulation.py tests complete.")
    except NotImplementedError as exc:
        print(f"\n[SKIP] Full simulation requires Person A/C modules: {exc}")
        print("[OK] Data generator verified. Full sim will work once all stubs are done.")
