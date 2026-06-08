# Implementation PRD — Joint Price-and-Match Optimization in Ride-Hailing
**Team:** Manoj Gupta D B · Ananth G Karanth · Anurag G Kharvi  
**Duration:** 2 Days (~8–12 total team hours)  
**Deliverable:** Working Python implementation + Streamlit web dashboard + simulation comparison vs. sequential baseline

---

## 1. Project Overview

We are implementing the `JointOpt` system described in the DAA PBL report. The system replaces the industry-standard sequential *surge-price-then-match* pipeline with a **single-pass Integer Linear Program (ILP)** that simultaneously finds the optimal driver-rider assignments and prices within a single optimization pass, subject to three constraints: wait-time efficiency, driver earnings fairness, and price stability across time windows.

The implementation must be **demonstrable** — a professor evaluating a live web dashboard will want to press a button, watch a simulation run, and see charts proving JointOpt outperforms the sequential baseline across all four metrics from the report.

---

## 2. Scope

### ✅ In Scope
- Full ILP formulation using PuLP (all four constraint sets as written in the report)
- Bipartite graph construction with two-sided feasibility filtering (NetworkX)
- City graph module with zone-based travel cost queries
- Time-window batch processing with price memory and earnings history
- Sequential surge-then-match baseline (SeqBaseline) for comparison
- Synthetic demand trace generator (calibrated WTP/MAF distributions)
- Streamlit web dashboard with parameter controls and results visualization
- Four evaluation metrics: wait time, earnings variance, price oscillation, matching rate

### ❌ Out of Scope
- Real-world data integration (Uber/Ola trip datasets)
- Live map visualization with actual geographic coordinates
- Greedy GNN-based approximate solver
- Multi-modal extensions (food delivery, pooling)
- Federated/privacy-preserving variants
- Full 30-run × 20-window experiment (we run fewer windows for demo speed; results still directionally valid)

---

## 3. Tech Stack

| Component | Library | Why |
|---|---|---|
| ILP Solver | `PuLP` + CBC | Exact ILP; CBC ships with PuLP, no extra install |
| Graph operations | `NetworkX` | Bipartite graph construction and matching utilities |
| Numerical ops | `NumPy`, `Pandas` | Data management, matrix operations |
| Web UI | `Streamlit` | Single-file app, runs in browser, zero front-end code needed |
| Charts | `Plotly` | Interactive charts that look professional in Streamlit |
| Dev | Python 3.10+ | Team familiar; type hints for clarity |

### Installation (run once)
```bash
pip install pulp networkx numpy pandas streamlit plotly
```

---

## 4. Folder Structure

```
ride_hailing_opt/
├── app.py                    # Streamlit dashboard (Person C owns)
├── city_graph.py             # Zone graph + travel cost queries (Person B owns)
├── feasibility_filter.py     # Two-sided acceptance filter (Person A owns)
├── ilp_engine.py             # Full ILP formulation via PuLP (Person A owns)
├── sequential_baseline.py    # SeqBaseline implementation (Person B owns)
├── simulation.py             # Synthetic data generator + harness (Person B owns)
├── metrics.py                # Evaluation metric calculations (Person C owns)
└── requirements.txt          # pip freeze output
```

Every file is **independently testable**. No file imports another at the top level except `app.py` which imports all of them. This means three people can write code simultaneously without blocking each other.

---

## 5. Module Specifications

Each specification below describes what the module does, its exact function signatures, and what its inputs/outputs are. This is the **contract** between team members — as long as everyone follows the signatures, the integration step is trivial.

---

### 5.1 `city_graph.py` — City Graph Module *(Person B)*

**Purpose:** Represents the service area as a weighted directed graph. Nodes are zones (e.g., Zone 0–9). Edge weights are travel costs (proxy for travel time). Exposes a travel cost query function used by the ILP engine to populate bipartite edge weights.

**What to implement:**

