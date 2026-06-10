# Project Structure Guide: Oober (R4)

This guide maps out the layout, structural boundaries, and module responsibilities of the Oober repository. It is designed to help new engineers understand where components live and how they interface.

---

## 1. Repository Layout

The high-level repository directory map is shown below:

```
Oober/
├── .venv/                  # Python virtual environment (ignored in git)
├── docs/                   # System documentation
│   ├── audit-report.md     # R1: Audit report
│   ├── architecture.md     # R3: System architecture
│   ├── project-structure.md# R4: Project structure map (This document)
│   ├── contributing.md     # R5: Contributor standards
│   ├── development-guide.md# R5: Developer workflow guide
│   └── troubleshooting.md  # R5: Troubleshooting FAQ
├── frontend/               # Static single-page dashboard application
│   ├── css/                # CSS stylesheets (base, configuration, viewer, results)
│   │   ├── base.css
│   │   ├── config.css
│   │   ├── simulation.css
│   │   └── results.css
│   ├── js/                 # JavaScript modules and orchestrators
│   │   ├── api.js          # API client and response transformer
│   │   ├── app.js          # Main UI controller & resize handler
│   │   ├── charts.js       # Progressive line chart drawer
│   │   ├── city-graph.js   # D3.js City SVG visualizer
│   │   ├── config.js       # Config view validations and run control
│   │   ├── log.js          # Detailed simulation table log
│   │   ├── metrics.js      # Metric cards count-up animations
│   │   ├── playback.js     # Playback control loop & speed manager
│   │   └── simulation.js   # Simulation coordinator & event router
│   └── index.html          # Main HTML markup
├── oober/                  # Backend optimization engine python package
│   ├── __init__.py         # Package entry marker
│   ├── api.py              # FastAPI server definition and static mounts
│   ├── city_graph.py       # City network generation using NetworkX
│   ├── feasibility_filter.py # Bipartite feasibility mapping
│   ├── ilp_engine.py       # PuLP-based assignment & pricing ILP solver
│   ├── metrics.py          # Math calculations for simulation metrics
│   ├── sequential_baseline.py # Surge-then-match baseline engine
│   └── simulation.py       # Master simulation loops and generators
├── tests/                  # Backend verification suites and runners
│   ├── test_backend_api.py # FastAPI testclient unit tests
│   ├── test_metrics.py     # Math correctness tests for metrics
│   └── verify_backend.py   # Unified backend verify test runner
├── run.py                  # Server launch entry point
├── requirements.txt        # Backend dependencies
└── LICENSE                 # MIT License file
```

---

## 2. Directory & Module Responsibilities

### `oober/` (Python Engine)
- **`api.py`**: Exposes `/api/simulate` and `/api/health`. Directs parameters to the simulation runner and handles response JSON serialization. Mounts the `frontend/` directory to serve files at `http://localhost:8000/`.
- **`simulation.py`**: Implements the synthetic data generator (`generate_time_window_data`) and coordinates the multi-window simulation loop. Collects matching logs and serializes them.
- **`city_graph.py`**: Generates zone network configurations. It builds directed graphs and ensures strong connectivity by adding bridging edges where necessary.
- **`feasibility_filter.py`**: Filters out-of-bounds agent pairs (where a rider's willingness-to-pay is below a driver's minimum acceptable fare or travel cost is infinite).
- **`ilp_engine.py`**: Formulates and solves the assignment and pricing linear programming problem under price stability and driver fairness constraints.
- **`sequential_baseline.py`**: Implements the greedy comparator system, calculating surge pricing per corridor and greedily matching drivers.
- **`metrics.py`**: Implements performance metrics formulas.

### `frontend/` (Dashboard Client)
- **`index.html`**: Houses the skeleton markup and anchors D3 SVG containers, canvases, log panels, and control buttons.
- **`js/api.js`**: Integrates client-side logic with backend endpoints. Performs key transformations on simulation response data (e.g., nesting flat keys into `joint_opt` and `seq_baseline` models).
- **`js/city-graph.js`**: Handles D3 force-directed SVG nodes representing zone topologies and animates rider/driver agent markers and match lines.
- **`js/playback.js`**: Controls the step-wise progress of simulation windows. Integrates speed variables (0.5x to 4x) and tracks animation timelines.
- **`js/simulation.js`**: Orchestrates event routing between playback changes, graph updates, chart data additions, and logs.

---

## 3. Component & Dependency Boundaries

To preserve architectural integrity, adhere to these boundary rules:

- **API Boundary**: All client-server communication must occur via HTTP JSON transactions on `/api/simulate`. Do not write backend values or state directly to frontend files or rely on local caching.
- **Backend Coupling**: Do not import or mix engine logic across algorithms. `ilp_engine.py` and `sequential_baseline.py` must remain fully isolated; they only share the input data generated in `simulation.py`.
- **Frontend Namespace**: All frontend JavaScript modules must attach their functions under the global `window.OoberApp` namespace rather than declaring global scope variables.

---

## 4. Maintenance Guidelines

### Safe Areas to Modify
- **Frontend Modules (`frontend/js/` and `frontend/css/`)**: Safe to refactor or visual style without affecting the core optimization logic.
- **Documentation (`docs/`)**: Documenting new features, writing developer guides, or detailing benchmarks can be done freely.
- **Unit Tests (`tests/`)**: Highly encouraged to write more coverage for API endpoints, solvers, and metric validations.

### Areas Requiring Extra Caution
- **`oober/ilp_engine.py`**: The PuLP formulation is sensitive to constraint definitions. Adding constraints or modifying bounds might make the solver infeasible for default inputs.
- **`oober/simulation.py`**: Changing the RNG flow or offsets will alter simulation results, breaking existing unit tests that rely on fixed seeds.
- **`requirements.txt`**: Modifying package versions (especially NetworkX or PuLP) may result in deprecation warnings or API breaks.
