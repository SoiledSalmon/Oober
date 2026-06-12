# Project: Oober Simulator Optimization & Hygiene

## Architecture
Oober is a joint price-and-match simulator that compares a joint optimization approach (JointOpt, formulated as an ILP) against a sequential baseline (SeqBaseline, surge pricing followed by matching).

### Component Map:
- `oober/config.py`: Handles configuration loading, simulation constants, and parameters.
- `oober/city_graph.py`: Generates the city grid (graph), calculates shortest paths, travel times, and distances.
- `oober/feasibility_filter.py`: Determines which driver-rider matchings are feasible under time/distance limits.
- `oober/ilp_engine.py`: Encodes and solves the Integer Linear Program (ILP) for simultaneous rider-driver matching and pricing.
- `oober/sequential_baseline.py`: Runs the traditional surge-then-match pipeline.
- `oober/simulation.py`: Manages the overall simulation loop, time-stepping, demand generation, driver movements, and statistics gathering.
- `oober/metrics.py`: Computes evaluative metrics (rider wait times, driver earnings, price oscillation, matching rates).
- `oober/api.py`: Serves as the interface/wrapper for the simulator (Streamlit dashboard and backend APIs).

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | R1 Project Audit | Run codebase audit, identify missing docstrings, types, dead code, untracked files, hardcoded parameters | none | DONE |
| 2 | R2 Dead Code & Hygiene | Delete confirmed dead code, update `.gitignore`, remove cached files, extract hardcoded values | M1 | DONE |
| 3 | R3 Docstrings & Type Annotations | Add Google-style docstrings, Notes sections for ILP formulation, and PEP 484 type annotations | M2 | DONE |
| 4 | R4 Code Cleanup | Consistent formatting (Black), sort imports (isort), naming consistency (UPPER_SNAKE_CASE, etc.), remove commented-out code | M3 | DONE |
| 5 | R5 Architectural Review | Conduct review of `oober/` directories, categorize/log smells, fix low-risk issues, document deferred ones | M4 | IN_PROGRESS (Conv: 35f11256-7c26-44af-9b27-d01aaae88b25) |
| 6 | R6 GitHub Repository Files | Create/update README.md, requirements.txt, LICENSE, and CONTRIBUTING.md | M5 | PLANNED |
| 7 | Verification & Reporting | Run and verify verify_backend, test_backend_api, test_metrics; generate final verification report | M6 | PLANNED |

## Interface Contracts
- To be refined and finalized after R1 Project Audit.