```python
import networkx as nx
import numpy as np

def build_city_graph(num_zones: int = 10, seed: int = 42) -> nx.DiGraph:
    """
    Creates a synthetic directed weighted city graph.
    Nodes: 0 to num_zones-1 (each representing a zone)
    Edges: randomly connected with travel cost weights in range [5, 50]
    Returns: nx.DiGraph with edge attribute 'cost'
    """

def get_travel_cost(graph: nx.DiGraph, origin_zone: int, dest_zone: int) -> float:
    """
    Returns shortest-path travel cost from origin_zone to dest_zone.
    Uses Dijkstra's algorithm (nx.shortest_path_length with weight='cost').
    Returns a large fallback cost (e.g., 999) if no path exists.
    """
```

**Key note:** In `build_city_graph`, make the graph reasonably dense (connect each node to ~3–5 others randomly) so that most zone-pairs have a valid path. Use `np.random.seed(seed)` for reproducibility.

---

### 5.2 `feasibility_filter.py` — Two-Sided Acceptance Filter *(Person A)*

**Purpose:** Implements the core two-sided acceptance constraint from the report. For every (rider, driver) candidate pair, checks whether there exists a price that satisfies both the rider's Willingness-To-Pay (WTP) and the driver's Minimum Acceptable Fare (MAF). If `MAF_d > WTP_r`, the pair is infeasible and discarded. Returns the bipartite graph of only feasible pairs.

**What to implement:**

```python
import networkx as nx

def build_feasibility_graph(
    riders: list[dict],       # each dict: {id, origin_zone, dest_zone, wtp}
    drivers: list[dict],      # each dict: {id, current_zone, maf}
    city_graph: nx.DiGraph
) -> nx.Graph:
    """
    Builds a bipartite graph G = (R ∪ D, E).
    
    Nodes:
      - Rider nodes labeled as ('rider', rider_id)
      - Driver nodes labeled as ('driver', driver_id)
    
    Edge (r, d) exists ONLY IF riders[r]['wtp'] >= drivers[d]['maf'].
    
    Edge attributes:
      - 'travel_cost': get_travel_cost(city_graph, driver.current_zone, rider.origin_zone)
      - 'price_lb': drivers[d]['maf']       # lower bound of feasible price interval
      - 'price_ub': riders[r]['wtp']         # upper bound of feasible price interval
    
    Returns: nx.Graph (bipartite)
    """
```

**Key note:** Mark nodes with the `bipartite` attribute (0 for riders, 1 for drivers) so NetworkX bipartite utilities work correctly.

---

### 5.3 `ilp_engine.py` — Joint ILP Optimizer *(Person A)*

**Purpose:** The heart of the project. Takes the feasibility graph and formulates a full ILP using PuLP. Solves it to get optimal (rider, driver, price) triples. Enforces all four constraint sets described in the report.

**What to implement:**

```python
import pulp
import networkx as nx

def solve_joint_opt(
    feasibility_graph: nx.Graph,
    price_memory: dict,         # {(origin_zone, dest_zone): last_price}
    earnings_history: dict,     # {driver_id: cumulative_earnings_so_far}
    delta: float = 0.10,        # stability threshold (10% of prev price)
    fairness_tolerance: float = 0.30,  # earnings range = ±30% of target
    window_id: int = 0
) -> dict:
    """
    Formulates and solves the joint ILP.
    
    Decision Variables:
      x_rd ∈ {0, 1}   — 1 if rider r assigned to driver d
      p_rd ∈ ℝ≥0      — price for pair (r,d); only meaningful when x_rd = 1
    
    Objective:
      Minimize Σ_{(r,d) ∈ E} travel_cost(r,d) * x_rd
    
    Constraints:
      [Assignment]  Σ_d x_rd ≤ 1   for all riders r
      [Assignment]  Σ_r x_rd ≤ 1   for all drivers d
      [Feasibility] p_rd ≥ price_lb(r,d) * x_rd   for all (r,d)
      [Feasibility] p_rd ≤ price_ub(r,d) * x_rd   for all (r,d)
      [Stability]   If price_memory has entry for (origin_r, dest_r):
                      p_rd ≥ (prev_price - delta * prev_price) * x_rd
                      p_rd ≤ (prev_price + delta * prev_price) * x_rd
      [Fairness]    earnings_d = Σ_r p_rd * x_rd   for each driver d
                    earnings_d ≤ target_earnings * (1 + fairness_tolerance) * Σ_r x_rd
                    earnings_d ≥ target_earnings * (1 - fairness_tolerance) * Σ_r x_rd
                    [where target_earnings = average of all feasible interval midpoints]
    
    Returns dict with keys:
      'assignments': list of (rider_id, driver_id, price) tuples
      'total_wait_cost': float
      'matched_count': int
      'solver_status': str  ('Optimal', 'Infeasible', etc.)
      'solve_time_sec': float
    """
```

