# Troubleshooting FAQ: Oober (R5)

This guide covers common errors, environment setup issues, solver failures, and runtime bugs, along with their solutions.

---

## 1. Setup & Environment Issues

### `ImportError: cannot import name 'TestClient' from 'fastapi.testclient'`
- **Cause**: The `TestClient` from FastAPI relies on `httpx` to perform requests. If `httpx` is not installed, this import will fail.
- **Solution**: Install `httpx` via your package manager:
  ```bash
  pip install httpx
  ```
  Ensure it is registered in your virtual environment.

### `ModuleNotFoundError: No module named 'oober'`
- **Cause**: The Python path does not include the project root, or you are running tests from inside the `tests/` directory without adjusting Python paths.
- **Solution**: Run tests and commands from the project root directory. The verification scripts dynamically add `oober/` to `sys.path`. If you are running tests manually, set `PYTHONPATH`:
  - *Windows PowerShell*: `$env:PYTHONPATH="."`
  - *macOS/Linux*: `export PYTHONPATH="."`

---

## 2. Optimization & Solver Failures

### JointOpt Falls Back to Baseline (Solver Status: Fallback / Relaxed)
- **Cause**: The constraints are too tight. If you set Price Stability ($\delta$) very low and Fairness Tolerance low, and there is a high supply-demand mismatch, the solver cannot find any set of assignment prices that satisfies all constraints simultaneously. The system now handles this gracefully:
  1. It first relaxes constraints internally (sets delta = 1.0, fairness_tolerance = 1.0) and re-solves (status: `"Relaxed"`).
  2. If that still fails, it falls back to the sequential baseline (status: `"Fallback"`).
- **Solution**:
  - To see fully constrained JointOpt behavior, relax your input parameters in the configuration panel (increase $\delta$ to $0.10+$ and Fairness to $0.30+$).
  - Increase the number of City Zones or try a different seed.

### `pulp.apis.core.PulpSolverError: PuLP: cannot run default solver cbc`
- **Cause**: PuLP could not locate the default Coin-OR CBC solver binary for your platform.
- **Solution**: PuLP installs a bundled version of CBC for major operating systems. If it is missing:
  1. Re-install pulp: `pip install --force-reinstall pulp`
  2. If using Linux, install the system solver: `sudo apt-get install coinor-cbc`

---

## 3. Frontend Dashboard Runtime Issues

### Simulation Graph or Timelines Frozen / Glitched
- **Cause**: The D3.js force layout or Anime.js timelines are experiencing thrashing due to window resizing or duplicate animation intervals.
- **Solution**:
  - Click the **"← Config"** button to cleanly reset timelines and state.
  - Refresh the page to wipe out memory leaks or background intervals.
  - Check the browser Console (`F12`) to identify any uncaught JavaScript exceptions.

### Slider Labels Do Not Sync
- **Cause**: One of the slider DOM elements (`param-windows`, `param-delta`, etc.) is missing from the page layout or has a mismatching ID.
- **Solution**: Ensure your custom HTML page contains all necessary IDs mapped in `frontend/js/config.js` under the `init()` block.
