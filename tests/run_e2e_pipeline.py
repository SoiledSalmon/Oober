import sys
import os
import numpy as np

# Ensure parent directory is in search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from oober.simulation import run_simulation_with_trace
except ImportError:
    from simulation import run_simulation_with_trace


def run_e2e_pipeline():
    print("=== Running End-to-End Pipeline Verification ===")
    
    delta = 0.10
    fairness_tolerance = 0.30
    num_zones = 10
    seed = 42
    
    # 1. Run 5-window simulation with trace
    trace_data = run_simulation_with_trace(
        num_windows=5,
        delta=delta,
        fairness_tolerance=fairness_tolerance,
        num_zones=num_zones,
        seed=seed
    )
    
    # Track corridor price history for temporal stability validation
    price_memory = {}
    
    # 2. Iterate through each window and verify constraints
    for window in trace_data["windows"]:
        window_id = window["window_id"]
        riders = window["riders"]
        drivers = window["drivers"]
        assignments = window["joint_opt_assignments"]
        status = window["joint_opt_solver_status"]
        
        print(f"\n--- Window {window_id} (Status: {status}, Matches: {len(assignments)}) ---")
        
        # Lookups
        rider_lookup = {r["id"]: r for r in riders}
        driver_lookup = {d["id"]: d for d in drivers}
        
        # Calculate target midpoint earnings T for this window
        feasible_midpoints = []
        for r in riders:
            for d in drivers:
                if r["wtp"] >= d["maf"]:
                    feasible_midpoints.append((r["wtp"] + d["maf"]) / 2.0)
        T = np.mean(feasible_midpoints) if feasible_midpoints else 0.0
        
        # Constraint variables
        assigned_riders = set()
        assigned_drivers = set()
        
        for rid, did, price in assignments:
            rider = rider_lookup[rid]
            driver = driver_lookup[did]
            
            # Constraint 1: Rider Uniqueness
            assert rid not in assigned_riders, f"Rider {rid} matched multiple times!"
            assigned_riders.add(rid)
            
            # Constraint 2: Driver Uniqueness
            assert did not in assigned_drivers, f"Driver {did} matched multiple times!"
            assigned_drivers.add(did)
            
            # Constraint 3: Edge Feasibility
            assert price >= driver["maf"] - 1e-5, f"Price {price} below driver MAF {driver['maf']}!"
            assert price <= rider["wtp"] + 1e-5, f"Price {price} above rider WTP {rider['wtp']}!"
            
            # Constraint 4: Temporal Price Stability
            corridor = (rider["origin_zone"], rider["dest_zone"])
            if status in ["Optimal", "Feasible"]:
                if corridor in price_memory:
                    prev_price = price_memory[corridor]
                    diff = abs(price - prev_price)
                    max_diff = delta * prev_price + 0.01 + 1e-5
                    assert diff <= max_diff, f"Price deviation error: price={price}, prev={prev_price}, diff={diff}, max_diff={max_diff}"
            
            # Constraint 5: Driver Earnings Fairness
            if status in ["Optimal", "Feasible"]:
                assert price <= T * (1.0 + fairness_tolerance) + 0.01 + 1e-5, f"Driver earnings {price} above fairness bound!"
                assert price >= T * (1.0 - fairness_tolerance) - 0.01 - 1e-5, f"Driver earnings {price} below fairness bound!"
        
        # Update price memory for the next window
        for rid, did, price in assignments:
            rider = rider_lookup[rid]
            corridor = (rider["origin_zone"], rider["dest_zone"])
            price_memory[corridor] = price
            
        print(f"Window {window_id} constraints: ALL PASSED")
        
    print("\n=== E2E Pipeline Verification COMPLETE: ALL CONSTRAINTS SATISFIED ===")
    return True


if __name__ == "__main__":
    try:
        run_e2e_pipeline()
        sys.exit(0)
    except AssertionError as err:
        print(f"\n[FAIL] E2E Verification failed: {err}")
        sys.exit(1)
