"""
FastAPI backend for the Oober JointOpt Dashboard.

Serves the simulation API and static frontend files.
"""

import sys
import os

# Allow sibling-module imports (city_graph, ilp_engine, etc.) the same way
# the old Streamlit app.py did.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from simulation import run_simulation_with_trace

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SimulationRequest(BaseModel):
    """Parameters accepted by the /api/simulate endpoint."""
    num_windows: int = Field(default=10, ge=1, le=50, description="Number of time windows to simulate")
    delta: float = Field(default=0.10, ge=0.01, le=1.0, description="Price stability threshold (δ)")
    fairness_tolerance: float = Field(default=0.30, ge=0.01, le=1.0, description="Earnings fairness tolerance")
    num_zones: int = Field(default=10, ge=3, le=30, description="Number of city zones")
    seed: int = Field(default=42, ge=0, description="Random seed for reproducibility")


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
def simulate(request: SimulationRequest):
    """
    Run the multi-window simulation and return full trace data.

    Returns the same structure as ``run_simulation()`` plus:
    - ``graph``: city-graph topology (nodes + edges)
    - ``windows``: per-window riders, drivers, and assignments
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
def health():
    """Simple health-check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Static files — mount frontend/ at root (must come AFTER API routes)
# ---------------------------------------------------------------------------

_frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