**Key implementation notes for PuLP:**

```python
# Create the problem
prob = pulp.LpProblem("JointOpt", pulp.LpMinimize)

# Create variables
x = {}  # binary assignment variables
p = {}  # continuous price variables

for (r_node, d_node) in feasibility_graph.edges():
    rid = r_node[1]
    did = d_node[1]
    edge_data = feasibility_graph[r_node][d_node]
    
    x[(rid, did)] = pulp.LpVariable(f"x_{rid}_{did}", cat='Binary')
    p[(rid, did)] = pulp.LpVariable(f"p_{rid}_{did}", lowBound=0)

# Objective
prob += pulp.lpSum(
    feasibility_graph[r_node][d_node]['travel_cost'] * x[(r_node[1], d_node[1])]
    for (r_node, d_node) in feasibility_graph.edges()
)

# Then add constraints as described above, one block at a time.
# Solve:
prob.solve(pulp.PULP_CBC_CMD(msg=0))  # msg=0 suppresses solver output
```

**Fairness target computation:**
```python
# Compute target earnings as average midpoint of all feasible price intervals
all_midpoints = [
    (data['price_lb'] + data['price_ub']) / 2
    for _, _, data in feasibility_graph.edges(data=True)
]
target_earnings = np.mean(all_midpoints) if all_midpoints else 0
```

---

### 5.4 `sequential_baseline.py` — SeqBaseline *(Person B)*

**Purpose:** Implements the standard surge-then-match pipeline for comparison. Step 1: compute a single surge price per corridor based on demand-supply ratio. Step 2: greedily assign drivers to riders who can afford the surge price.

**What to implement:**

```python
def solve_sequential_baseline(
    riders: list[dict],
    drivers: list[dict],
    city_graph: nx.DiGraph,
    price_memory: dict
) -> dict:
    """
    Step 1 — Surge Pricing:
      For each unique (origin_zone, dest_zone) corridor in riders:
        demand = number of riders on that corridor
        supply = number of drivers within 2 zones of that corridor's origin
        surge_multiplier = max(1.0, demand / max(supply, 1))
        base_price = average MAF of all drivers
        surge_price[corridor] = base_price * surge_multiplier
    
    Step 2 — Greedy Matching:
      For each rider (sorted by WTP descending):
        corridor = (rider.origin_zone, rider.dest_zone)
        price = surge_price[corridor]
        If rider.wtp >= price:
          Find nearest available driver whose maf <= price
          Assign them; mark both as unavailable
    
    Returns same dict format as solve_joint_opt:
      'assignments': list of (rider_id, driver_id, price) tuples
      'total_wait_cost': float
      'matched_count': int
      'solver_status': 'Greedy'
      'solve_time_sec': float
    """
```

---

### 5.5 `simulation.py` — Simulation Harness *(Person B)*

**Purpose:** Generates synthetic demand traces and orchestrates the full multi-window simulation loop for both JointOpt and SeqBaseline. Collects per-window metrics.

**What to implement:**

