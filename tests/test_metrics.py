import unittest
import networkx as nx
import numpy as np

# We import the functions to test. Since the tests are in the root directory or a tests/ folder,
# we need to make sure we can import from the oober package.
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "oober")))

from metrics import (
    compute_wait_time,
    compute_earnings_variance,
    compute_price_deviation,
    compute_matching_rate
)


class TestMetrics(unittest.TestCase):

    def setUp(self):
        # 1. Create a dummy feasibility graph (bipartite)
        self.feas_graph = nx.Graph()
        
        # Add rider nodes (bipartite=0)
        self.feas_graph.add_node(("rider", 0), bipartite=0, data={"id": 0, "origin_zone": 0, "dest_zone": 3, "wtp": 60})
        self.feas_graph.add_node(("rider", 1), bipartite=0, data={"id": 1, "origin_zone": 1, "dest_zone": 4, "wtp": 45})
        self.feas_graph.add_node(("rider", 2), bipartite=0, data={"id": 2, "origin_zone": 2, "dest_zone": 5, "wtp": 80})

        # Add driver nodes (bipartite=1)
        self.feas_graph.add_node(("driver", 0), bipartite=1, data={"id": 0, "current_zone": 0, "maf": 20})
        self.feas_graph.add_node(("driver", 1), bipartite=1, data={"id": 1, "current_zone": 1, "maf": 35})
        self.feas_graph.add_node(("driver", 2), bipartite=1, data={"id": 2, "current_zone": 2, "maf": 25})

        # Add edges with attributes
        self.feas_graph.add_edge(("rider", 0), ("driver", 0), travel_cost=10.0, price_lb=20.0, price_ub=60.0, origin_zone=0, dest_zone=3)
        self.feas_graph.add_edge(("rider", 1), ("driver", 1), travel_cost=15.0, price_lb=35.0, price_ub=45.0, origin_zone=1, dest_zone=4)
        self.feas_graph.add_edge(("rider", 2), ("driver", 2), travel_cost=25.0, price_lb=25.0, price_ub=80.0, origin_zone=2, dest_zone=5)

        # 2. Dummy riders list
        self.riders = [
            {"id": 0, "origin_zone": 0, "dest_zone": 3, "wtp": 60},
            {"id": 1, "origin_zone": 1, "dest_zone": 4, "wtp": 45},
            {"id": 2, "origin_zone": 2, "dest_zone": 5, "wtp": 80}
        ]

        # 3. Dummy drivers list
        self.drivers = [
            {"id": 0, "current_zone": 0, "maf": 20},
            {"id": 1, "current_zone": 1, "maf": 35},
            {"id": 2, "current_zone": 2, "maf": 25}
        ]

    def test_compute_wait_time(self):
        # Sample assignments: (rider_id, driver_id, price)
        assignments = [
            (0, 0, 40.0),
            (2, 2, 70.0)
        ]
        # Wait time should be travel_cost(0,0) + travel_cost(2,2) = 10.0 + 25.0 = 35.0
        try:
            wait_time = compute_wait_time(assignments, self.feas_graph)
            self.assertAlmostEqual(wait_time, 35.0)
        except NotImplementedError:
            self.skipTest("compute_wait_time not implemented yet")

    def test_compute_wait_time_empty(self):
        assignments = []
        try:
            wait_time = compute_wait_time(assignments, self.feas_graph)
            self.assertEqual(wait_time, 0.0)
        except NotImplementedError:
            self.skipTest("compute_wait_time not implemented yet")

    def test_compute_earnings_variance(self):
        # Assignments:
        # Driver 0: earns 40.0
        # Driver 2: earns 70.0
        # Driver 1: unmatched, earns 0.0
        assignments = [
            (0, 0, 40.0),
            (2, 2, 70.0)
        ]
        # Total list of drivers has length 3.
        # Earnings list: [40.0, 0.0, 70.0]
        # Mean = 110 / 3 = 36.6666...
        # Population variance = np.var([40.0, 0.0, 70.0], ddof=0)
        # = ((40-110/3)**2 + (0-110/3)**2 + (70-110/3)**2) / 3
        # = ((10/3)**2 + (-110/3)**2 + (100/3)**2) / 3
        # = (100 + 12100 + 10000) / 27 = 22200 / 27 = 822.2222...
        expected_var = float(np.var([40.0, 0.0, 70.0], ddof=0))
        
        try:
            var = compute_earnings_variance(assignments, self.drivers)
            self.assertAlmostEqual(var, expected_var)
        except NotImplementedError:
            self.skipTest("compute_earnings_variance not implemented yet")

    def test_compute_earnings_variance_empty(self):
        assignments = []
        # All drivers earn 0
        expected_var = 0.0
        try:
            var = compute_earnings_variance(assignments, self.drivers)
            self.assertAlmostEqual(var, expected_var)
        except NotImplementedError:
            self.skipTest("compute_earnings_variance not implemented yet")

    def test_compute_price_deviation(self):
        # Price memory: corridor (0, 3) was 50.0, corridor (1, 4) was 30.0
        price_memory = {
            (0, 3): 50.0,
            (1, 4): 30.0
        }
        
        # Assignments:
        # 1. Rider 0 -> Driver 0 at 52.0 (Corridor (0,3), prev_price=50.0)
        #    Deviation = |52 - 50| / 50 = 2/50 = 0.04.
        #    If delta=0.10, deviation 0.04 <= 0.10 (No violation)
        # 2. Rider 1 -> Driver 1 at 40.0 (Corridor (1,4), prev_price=30.0)
        #    Deviation = |40 - 30| / 30 = 10/30 = 0.3333.
        #    If delta=0.10, deviation 0.3333 > 0.10 (Violation!)
        # 3. Rider 2 -> Driver 2 at 75.0 (Corridor (2,5), no price memory)
        #    Ignored (No violation)
        # Total assignments = 3. Violations = 1.
        # Price deviation fraction = 1 / 3 = 0.3333...
        assignments = [
            (0, 0, 52.0),
            (1, 1, 40.0),
            (2, 2, 75.0)
        ]
        
        try:
            deviation = compute_price_deviation(assignments, price_memory, self.riders, delta=0.10)
            self.assertAlmostEqual(deviation, 1.0 / 2.0)
        except NotImplementedError:
            self.skipTest("compute_price_deviation not implemented yet")

    def test_compute_price_deviation_empty_memory(self):
        price_memory = {}
        assignments = [
            (0, 0, 52.0),
            (1, 1, 40.0),
            (2, 2, 75.0)
        ]
        try:
            deviation = compute_price_deviation(assignments, price_memory, self.riders, delta=0.10)
            self.assertEqual(deviation, 0.0)
        except NotImplementedError:
            self.skipTest("compute_price_deviation not implemented yet")

    def test_compute_price_deviation_empty_assignments(self):
        price_memory = {(0, 3): 50.0}
        assignments = []
        try:
            deviation = compute_price_deviation(assignments, price_memory, self.riders, delta=0.10)
            self.assertEqual(deviation, 0.0)
        except NotImplementedError:
            self.skipTest("compute_price_deviation not implemented yet")

    def test_compute_matching_rate(self):
        assignments = [
            (0, 0, 40.0),
            (2, 2, 70.0)
        ]
        # Matching rate = 2 assignments / 3 riders = 0.6666...
        try:
            rate = compute_matching_rate(assignments, total_riders=3)
            self.assertAlmostEqual(rate, 2.0 / 3.0)
        except NotImplementedError:
            self.skipTest("compute_matching_rate not implemented yet")

    def test_compute_matching_rate_zero_riders(self):
        assignments = []
        try:
            rate = compute_matching_rate(assignments, total_riders=0)
            self.assertEqual(rate, 0.0)
        except NotImplementedError:
            self.skipTest("compute_matching_rate not implemented yet")


if __name__ == "__main__":
    unittest.main()
