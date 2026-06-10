# Repository Audit Report: Oober (R1)

**Date:** June 10, 2026  
**Auditor:** explorer_audit_1  

---

## 1. Executive Summary

A comprehensive repository audit of Oober was performed to evaluate its backend, frontend, dependencies, and documentation. The project is an optimization platform that replaces sequential surge-price-then-match pipelines with a Joint Optimization Integer Linear Program (`JointOpt`). 

The codebase is generally well-structured and implements custom visual graphs and canvas-based charting components. However, several critical issues were identified:
1. **Critical Documentation Drift:** The `README.md` and `docs/DEVELOPER.md` describe a Streamlit-based interface run via `streamlit run oober/app.py` that no longer exists. The application has been fully refactored into a FastAPI backend with a static web frontend.
2. **Hard Constraints & Solver Infeasibility:** The ILP formulation treats price stability and driver fairness as hard constraints. Over-constraining these parameters causes the solver to fail, yielding zero rider-driver matches rather than falling back gracefully.
3. **Significant Logic Duplication:** The simulation harness in `oober/simulation.py` contains ~200+ lines of duplicated code across two nearly identical execution loops.
4. **Dead Code & Inconsistencies:** The frontend contains substantial dead code (~190 lines of a mock data generator), and there are validation limit mismatches between the frontend and backend.

---

## 2. Findings Ranked by Priority

### High Priority

#### H1: Severe Documentation Drift (Streamlit vs. FastAPI/HTML UI)
* **Location:** `README.md` (lines 5, 63–69, 79–89), `docs/DEVELOPER.md` (lines 103, 153–155, 165, 171, 201)
* **Observation:** The documentation directs developers to run `streamlit run oober/app.py`. However, `oober/app.py` is absent, `streamlit` is not in `requirements.txt`, and the application actually uses a FastAPI backend (`oober/api.py` / `run.py`) and a static HTML/JS frontend (`frontend/`).
* **Impact:** Prevents new users and developers from running the application or onboarding correctly.

#### H2: ILP Solver Hard Constraints & Fallback Absence
* **Location:** `oober/ilp_engine.py` (lines 190–205, 253–265) and `oober/simulation.py` (lines 249–256, 451–457)
* **Observation:** The stability and fairness tolerances are enforced as hard constraints. When constraints are tight or supply-demand mismatch is high, the PuLP solver status is `"Infeasible"` or `"Undefined"`. The simulator handles this by clearing all assignments, resulting in zero matches.
* **Impact:** System robustness is low; in production, this would cause complete service outages (zero matches) under tight parameter configurations.

---

### Medium Priority

#### M1: Code Duplication in Simulation Harness
* **Location:** `oober/simulation.py`
* **Observation:** `run_simulation` (lines 128–347) and `run_simulation_with_trace` (lines 350–564) are nearly identical (~200+ lines of duplicated logic). They run the same loop, generate the same data, and call the same solvers and metrics. The only difference is that the latter returns trace data for the frontend.
* **Impact:** Poor maintainability. Any updates to the simulation logic (such as bug fixes or metric updates) must be duplicated in both methods.

#### M2: Parameter Validation Range Mismatch
* **Location:** `frontend/js/config.js` (lines 83–102) vs. `oober/api.py` (lines 27–31)
* **Observation:** The validation limits for simulation parameters are inconsistent:
  * `num_windows`: Frontend allows 5–20 vs. Backend allows 1–50.
  * `delta`: Frontend allows 0.05–0.30 vs. Backend allows 0.01–1.0.
  * `fairness_tolerance`: Frontend allows 0.10–0.50 vs. Backend allows 0.01–1.0.
  * `num_zones`: Frontend allows 5–15 vs. Backend allows 3–30.
* **Impact:** Confusing developer and user experience. The backend allows a much wider, more flexible range of parameters than the frontend UI exposes.

#### M3: Dead Code in Frontend API module
* **Location:** `frontend/js/api.js` (lines 120–310)
* **Observation:** The `generateMockData` function (190 lines of JavaScript) is defined and exported as `window.OoberApp.api.generateMockData` but is never imported, invoked, or referenced anywhere else in the project.
* **Impact:** Increases frontend bundle size and clutters the codebase with dead logic.

---

### Low Priority

#### L1: Unused Dependency in `requirements.txt`
* **Location:** `requirements.txt` (line 4)
* **Observation:** `pandas` is declared in the requirements but is never imported or used in the backend codebase (`oober/`) or test suite (`tests/`).
* **Impact:** Unnecessary package installation, increasing container/environment build times.

#### L2: Missing Testing Dependency in `requirements.txt`
* **Location:** `requirements.txt` (none), `tests/test_backend_api.py` (line 4)
* **Observation:** `TestClient` from `fastapi.testclient` requires `httpx` to function. `httpx` is not declared in `requirements.txt`.
* **Impact:** Running backend API tests will fail with `ImportError` if `httpx` is not transitively installed in the environment.

#### L3: Unused Backend Imports
* **Location:** `verify_backend.py` (lines 5, 6, 11)
* **Observation:** `networkx` (`nx`), `numpy` (`np`), and all metrics functions (`compute_wait_time`, etc.) are imported but never used in the script.
* **Impact:** Minor code clutter.

#### L4: Unused Backend Function Parameters
* **Location:** `oober/ilp_engine.py` (line 15) and `oober/sequential_baseline.py` (line 41)
* **Observation:** 
  * `solve_joint_opt` takes `earnings_history` and `window_id` as arguments but does not use them in its body.
  * `solve_sequential_baseline` takes `price_memory` as an argument but does not use it.
* **Impact:** Minor architectural drift.

#### L5: Typo in Metrics Test Comments
* **Location:** `tests/test_metrics.py` (line 125)
* **Observation:** The comment states `"Total assignments = 3. Violations = 1. Price deviation fraction = 1 / 3 = 0.3333..."` but the code asserts `1.0 / 2.0` (0.5), which is correct since only two assignments are checked (the third lacks price memory).
* **Impact:** Minor documentation confusion in the test suite.

---

## 3. Recommended Remediation Order

To address these findings systematically, the following remediation plan is proposed:

1. **Phase 1: Critical Fixes & Documentation (High Priority)**
   * **Update README.md & DEVELOPER.md:** Replace Streamlit setup/execution instructions with FastAPI/Uvicorn instructions (`python run.py` or running uvicorn directly). Remove references to `app.py`.
   * **Introduce ILP Fallback Mechanism:** Refactor the simulator to fall back to the sequential baseline or a relaxed version of the ILP if the solver fails to find an optimal solution due to over-constraining.

2. **Phase 2: Code Quality & Consistency (Medium Priority)**
   * **Refactor Simulation Harness:** Consolidate the duplicate loops in `run_simulation` and `run_simulation_with_trace` by moving the core simulation logic into a single internal helper (e.g. `_execute_simulation_loop`) that both public functions call.
   * **Align Validation Ranges:** Sync the validation limits in `frontend/js/config.js` and `oober/api.py`.
   * **Prune Dead JS Code:** Remove `generateMockData` from `frontend/js/api.js`.

3. **Phase 3: Clean up Dependencies & Code Clutter (Low Priority)**
   * **Clean requirements.txt:** Remove `pandas` and add `httpx` (as a test dependency).
   * **Clean Backend Code:** Remove the unused imports in `verify_backend.py` and the unused parameters in the solver signatures, and fix the typo in `tests/test_metrics.py`.
