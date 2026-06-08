"""
Streamlit Dashboard (Person C)

The demo interface. Runs in the browser. Lets the professor control parameters,
run the simulation, and view results with interactive charts.

Run with:
    streamlit run app.py
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from simulation import run_simulation


# ── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="JointOpt Dashboard",
    page_icon="🚗",
    layout="wide",
)

st.title("Joint Price-and-Match Optimization in Ride-Hailing")
st.caption("DAA PBL — RV College of Engineering, 2025-26")


# ── Sidebar Controls ────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Simulation Parameters")

    num_windows = st.slider("Time Windows", 5, 20, 10)
    delta = st.slider("Price Stability δ", 0.05, 0.30, 0.10)
    fairness_tol = st.slider("Fairness Tolerance", 0.10, 0.50, 0.30)
    num_zones = st.slider("City Zones", 5, 15, 10)
    seed = st.number_input("Random Seed", value=42)

    run_btn = st.button("▶ Run Simulation", type="primary")


# ── Run Simulation ──────────────────────────────────────────────────────────

if run_btn:
    with st.spinner("Running simulation..."):
        results = run_simulation(
            num_windows=num_windows,
            delta=delta,
            fairness_tolerance=fairness_tol,
            num_zones=num_zones,
            seed=seed,
        )
        st.session_state["results"] = results


# ── Display Results ─────────────────────────────────────────────────────────

if "results" in st.session_state:
    results = st.session_state["results"]
    summary = results["summary"]

    tab1, tab2, tab3 = st.tabs(["Overview", "Charts", "Raw Data"])

    # ── Tab 1: Overview ─────────────────────────────────────────────────────
    with tab1:
        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Wait Time Reduction",
            f"{summary['wait_time_improvement_pct']:.1f}%",
            "vs SeqBaseline",
        )
        # TODO: Person C — add metrics for earnings variance, price deviation,
        #       and matching rate improvement

    # ── Tab 2: Charts ───────────────────────────────────────────────────────
    with tab2:
        windows = list(range(num_windows))

        # Wait Time chart
        fig_wait = go.Figure()
        fig_wait.add_trace(go.Scatter(
            x=windows,
            y=results["joint_opt"]["wait_times"],
            name="JointOpt",
            line=dict(color="blue"),
        ))
        fig_wait.add_trace(go.Scatter(
            x=windows,
            y=results["seq_baseline"]["wait_times"],
            name="SeqBaseline",
            line=dict(color="red", dash="dash"),
        ))
        fig_wait.update_layout(
            title="Wait Time per Window",
            xaxis_title="Window",
            yaxis_title="Total Wait Cost",
        )
        st.plotly_chart(fig_wait, use_container_width=True)

        # TODO: Person C — add charts for earnings variance, price deviation,
        #       and matching rate

    # ── Tab 3: Raw Data ─────────────────────────────────────────────────────
    with tab3:
        # TODO: Person C — build a DataFrame with per-window data for both
        #       systems and display with st.dataframe()
        st.info("Raw data table will appear here after implementation.")

else:
    st.info("👈 Configure parameters and click **Run Simulation** to start.")
