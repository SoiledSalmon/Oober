import unittest
import sys
import os

# Adjust path to find oober (parent folder's oober directory)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "oober")))

from simulation import run_simulation_with_trace

def run_unit_tests():
    print("Running unittest suite...")
    loader = unittest.TestLoader()
    # Discover tests in the directory of this script (tests/)
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(tests_dir)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print(f"Tests run: {result.testsRun}, Errors: {len(result.errors)}, Failures: {len(result.failures)}")
    return result.wasSuccessful()

def run_simulation_checks():
    print("Running simulation checks...")
    try:
        res = run_simulation_with_trace(
            num_windows=5,
            delta=0.15,
            fairness_tolerance=0.25,
            num_zones=8,
            seed=123
        )
        assert "joint_opt" in res, "Missing joint_opt key"
        assert "seq_baseline" in res, "Missing seq_baseline key"
        assert "summary" in res, "Missing summary key"
        assert "graph" in res, "Missing graph key"
        assert "windows" in res, "Missing windows key"
        
        # Verify graph structure
        graph = res["graph"]
        assert "nodes" in graph and "edges" in graph, "Graph format mismatch"
        assert len(graph["nodes"]) == 8, f"Expected 8 nodes, got {len(graph['nodes'])}"
        
        # Verify windows structure
        windows = res["windows"]
        assert len(windows) == 5, f"Expected 5 windows, got {len(windows)}"
        for idx, win in enumerate(windows):
            assert "riders" in win, f"Window {idx} missing riders"
            assert "drivers" in win, f"Window {idx} missing drivers"
            assert "joint_opt_assignments" in win, f"Window {idx} missing joint_opt_assignments"
            assert "seq_baseline_assignments" in win, f"Window {idx} missing seq_baseline_assignments"
            assert "joint_opt_wait_time" in win, f"Window {idx} missing joint_opt_wait_time"
            assert "seq_baseline_wait_time" in win, f"Window {idx} missing seq_baseline_wait_time"
            
        print("Simulation checks passed successfully!")
        return True
    except Exception as e:
        print(f"Simulation check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    ut_ok = run_unit_tests()
    sim_ok = run_simulation_checks()
    if ut_ok and sim_ok:
        print("ALL BACKEND VERIFICATIONS PASSED!")
        sys.exit(0)
    else:
        print("SOME VERIFICATIONS FAILED!")
        sys.exit(1)
