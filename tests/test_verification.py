import unittest
import networkx as nx
import numpy as np
import sys
import os

# Ensure parent directory is in search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from oober.city_graph import build_city_graph, get_travel_cost
    from oober.feasibility_filter import build_feasibility_graph
    from oober.ilp_engine import solve_joint_opt
    from oober.metrics import compute_earnings_variance
except ImportError:
    from city_graph import build_city_graph, get_travel_cost
    from feasibility_filter import build_feasibility_graph
    from ilp_engine import solve_joint_opt
    from metrics import compute_earnings_variance


class TestVerification(unittest.TestCase):

    def setUp(self):
        self.city_graph = build_city_graph(num_zones=5, seed=42)

    def test_two_sided_feasibility(self):
        """1. Verifies build_feasibility_graph contains edges only when WTP >= MAF."""
        riders = [{"id": 0, "origin_zone": 0, "dest_zone": 2, "wtp": 50.0}]
        drivers = [
            {"id": 0, "current_zone": 1, "maf": 40.0},
            {"id": 1, "current_zone": 1, "maf": 60.0}
        ]
        
        G = build_feasibility_graph(riders, drivers, self.city_graph)
        
        # Rider 0 -> Driver 0 should exist (50 >= 40)
        self.assertTrue(G.has_edge(("rider", 0), ("driver", 0)))
        # Rider 0 -> Driver 1 should not exist (50 < 60)
        self.assertFalse(G.has_edge(("rider", 0), ("driver", 1)))
        
        # Verify edge attributes
        edge_data = G[("rider", 0)][("driver", 0)]
        self.assertEqual(edge_data["price_lb"], 40.0)
        self.assertEqual(edge_data["price_ub"], 50.0)
        self.assertEqual(edge_data["origin_zone"], 0)
        self.assertEqual(edge_data["dest_zone"], 2)
        expected_cost = get_travel_cost(self.city_graph, 1, 0)
        self.assertEqual(edge_data["travel_cost"], expected_cost)

    def test_assignment_uniqueness(self):
        """2. Verifies that no rider or driver is matched more than once."""
        riders = [
            {"id": 0, "origin_zone": 0, "dest_zone": 1, "wtp": 80.0},
            {"id": 1, "origin_zone": 1, "dest_zone": 2, "wtp": 80.0},
            {"id": 2, "origin_zone": 2, "dest_zone": 3, "wtp": 80.0}
        ]
        drivers = [
            {"id": 0, "current_zone": 0, "maf": 20.0},
            {"id": 1, "current_zone": 1, "maf": 20.0},
            {"id": 2, "current_zone": 2, "maf": 20.0}
        ]
        
        G = build_feasibility_graph(riders, drivers, self.city_graph)
        res = solve_joint_opt(G, price_memory={}, earnings_history={}, delta=1.0, fairness_tolerance=1.0)
        
        self.assertIn(res["solver_status"], ["Optimal", "Feasible"])
        
        matched_riders = set()
        matched_drivers = set()
        
        for r_id, d_id, _ in res["assignments"]:
            self.assertNotIn(r_id, matched_riders, f"Rider {r_id} matched multiple times!")
            self.assertNotIn(d_id, matched_drivers, f"Driver {d_id} matched multiple times!")
            matched_riders.add(r_id)
            matched_drivers.add(d_id)

    def test_driver_earnings_bounds(self):
        """3. Verifies that driver earnings stay within fairness limits relative to target midpoint."""
        riders = [
            {"id": 0, "origin_zone": 0, "dest_zone": 1, "wtp": 100.0},
            {"id": 1, "origin_zone": 1, "dest_zone": 2, "wtp": 100.0}
        ]
        drivers = [
            {"id": 0, "current_zone": 0, "maf": 80.0},
            {"id": 1, "current_zone": 1, "maf": 80.0}
        ]
        
        G = build_feasibility_graph(riders, drivers, self.city_graph)
        
        # Calculate target midpoint earnings T
        midpoints = [(data["price_lb"] + data["price_ub"]) / 2 for _, _, data in G.edges(data=True)]
        T = np.mean(midpoints)
        
        tol = 0.05  # ±5% tolerance
        res = solve_joint_opt(G, price_memory={}, earnings_history={}, delta=1.0, fairness_tolerance=tol)
        
        self.assertIn(res["solver_status"], ["Optimal", "Feasible", "Relaxed"])
        
        # Verify matched drivers earnings are within [T * (1 - tol), T * (1 + tol)]
        matched_drivers_earnings = {d_id: price for _, d_id, price in res["assignments"]}
        
        for d_id, earnings in matched_drivers_earnings.items():
            self.assertTrue(earnings <= T * (1 + tol) + 1e-5, f"Earnings {earnings} exceeded upper bound!")
            self.assertTrue(earnings >= T * (1 - tol) - 1e-5, f"Earnings {earnings} fell below lower bound!")

    def test_price_stability(self):
        """4. Verifies pricing stays within ±delta of corridor price memory."""
        riders = [{"id": 0, "origin_zone": 0, "dest_zone": 2, "wtp": 100.0}]
        drivers = [{"id": 0, "current_zone": 1, "maf": 20.0}]
        price_memory = {(0, 2): 50.0}
        delta = 0.10  # ±10%
        
        G = build_feasibility_graph(riders, drivers, self.city_graph)
        res = solve_joint_opt(G, price_memory=price_memory, earnings_history={}, delta=delta, fairness_tolerance=1.0)
        
        self.assertIn(res["solver_status"], ["Optimal", "Feasible"])
        self.assertEqual(len(res["assignments"]), 1)
        
        _, _, price = res["assignments"][0]
        # Price must be in [45.0, 55.0]
        self.assertTrue(price >= 50.0 * (1 - delta) - 1e-5)
        self.assertTrue(price <= 50.0 * (1 + delta) + 1e-5)

    def test_variance_calculation(self):
        """5. Verifies compute_earnings_variance is calculated only over matched drivers."""
        drivers = [{"id": 0}, {"id": 1}, {"id": 2}]
        assignments = [
            (0, 0, 40.0),
            (2, 2, 70.0)
        ]
        
        # Matched earnings: [40.0, 70.0], mean = 55.0, var = 225.0
        var = compute_earnings_variance(assignments, drivers)
        expected_var = float(np.var([40.0, 70.0], ddof=0))
        self.assertAlmostEqual(var, expected_var)
        
        # Test empty assignments returns 0.0
        var_empty = compute_earnings_variance([], drivers)
        self.assertEqual(var_empty, 0.0)


if __name__ == "__main__":
    unittest.main()
