# Oober — Joint Price-and-Match Optimization in Ride-Hailing

**DAA PBL Project — RV College of Engineering, 2025-26**

Replaces the industry-standard sequential *surge-price-then-match* pipeline with a **single-pass Integer Linear Program (ILP)** that simultaneously finds optimal driver-rider assignments and prices, subject to wait-time efficiency, driver earnings fairness, and price stability constraints.

## Team

| Person | Role | Files |
|---|---|---|
| **Person A** | Algorithm Core | `feasibility_filter.py`, `ilp_engine.py` |
| **Person B** | Data & Baseline | `city_graph.py`, `simulation.py`, `sequential_baseline.py` |
| **Person C** | UI & Integration | `app.py`, `metrics.py` |

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
├── app.py                    # Streamlit dashboard (Person C)
├── city_graph.py             # Zone graph + travel cost queries (Person B)
├── feasibility_filter.py     # Two-sided acceptance filter (Person A)
├── ilp_engine.py             # Full ILP formulation via PuLP (Person A)
├── sequential_baseline.py    # SeqBaseline implementation (Person B)
├── simulation.py             # Synthetic data generator + harness (Person B)
└── metrics.py                # Evaluation metric calculations (Person C)
```

## Quick Test Checklist

- [ ] `python -c "import pulp, networkx, streamlit, plotly"` — no import errors
- [ ] City graph builds without error on 10 zones
- [ ] Feasibility filter produces ~60% feasible pairs on 20-rider/20-driver instance
- [ ] ILP solves to `Optimal` status on 20-rider/20-driver instance
- [ ] Sequential baseline produces assignments on same input
- [ ] `streamlit run app.py` opens in browser and all charts populate