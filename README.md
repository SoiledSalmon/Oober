# Oober — Joint Price-and-Match Optimization in Ride-Hailing

**DAA PBL Project — RV College of Engineering, 2025-26**

Replaces the industry-standard sequential *surge-price-then-match* pipeline with a **single-pass Integer Linear Program (ILP)** that simultaneously finds optimal driver-rider assignments and prices, subject to wait-time efficiency, driver earnings fairness, and price stability constraints.

## Team & Module Status

| Person | Role | Files | Status |
|---|---|---|---|
| **Person A** | Algorithm Core | `feasibility_filter.py`, `ilp_engine.py` | ✅ Completed |
| **Person B** | Data & Baseline | `city_graph.py`, `simulation.py`, `sequential_baseline.py` | ✅ Completed |
| **Person C** | UI & Integration | `app.py`, `metrics.py` | ⏳ Pending (Stubs) |

## Setup

```bash
# Clone the repo
git clone https://github.com/SoiledSalmon/Oober.git
cd Oober

# Create and activate virtual environment
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Git Workflow

Each person works on their own branch:

```bash
# Person A:
git checkout -b feat/algorithm-core

# Person B:
git checkout -b feat/data-and-baseline

# Person C:
git checkout -b feat/ui-and-metrics
```

When done, open a Pull Request to merge into `main`.

## Running the Dashboard

```bash
cd oober
streamlit run app.py
```

## Project Structure

```
oober/
├── app.py                    # Streamlit dashboard (Person C - Stub)
├── city_graph.py             # Zone graph + travel cost queries (Person B - Complete)
├── feasibility_filter.py     # Two-sided acceptance filter (Person A - Complete)
├── ilp_engine.py             # Full ILP formulation via PuLP (Person A - Complete)
├── sequential_baseline.py    # SeqBaseline implementation (Person B - Complete)
├── simulation.py             # Synthetic data generator + harness (Person B - Complete)
└── metrics.py                # Evaluation metric calculations (Person C - Stub)
```

For detailed instructions on completing Person C's components and testing them, refer to the [Developer Implementation Guide](file:///D:/Coding%20Projects/College%20Era/Oober/docs/person_c_guide.md).

## Running Unit Tests

A unit test suite is available to verify the evaluation metric calculations. Run the tests using:

```bash
python -m unittest tests/test_metrics.py
```

## Quick Test Checklist

- [ ] `python -c "import pulp, networkx, streamlit, plotly"` — no import errors
- [ ] City graph builds without error on 10 zones (`python oober/city_graph.py`)
- [ ] Feasibility filter produces ~60% feasible pairs on 20-rider/20-driver instance
- [ ] ILP solves to `Optimal` status on 20-rider/20-driver instance
- [ ] Sequential baseline produces assignments on same input (`python oober/sequential_baseline.py`)
- [ ] Metric tests pass after Person C's implementation (`python -m unittest tests/test_metrics.py`)
- [ ] `streamlit run oober/app.py` opens in browser and all charts populate