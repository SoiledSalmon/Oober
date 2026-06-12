# Oober — Joint Price-and-Match Optimization in Ride-Hailing

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![FastAPI Backend](https://img.shields.io/badge/FastAPI-Backend-009688.svg)](https://fastapi.tiangolo.com)
[![HTML/JS Dashboard](https://img.shields.io/badge/HTML5-Frontend-orange.svg)](frontend/)

Oober is a ride-hailing optimization research platform comparing **Joint Optimization (JointOpt)** against the **Sequential Surge-then-Match Baseline (SeqBaseline)**. Developed as a **DAA PBL project at RV College of Engineering (2025–26)**.

Traditional ride-hailing platforms run pricing and matching as two separate sequential steps: first compute a surge multiplier, then greedily match riders to drivers. This two-stage approach is suboptimal because the matching stage has no visibility into how the prices it accepts will affect future corridor stability or driver earnings fairness. Oober replaces this pipeline with a **single-pass Integer Linear Program (ILP)** that solves assignment and pricing jointly, under explicit constraints for Willingness-to-Pay (WTP), Minimum Acceptable Fare (MAF), price stability across time windows, and driver earnings fairness.

---

## What This Is

Oober simulates a city divided into zones connected by a weighted graph. In each time window, a synthetic population of riders and drivers is generated. The platform then runs two solvers side-by-side:

- **JointOpt** — a single-pass ILP that simultaneously decides which rider-driver pairs to match *and* what price to charge each pair, subject to four classes of constraints.
- **SeqBaseline** — a two-stage greedy pipeline that first applies zone-level surge pricing, then greedily assigns riders to drivers, replicating the approach used by most commercial platforms.

The simulation accumulates metrics across windows and serves them to an interactive browser dashboard where users can explore the city graph animation, compare metrics in real time, and export per-window logs to CSV.

---

## Algorithm Overview

### JointOpt (ILP)

**Decision variables**
- `x[r,d] ∈ {0, 1}` — 1 if rider `r` is matched to driver `d`.
- `p[r,d] ≥ 0` — price charged for the match.

**Objective** (minimize total travel cost, with a large negative offset to prioritize coverage):
```
minimize  Σ (travel_cost[r,d] − 10 000) · x[r,d]
```

**Constraints**
1. **Matching uniqueness** — each rider is matched to at most one driver and vice versa.
2. **WTP/MAF feasibility** — the price must be within the rider's WTP and above the driver's MAF:
   `price_lb · x[r,d] ≤ p[r,d] ≤ price_ub · x[r,d]`
3. **Price stability** (corridor-level, parameterized by `delta`) — the price on a corridor must not deviate more than `delta` from the price charged in the previous window:
   `prev_price · (1 − δ) · x[r,d] ≤ p[r,d] ≤ prev_price · (1 + δ) · x[r,d]`
4. **Driver earnings fairness** (parameterized by `fairness_tolerance`) — each driver's total earnings must fall within a tolerance band around the average:
   `earnings[d] ∈ [target · (1 − τ) · assignments[d],  target · (1 + τ) · assignments[d]]`

If the ILP is infeasible under the current parameters, it is automatically retried with relaxed constraints (delta = 1.0, fairness_tolerance = 1.0). The solver is CBC via PuLP with a 30-second time limit per window.

### SeqBaseline (Surge-then-Match)

1. Compute a zone-level surge multiplier based on local supply-demand ratio.
2. Apply the multiplier to a base fare to produce a corridor price.
3. Greedily assign riders to the nearest available driver whose fare falls within the rider's WTP.

No global feasibility check is performed; riders whose WTP is below the surged price are simply unmatched.

---

## Key Results

The table below summarises expected metric trends across a typical 10-window simulation run (results vary by seed and parameter settings).

| Metric | JointOpt | SeqBaseline | Winner |
|---|---|---|---|
| Average Wait Time (total travel cost) | Lower | Higher | ✅ JointOpt |
| Driver Earnings Variance | Lower | Higher | ✅ JointOpt |
| Price Oscillation (deviation fraction) | Lower | Higher | ✅ JointOpt |
| Matching Rate (riders matched / total riders) | Higher | Lower | ✅ JointOpt |

JointOpt outperforms SeqBaseline across all four primary metrics because it jointly considers all constraints at once, avoiding the cascading sub-optimality of the two-stage greedy approach.

---

## Project Structure

```
Oober/
├── oober/                         # Python backend engine
│   ├── __init__.py                # Package exports
│   ├── api.py                     # FastAPI server & route handlers
│   ├── city_graph.py              # Zone graph construction (NetworkX)
│   ├── config.py                  # All configuration constants
│   ├── feasibility_filter.py      # Bipartite candidate-pair graph builder
│   ├── ilp_engine.py              # PuLP ILP formulation & solver (JointOpt)
│   ├── metrics.py                 # Metric calculations (wait time, variance, etc.)
│   ├── sequential_baseline.py     # Greedy surge-then-match engine (SeqBaseline)
│   ├── simulation.py              # Multi-window simulation orchestrator
│   ├── type_defs.py               # TypedDict definitions for structured data
│   └── types.py                   # Pydantic request/response models
├── frontend/                      # Single-page web dashboard
│   ├── index.html                 # Entry point
│   ├── css/                       # Glassmorphism styles
│   └── js/                        # Vanilla JS modules (app, D3 graph, charts, etc.)
├── tests/                         # Test suites
│   ├── verify_backend.py          # Unified test entry point
│   ├── test_backend_api.py        # FastAPI route integration tests
│   ├── test_metrics.py            # Metric formula unit tests
│   ├── test_verification.py       # End-to-end solver verification
│   ├── run_e2e_pipeline.py        # Full pipeline runner
│   └── run_behavioral_comparison.py  # JointOpt vs SeqBaseline comparison
├── docs/                          # Extended documentation
├── run.py                         # Server entry point
├── requirements.txt               # Pinned direct dependencies
├── LICENSE                        # MIT License
└── CONTRIBUTING.md                # Branch, commit, and PR conventions
```

---

## Setup

### Prerequisites
- Python 3.10 or higher
- Git

### Installation Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/SoiledSalmon/Oober.git
   cd Oober
   ```

2. **Create and activate a virtual environment**:

   *Windows PowerShell*:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   *Windows CMD*:
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate.bat
   ```

   *macOS / Linux*:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Running the Simulation

1. **Start the FastAPI server**:
   ```bash
   python run.py
   ```

2. **Open the dashboard**:
   Navigate to [http://localhost:8000](http://localhost:8000).

3. **Configure and run**:
   - Set the number of zones, riders, drivers, and time windows using the controls in the sidebar.
   - Adjust `delta` (price stability tolerance) and `fairness_tolerance` (driver earnings band).
   - Click **Run Simulation** to execute both solvers and animate the results.
   - Use **Export CSV** to download per-window metrics for further analysis.

### Parameter Reference

| Parameter | Default | Description |
|---|---|---|
| `num_zones` | 10 | Number of city zones in the graph |
| `num_riders` | 30 | Riders generated per time window |
| `num_drivers` | 20 | Drivers available per time window |
| `num_windows` | 5 | Number of sequential time windows to simulate |
| `delta` | 0.10 | Maximum allowed fractional price deviation across windows |
| `fairness_tolerance` | 0.30 | Allowed fractional earnings deviation from target per driver |
| `seed` | 42 | RNG seed for reproducible runs |

---

## Running Tests

```bash
# Full backend verification (runs all suites)
python tests/verify_backend.py

# API integration tests
pytest tests/test_backend_api.py

# Metric formula unit tests
pytest tests/test_metrics.py
```

---

## References

1. Yan, C., Zhu, H., Korolko, N., & Woodard, D. (2020). Dynamic pricing and matching in ride-hailing platforms. *Naval Research Logistics*, 67(8), 705–724.
2. Chen, M. K., & Sheldon, M. (2016). Dynamic pricing in a labor market: Surge pricing and flexible work on the Uber platform. *EC '16*.
3. Bimpikis, K., Candogan, O., & Saban, D. (2019). Spatial pricing in ride-sharing networks. *Operations Research*, 67(3), 744–769.
4. Özkan, E., & Ward, A. R. (2020). Dynamic matching for real-time ridesharing. *Stochastic Systems*, 10(1), 29–70.
5. Cachon, G. P., Daniels, K. M., & Lobel, R. (2017). The role of surge pricing on a service platform with self-scheduling capacity. *Manufacturing & Service Operations Management*, 19(3), 368–384.
6. Garg, N., & Ravi, R. (2021). Driver welfare and algorithmic fairness in dynamic matching. *arXiv:2105.11024*.
7. Lian, Z., & Zheng, S. (2021). Joint pricing and matching in on-demand platforms: An integer programming approach. *Operations Research Letters*, 49(4), 558–563.
8. Nikzad, A. (2022). Thickness and competition in ride-hailing markets. *Management Science*, 68(6), 4389–4409.
9. Jian, N., & Henderson, S. G. (2020). An introduction to simulation optimization. *Proceedings of the 2020 Winter Simulation Conference*.
10. Agrawal, S., & Devanur, N. (2015). Fast algorithms for online stochastic convex programming. *SODA '15*, 1405–1424.
11. Wolsey, L. A. (1998). *Integer Programming*. Wiley-Interscience.

---

## Team

| Name | USN |
|---|---|
| Manoj Gupta D B | 1RV24CD029 |
| Ananth G Karanth | 1RV24CD006 |
| Anurag G Kharvi | 1RV24CD010 |

RV College of Engineering, Bengaluru — DAA PBL Project, 2025–26.