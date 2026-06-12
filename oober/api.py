"""
Exposes the FastAPI web endpoints for running the Oober simulation.

This module is part of the Oober joint price-and-match
optimisation system. It defines the HTTP entrypoints and request payload schemas
to interface the backend simulation with the frontend dashboard.
"""

import os
import sys
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Constants
PATH_INSERT_INDEX = 0  # Position in sys.path to insert module search path
DEFAULT_NUM_WINDOWS = 10  # Default number of time windows to simulate
MAX_NUM_WINDOWS = 50  # Maximum allowable time windows for simulation validation
DEFAULT_DELTA = 0.10  # Default price stability corridor tolerance
DEFAULT_FAIRNESS_TOLERANCE = 0.30  # Default driver earnings fairness tolerance
STATIC_PARENT_DIR = ".."  # Parent directory path component for static files
STATIC_TARGET_DIR = "frontend"  # Target directory name containing static assets

# Allow sibling-module imports (city_graph, ilp_engine, etc.) for FastAPI.
sys.path.insert(PATH_INSERT_INDEX, os.path.dirname(os.path.abspath(__file__)))

try:
    from .simulation import run_simulation_with_trace
except ImportError:
    from simulation import run_simulation_with_trace

__all__ = ["app"]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SimulationRequest(BaseModel):
    """Parameters accepted by the /api/simulate endpoint.

    Attributes:
        num_windows: Number of time windows to simulate.
        delta: Price stability threshold (δ).
        fairness_tolerance: Earnings fairness tolerance.
        num_zones: Number of city zones.
        seed: Random seed for reproducibility.
    """

    num_windows: int = Field(
        default=DEFAULT_NUM_WINDOWS,
        ge=1,
        le=MAX_NUM_WINDOWS,
        description="Number of time windows to simulate",
    )
    delta: float = Field(
        default=DEFAULT_DELTA,
        ge=0.01,
        le=1.0,
        description="Price stability threshold (δ)",
    )
    fairness_tolerance: float = Field(
        default=DEFAULT_FAIRNESS_TOLERANCE,
        ge=0.01,
        le=1.0,
        description="Earnings fairness tolerance",
    )
    num_zones: int = Field(
        default=10, ge=3, le=30, description="Number of city zones"
    )
    seed: int = Field(
        default=42, ge=0, description="Random seed for reproducibility"
    )


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Oober JointOpt API",
    description="Simulation API for comparing JointOpt vs SeqBaseline in ride-hailing.",
    version="2.0.0",
)

# CORS — allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/api/simulate")
def simulate(request: SimulationRequest) -> dict[str, Any]:
    """Run the multi-window simulation and return full trace data.

    Args:
        request: The parameters for configuring the simulation.

    Returns:
        dict[str, Any]: Compiled simulation results and trace data.
    """
    result = run_simulation_with_trace(
        num_windows=request.num_windows,
        delta=request.delta,
        fairness_tolerance=request.fairness_tolerance,
        num_zones=request.num_zones,
        seed=request.seed,
    )
    return result


@app.get("/api/health")
def health() -> dict[str, str]:
    """Simple health-check endpoint.

    Returns:
        dict[str, str]: A dictionary indicating backend health status.
    """
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Static files — mount frontend/ at root (must come AFTER API routes)
# ---------------------------------------------------------------------------

_frontend_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    STATIC_PARENT_DIR,
    STATIC_TARGET_DIR,
)
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
