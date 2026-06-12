"""
Unit tests for the FastAPI backend endpoints of the Oober JointOpt dashboard.

This module is part of the Oober joint price-and-match
optimisation system. It tests health check endpoints, parameter bounds,
validation errors, and solver fallback logic.
"""

import os
import sys
import unittest
from typing import Any
from unittest.mock import patch

# Adjust path to import oober
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from oober.api import app


class TestBackendAPI(unittest.TestCase):
    """Test suite for validating Oober FastAPI API endpoints and routing constraints."""

    def setUp(self) -> None:
        """Setup FastAPITestClient instance before each test run."""
        self.client = TestClient(app)

    def test_health_endpoint(self) -> None:
        """Verify that the health check endpoint returns 200 OK and valid JSON status."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/json")
        data = response.json()
        self.assertEqual(data, {"status": "ok"})

    def test_simulate_valid_parameters(self) -> None:
        """Verify that /api/simulate returns 200 OK and valid trace JSON
        for default/valid inputs.
        """
        payload = {
            "num_windows": 5,
            "delta": 0.10,
            "fairness_tolerance": 0.30,
            "num_zones": 5,
            "seed": 42,
        }
        response = self.client.post("/api/simulate", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/json")
        data = response.json()

        # Check trace structure
        self.assertIn("graph", data)
        self.assertIn("windows", data)
        self.assertIn("summary", data)

        # Check graph
        graph = data["graph"]
        self.assertIn("nodes", graph)
        self.assertIn("edges", graph)

        # Check windows length matches
        self.assertEqual(len(data["windows"]), 5)

        # Check summary structure
        summary = data["summary"]
        self.assertIn("wait_time_improvement_pct", summary)
        self.assertIn("earnings_variance_improvement_pct", summary)

    def test_simulate_boundary_parameters(self) -> None:
        """Verify that /api/simulate allows boundary values matching
        backend pydantic limits.
        """
        payloads = [
            # Minimum boundaries
            {
                "num_windows": 1,
                "delta": 0.01,
                "fairness_tolerance": 0.01,
                "num_zones": 3,
                "seed": 0,
            },
            # Maximum boundaries
            {
                "num_windows": 50,
                "delta": 1.0,
                "fairness_tolerance": 1.0,
                "num_zones": 30,
                "seed": 9999,
            },
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.post("/api/simulate", json=payload)
                self.assertEqual(response.status_code, 200)

    def test_simulate_invalid_num_windows(self) -> None:
        """Verify that num_windows bounds (1-50) are enforced, returning 422 JSON."""
        # Under limit
        response = self.client.post("/api/simulate", json={"num_windows": 0})
        self.assertEqual(response.status_code, 422)

        # Over limit
        response = self.client.post("/api/simulate", json={"num_windows": 51})
        self.assertEqual(response.status_code, 422)

    def test_simulate_invalid_delta(self) -> None:
        """Verify that delta bounds (0.01-1.0) are enforced, returning 422 JSON."""
        # Under limit
        response = self.client.post("/api/simulate", json={"delta": 0.009})
        self.assertEqual(response.status_code, 422)

        # Over limit
        response = self.client.post("/api/simulate", json={"delta": 1.01})
        self.assertEqual(response.status_code, 422)

    def test_simulate_invalid_fairness_tolerance(self) -> None:
        """Verify that fairness_tolerance bounds (0.01-1.0) are enforced,
        returning 422 JSON.
        """
        # Under limit
        response = self.client.post(
            "/api/simulate", json={"fairness_tolerance": 0.009}
        )
        self.assertEqual(response.status_code, 422)

        # Over limit
        response = self.client.post(
            "/api/simulate", json={"fairness_tolerance": 1.01}
        )
        self.assertEqual(response.status_code, 422)

    def test_simulate_invalid_num_zones(self) -> None:
        """Verify that num_zones bounds (3-30) are enforced, returning 422 JSON."""
        # Under limit
        response = self.client.post("/api/simulate", json={"num_zones": 2})
        self.assertEqual(response.status_code, 422)

        # Over limit
        response = self.client.post("/api/simulate", json={"num_zones": 31})
        self.assertEqual(response.status_code, 422)

    def test_simulate_invalid_seed(self) -> None:
        """Verify that seed must be >= 0, returning 422 JSON otherwise."""
        response = self.client.post("/api/simulate", json={"seed": -1})
        self.assertEqual(response.status_code, 422)

    @patch("oober.simulation.solve_joint_opt")
    def test_simulate_fallback_to_greedy(
        self, mock_solve_joint_opt: Any
    ) -> None:
        """Verify that if the ILP solver fails completely, it falls back to SeqBaseline.

        Args:
            mock_solve_joint_opt: The mocked solve_joint_opt function.
        """
        mock_solve_joint_opt.return_value = {
            "assignments": [],
            "total_wait_cost": 0.0,
            "matched_count": 0,
            "solver_status": "Infeasible",
            "solve_time_sec": 0.01,
        }

        payload = {
            "num_windows": 3,
            "delta": 0.10,
            "fairness_tolerance": 0.30,
            "num_zones": 5,
            "seed": 42,
        }
        response = self.client.post("/api/simulate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check that the solver status returned is "Fallback" for all windows
        for window in data["windows"]:
            self.assertEqual(window["joint_opt_solver_status"], "Fallback")
            # Should have baseline assignments copied to joint_opt
            self.assertEqual(
                window["joint_opt_assignments"],
                window["seq_baseline_assignments"],
            )
if __name__ == "__main__":
    unittest.main()
