# Oober — Joint Price-and-Match Optimization in Ride-Hailing

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![FastAPI Backend](https://img.shields.io/badge/FastAPI-Backend-009688.svg)](https://fastapi.tiangolo.com)
[![HTML/JS Dashboard](https://img.shields.io/badge/HTML5-Frontend-orange.svg)](frontend/)

Oober is a ride-hailing optimization research platform comparing Joint Optimization vs. Sequential Surge-then-Match methodologies. Developed as a **DAA PBL Project at RV College of Engineering (2025-26)**.

The system replaces the traditional sequential *surge-price-then-match* pipeline (greedy baseline) with a **single-pass Integer Linear Program (ILP)**. The Joint Optimization model (`JointOpt`) simultaneously solves driver-rider assignments and pricing in a single mathematical pass, minimizing wait times while enforcing constraints for price stability across time windows and driver earnings fairness.

---

## 🚀 Key Features

- **Joint Price-and-Match Optimization (ILP)**: A unified solver formulated via PuLP that solves assignment and pricing simultaneously.
- **Sequential Surge-then-Match Baseline**: Represents standard industry pipelines for comparative benchmark analysis.
- **High-Fidelity Simulation & RNG Reproducibility**: Seed-based generation of city zones, passenger demands, and driver capacities.
- **Interactive Glassmorphism Dashboard**: Fully animated city graph simulation (D3.js), count-up metric cards, real-time charts (Chart.js), and detailed execution logs.
- **CSV Data Exporter**: Instant client-side download of per-window simulation logs for further research analysis.

---

## 🛠️ System Architecture Summary

The project utilizes a client-server architecture:
- **Backend (Python 3.10+)**: Built with FastAPI. Optimization models use NetworkX for city graphs and PuLP (using standard Coin-OR CBC or alternative solver packages) for Integer Linear Programs.
- **Frontend (HTML/JS/CSS)**: Pure Vanilla JS modules communicating via REST API (`POST /api/simulate`). Visualizations are driven by D3.js and Anime.js.

For detailed architecture patterns and sequence flow, see the [System Architecture Guide](file:///D:/Coding%20Projects%20/College%20Era/Oober/docs/architecture.md).

---

## ⚙️ Setup and Installation

### Prerequisites
- Python 3.10 or higher
- Git

### Installation Steps

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/SoiledSalmon/Oober.git
   cd Oober
   ```

2. **Create and Activate Virtual Environment**:
   - **Windows PowerShell**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - **Windows CMD**:
     ```cmd
     python -m venv .venv
     .venv\Scripts\activate.bat
     ```
   - **macOS/Linux**:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Quick Start (Running Oober)

1. **Start the FastAPI Server**:
   ```bash
   python run.py
   ```
2. **Access the Dashboard**:
   Open [http://localhost:8000](http://localhost:8000) in your web browser. 

---

## 🧪 Testing & Verification

A unified test execution script is provided inside the tests directory:
```bash
python tests/verify_backend.py
```
This runs:
1. **API Endpoints Test Suite**: Verifies routing, parameter validation, and boundary conditions.
2. **Metrics Formulas Test Suite**: Validates mathematical calculations for wait time, earnings variance, price deviation, and matching rates.
3. **Simulation Integration Test**: Checks end-to-end integration and data serialization.

---

## 📁 Repository Map

```
Oober/
├── oober/                  # Python backend engine
│   ├── api.py              # FastAPI server & route handlers
│   ├── simulation.py       # Simulation harness & generator loops
│   ├── ilp_engine.py       # PuLP linear program formulation
│   ├── sequential_baseline.py # Greedy surge-then-match engine
│   └── metrics.py          # Metric calculations
├── frontend/               # Single-page web dashboard
│   ├── css/                # Visual styles & glassmorphism layout
│   └── js/                 # JS modules (app, D3 graph, charts, config, playback)
├── tests/                  # Test suites and runners
│   ├── test_backend_api.py # FastAPI route validations
│   ├── test_metrics.py     # Math formula verifications
│   └── verify_backend.py   # Unified test verification entry point
└── docs/                   # Platform documentation
```

---

## 📚 Detailed Documentation Index

For deep dives into the project components, refer to these guides:
- [Repository Audit Report (docs/audit-report.md)](file:///D:/Coding%20Projects/College%20Era/Oober/docs/audit-report.md) - Details code health, priority findings, and remediation.
- [System Architecture Guide (docs/architecture.md)](file:///D:/Coding%20Projects/College%20Era/Oober/docs/architecture.md) - Reviews design patterns, component dependencies, and sequence diagrams.
- [Project Structure Map (docs/project-structure.md)](file:///D:/Coding%20Projects/College%20Era/Oober/docs/project-structure.md) - Maps repository boundaries, ownership, and maintenance safety guidelines.
- [Contributing Standards (docs/contributing.md)](file:///D:/Coding%20Projects/College%20Era/Oober/docs/contributing.md) - Details setup instructions, coding conventions, and PR workflows.
- [Developer & Workflows Guide (docs/development-guide.md)](file:///D:/Coding%20Projects/College%20Era/Oober/docs/development-guide.md) - Contains deep concepts, math specifications, and debugger guidelines.
- [Troubleshooting FAQ (docs/troubleshooting.md)](file:///D:/Coding%20Projects/College%20Era/Oober/docs/troubleshooting.md) - Resolves common setup issues, solver errors, and runtime failures.