```python
import numpy as np

def generate_time_window_data(
    num_riders: int,       # e.g., randomly between 15–30 per window
    num_drivers: int,      # e.g., randomly between 20–35 per window
    num_zones: int = 10,
    seed: int = None
) -> tuple[list[dict], list[dict]]:
    """
    Generates synthetic riders and drivers for one time window.
    
    Riders: each has {id, origin_zone, dest_zone, wtp}
      - origin_zone, dest_zone: random integers in [0, num_zones)
      - wtp: drawn from Normal(mean=50, std=15), clipped to [20, 100]
    
    Drivers: each has {id, current_zone, maf}
      - current_zone: random integer in [0, num_zones)
      - maf: drawn from Normal(mean=30, std=8), clipped to [10, 60]
    
    Note: calibrate so ~60-70% of (rider, driver) pairs are feasible
    (i.e., wtp >= maf for most pairs). The Normal distributions above
    achieve this since E[wtp]=50 > E[maf]=30.
    
    Returns: (riders_list, drivers_list)
    """

def run_simulation(
    num_windows: int = 10,      # use 10 for demo speed (report uses 20)
    riders_per_window: tuple = (15, 30),
    drivers_per_window: tuple = (20, 35),
    delta: float = 0.10,
    fairness_tolerance: float = 0.30,
    num_zones: int = 10,
    seed: int = 42
) -> dict:
    """
    Runs the full multi-window simulation for BOTH JointOpt and SeqBaseline.
    
    For each window t = 0, 1, ..., num_windows-1:
      1. Generate rider/driver data
      2. Build city graph (reuse same graph across windows)
      3. Run JointOpt → collect metrics
      4. Run SeqBaseline (same input data) → collect metrics
      5. Update price_memory and earnings_history from JointOpt results
    
    Returns dict:
      'joint_opt': {
          'wait_times': [float per window],
          'earnings_variances': [float per window],
          'price_deviations': [float per window],  # fraction of corridors exceeding delta
          'matching_rates': [float per window],
          'solve_times': [float per window]
      },
      'seq_baseline': {
          'wait_times': [...],
          'earnings_variances': [...],
          'price_deviations': [...],
          'matching_rates': [...],
          'solve_times': [...]
      },
      'summary': {
          'joint_opt_avg_wait': float,
          'seq_baseline_avg_wait': float,
          'wait_time_improvement_pct': float,
          ... (one entry per metric)
      }
    """
```

---

### 5.6 `metrics.py` — Evaluation Metrics *(Person C)*

**Purpose:** Pure calculation functions. Takes raw assignment output and computes the four evaluation metrics. No side effects, easy to unit test.

```python
def compute_wait_time(assignments: list[tuple], feasibility_graph) -> float:
    """Sum of travel_cost values for all matched (r, d) pairs."""

def compute_earnings_variance(assignments: list[tuple]) -> float:
    """
    For each driver in assignments, compute their total earnings (sum of prices).
    Return variance of per-driver earnings list.
    Drivers with no assignment contribute 0 earnings.
    """

def compute_price_deviation(
    assignments: list[tuple],
    price_memory: dict,
    riders: list[dict],
    delta: float
) -> float:
    """
    For each assignment (r, d, price), look up corridor = (rider.origin, rider.dest).
    If corridor exists in price_memory:
      Check if |price - prev_price| > delta * prev_price
    Return fraction of assignments that violate the delta threshold.
    """

def compute_matching_rate(assignments: list[tuple], total_riders: int) -> float:
    """Return len(assignments) / total_riders."""
```

---

### 5.7 `app.py` — Streamlit Dashboard *(Person C)*

**Purpose:** The demo interface. Runs in the browser. Lets the professor control parameters, run the simulation, and view results.

**UI Layout:**

```
┌─────────────────────────────────────────────────────────┐
│  SIDEBAR                  │  MAIN AREA                  │
│                           │                             │
│  Simulation Parameters    │  [Tab 1: Overview]          │
│  ─────────────────        │  Summary stats table        │
│  Time Windows: [10]       │  4 big metric cards         │
│  Delta (δ): [0.10]        │                             │
│  Fairness: [0.30]         │  [Tab 2: Charts]            │
│  Zones: [10]              │  4 line charts (per window) │
│  Seed: [42]               │   - Wait Time               │
│                           │   - Earnings Variance       │
│  [▶ Run Simulation]       │   - Price Oscillation       │
│                           │   - Matching Rate           │
│  Status: ✅ Complete      │                             │
│  Solve time: 1.2s avg     │  [Tab 3: Raw Data]          │
│                           │  Scrollable per-window df   │
└─────────────────────────────────────────────────────────┘
```

**Streamlit skeleton:**

```python
import streamlit as st
import plotly.graph_objects as go
from simulation import run_simulation

st.set_page_config(page_title="JointOpt Dashboard", layout="wide")
st.title("Joint Price-and-Match Optimization in Ride-Hailing")
st.caption("DAA PBL — RV College of Engineering, 2025-26")

# Sidebar controls
with st.sidebar:
    st.header("Simulation Parameters")
    num_windows = st.slider("Time Windows", 5, 20, 10)
    delta = st.slider("Price Stability δ", 0.05, 0.30, 0.10)
    fairness_tol = st.slider("Fairness Tolerance", 0.10, 0.50, 0.30)
    num_zones = st.slider("City Zones", 5, 15, 10)
    seed = st.number_input("Random Seed", value=42)
    run_btn = st.button("▶ Run Simulation", type="primary")

# Run simulation on button click, cache result in session state
if run_btn:
    with st.spinner("Running simulation..."):
        results = run_simulation(
            num_windows=num_windows, delta=delta,
            fairness_tolerance=fairness_tol, num_zones=num_zones, seed=seed
        )
        st.session_state['results'] = results

# Display results
if 'results' in st.session_state:
    results = st.session_state['results']
    tab1, tab2, tab3 = st.tabs(["Overview", "Charts", "Raw Data"])
    
    with tab1:
        # Show 4 metric cards using st.metric() with delta arrows
        col1, col2, col3, col4 = st.columns(4)
        summary = results['summary']
        col1.metric("Wait Time Reduction", 
                    f"{summary['wait_time_improvement_pct']:.1f}%", "vs SeqBaseline")
        # ... similar for other 3 metrics
    
    with tab2:
        # Show 4 Plotly line charts comparing JointOpt vs SeqBaseline per window
        windows = list(range(num_windows))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=windows, y=results['joint_opt']['wait_times'], 
                                  name='JointOpt', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=windows, y=results['seq_baseline']['wait_times'],
                                  name='SeqBaseline', line=dict(color='red', dash='dash')))
        fig.update_layout(title="Wait Time per Window", 
                          xaxis_title="Window", yaxis_title="Total Wait Cost")
        st.plotly_chart(fig, use_container_width=True)
        # ... similar for other 3 metrics
    
    with tab3:
        import pandas as pd
        # Build a dataframe with per-window data for both systems
        st.dataframe(pd.DataFrame({...}))
```

---

## 6. Data Contracts Between Modules

This table defines exactly what each module passes to the next. If everyone builds to this contract, integration is a 30-minute job.

| From | To | Data | Format |
|---|---|---|---|
| `simulation.py` | `feasibility_filter.py` | riders, drivers | `list[dict]` with keys `{id, origin_zone, dest_zone, wtp}` and `{id, current_zone, maf}` |
| `city_graph.py` | `feasibility_filter.py` | city graph | `nx.DiGraph` with edge attr `cost` |
| `feasibility_filter.py` | `ilp_engine.py` | bipartite graph | `nx.Graph` with edge attrs `travel_cost`, `price_lb`, `price_ub` |
| `ilp_engine.py` | `metrics.py` | result dict | `{'assignments': [(rid, did, price), ...], 'total_wait_cost': float, ...}` |
| `metrics.py` | `simulation.py` | per-window metrics | individual floats returned from each function |
| `simulation.py` | `app.py` | full results | `{'joint_opt': {...}, 'seq_baseline': {...}, 'summary': {...}}` |

**Critical:** The `assignments` list format is always `list[tuple[int, int, float]]` — `(rider_id, driver_id, price)`. Everyone must use exactly this format.

---

## 7. Work Division

### Person A — Algorithm Core [Status: ✅ COMPLETE]
**Files:** `feasibility_filter.py`, `ilp_engine.py`  
**Owns:** The two-sided acceptance constraint, the full ILP formulation, the PuLP setup.

This is the highest-risk, highest-reward role. The ILP is the core of the entire project. Use AI heavily to generate the PuLP constraint code — the specification in Section 5.3 above is detailed enough to prompt Claude or ChatGPT directly. The main skill needed here is careful testing: verify each constraint in isolation on a tiny example (3 riders, 3 drivers) before running the full simulation.

**Day 1 Goal:** `feasibility_filter.py` fully working and tested. ILP skeleton with assignment + feasibility constraints working.  
**Day 2 Goal:** Stability and fairness constraints added. Full `ilp_engine.py` working on 20-rider/driver instances.

---

### Person B — Data & Baseline [Status: ✅ COMPLETE]
**Files:** `city_graph.py`, `simulation.py`, `sequential_baseline.py`  
**Owns:** The city graph, the data generator, the baseline system, the simulation orchestration loop.

This is the most volume of files but each one is simpler than the ILP. The city graph is essentially a graph construction + Dijkstra call. The baseline is a greedy algorithm. The simulation harness is a for-loop calling the other modules. Person B can make progress even while Person A's ILP is still being debugged — write the simulation to accept a `solver_fn` parameter and test with mock results.

**Day 1 Goal:** `city_graph.py` done. `simulation.py` data generator done. Baseline skeleton working.  
**Day 2 Goal:** Full baseline working. Simulation loop running end-to-end with both solvers.

---

### Person C — UI & Integration [Status: ⏳ IN PROGRESS (Stubs Only)]
**Files:** `app.py`, `metrics.py`  
**Owns:** The Streamlit dashboard, all four metric calculations, final integration.

This role has the most flexibility. `metrics.py` can be built and tested on Day 1 with mock data. The Streamlit app layout can be built even before the simulation runs — just display placeholder data. On Day 2, Person C is the integrator: takes outputs from A and B, plugs them in, and makes the dashboard work end-to-end.

**Day 1 Goal:** `metrics.py` fully done and tested. Streamlit app layout built (with hardcoded placeholder data showing in charts).  
**Day 2 Goal:** Full integration — plug in real simulation results, charts populated, all 4 metric cards showing correct improvement percentages.

---

## 8. Day-by-Day Timeline

### Day 1 (~5 hours)

| Hour | Person A | Person B | Person C |
|---|---|---|---|
| 1 | **Setup:** Create repo, folder structure, install dependencies, shared `requirements.txt`. All three work together. | ← same → | ← same → |
| 2 | Write `feasibility_filter.py`. Test on 3-rider / 3-driver example. Verify bipartite graph edges correct. | Write `city_graph.py`. Build 10-zone graph, test `get_travel_cost()` for all zone pairs. | Write `metrics.py`. Test each function with hardcoded assignments. |
| 3 | Start `ilp_engine.py`: set up PuLP problem, add assignment constraints + feasibility constraints only (no stability/fairness yet). Test solve. | Write `simulation.py` data generator. Print sample riders/drivers to verify distributions look right. | Build Streamlit app skeleton. Sidebar controls + tabs layout. Display placeholder charts. |
| 4 | Add stability constraint to ILP. Test: verify that when prev_price = 40 and delta = 0.1, prices in [36, 44] only. | Write `sequential_baseline.py`. Test on same 3-rider/3-driver example used by A. | Add `st.session_state` result caching. Hook up button to call `run_simulation` (mock version). |
| 5 | Add fairness constraint. Verify full ILP solves on 10-rider/10-driver instance. | Write simulation loop skeleton. Wire up JointOpt and SeqBaseline calls. Run first full 3-window simulation. | Polish Streamlit layout. Add `st.metric()` cards. Confirm charts display data properly. |
| **EOD Check** | `feasibility_filter.py` ✅, `ilp_engine.py` solving 4/4 constraints. | `city_graph.py` ✅, `simulation.py` data gen ✅, baseline mostly done. | `metrics.py` ✅, Streamlit layout done, charts display placeholder data. |

---

### Day 2 (~5 hours)

| Hour | Person A | Person B | Person C |
|---|---|---|---|
| 1 | **Integration kickoff:** All three share code. Person C integrates modules. Fix any import/interface issues together. | ← same → | ← same → |
| 2 | Stress-test ILP on 30-rider/30-driver instance. Fix any solver crashes. Tune solver timeout. | Complete simulation loop. Ensure metrics are collected correctly per window for both systems. | Plug real `run_simulation()` into Streamlit. Debug any data format mismatches. |
| 3 | Implement adaptive δ relaxation: if matched_count < threshold, relax delta and re-solve. | Run 10-window simulation. Verify JointOpt outperforms SeqBaseline on all 4 metrics. | Build all 4 comparison charts (one per metric, JointOpt vs SeqBaseline per window). |
| 4 | Write short inline comments explaining each ILP constraint block. | Compute and store summary statistics (% improvement for each metric). | Add summary metric cards with delta arrows. Add `st.info()` boxes explaining what each metric means. |
| 5 | **Demo rehearsal:** All three do a dry run of the demo together. Fix any visual bugs or crashes. | ← same → | ← same → |
| **EOD Goal** | Full ILP stable, no crashes on demo inputs. | Simulation produces correct comparative results. | Dashboard runs end-to-end, all charts correct, looks professional. |

---

## 9. AI Prompting Guide

Since the team is using AI tools to generate code, use these prompts to get clean, working output. Always paste the relevant section from Section 5 (Module Specifications) as context.

**For `ilp_engine.py` ILP constraints:**
> "I'm implementing a joint ride-hailing optimization ILP using Python PuLP. Here is the exact specification: [paste Section 5.3]. Write the complete PuLP formulation including all four constraint sets. Use variable names x_rd for binary assignment and p_rd for price. Suppress solver output with `PULP_CBC_CMD(msg=0)`. Return a dict with keys: assignments, total_wait_cost, matched_count, solver_status, solve_time_sec."

**For `feasibility_filter.py`:**
> "Write a Python function using NetworkX that builds a bipartite graph of feasible rider-driver pairs. [paste Section 5.2 signature and docstring]. Riders are labeled ('rider', id) and drivers ('driver', id). Edge exists only if rider.wtp >= driver.maf. Edge attributes: travel_cost from city graph, price_lb = driver.maf, price_ub = rider.wtp."

**For `sequential_baseline.py`:**
> "Write a Python function for a sequential surge-then-match baseline. [paste Section 5.4]. Step 1 computes surge price per corridor based on demand/supply ratio. Step 2 greedily assigns drivers to affordable riders. Return the same dict format as the JointOpt solver."

**For Streamlit charts:**
> "Write Streamlit code using Plotly to display a line chart comparing two lists (joint_opt_values and seq_baseline_values) across time windows. Use blue for JointOpt and red-dashed for SeqBaseline. Add a title and axis labels. Use `st.plotly_chart(fig, use_container_width=True)`."

---

## 10. Quick Test Protocol

Before the demo, run through this checklist:

- [ ] `python -c "import pulp, networkx, streamlit, plotly"` — no import errors
- [ ] City graph builds without error on 10 zones
- [ ] Feasibility filter produces ~60% feasible pairs on 20-rider/20-driver instance
- [ ] ILP solves to `Optimal` status on 20-rider/20-driver instance
- [ ] Sequential baseline produces assignments on same input
- [ ] JointOpt matching rate ≥ SeqBaseline matching rate
- [ ] JointOpt wait time < SeqBaseline wait time
- [ ] `streamlit run app.py` opens in browser
- [ ] Button click triggers simulation and populates all charts
- [ ] All 4 metric cards show positive improvement percentages

---

## 11. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| ILP infeasible on some windows | Medium | Medium | Catch `pulp.LpStatus` and return empty assignments; SeqBaseline handles that window instead |
| ILP solve time > 10s per window | Medium | High | Reduce instance size to 20 riders/drivers; add `timeLimit=30` to CBC solver |
| Fairness constraint over-constrains (kills matches) | High | Medium | Widen `fairness_tolerance` to 0.50 in demo parameters |
| Stability constraint makes all pairs infeasible after a surge | Medium | Medium | Adaptive δ: if matching_rate < 0.4, double δ and re-solve |
| Integration fails Day 2 | Low | High | All functions have identical return dict format — only `app.py` needs to change |
| Streamlit crashes on large data | Low | Low | Cap simulation at 10 windows for demo; data volume is small |

---

## 12. Definition of Done

The project is complete when:

1. `streamlit run app.py` launches a dashboard in the browser without errors.
2. Pressing "Run Simulation" completes within 60 seconds and populates all four charts.
3. JointOpt outperforms SeqBaseline on all four metrics (wait time, earnings variance, price deviation, matching rate) in the simulation output.
4. All four ILP constraint types (assignment, feasibility, stability, fairness) are present and commented in `ilp_engine.py`.
5. The professor can adjust δ and fairness tolerance via sliders and re-run to see how constraints affect results.
6. Code is organized in the defined folder structure with no single-file monolith.
