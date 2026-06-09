import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time

from simulation import run_simulation

# --------------------------------------------------
# Page Config
# --------------------------------------------------

st.set_page_config(
    page_title="JointOpt Dashboard",
    layout="wide"
)

st.title("Joint Price-and-Match Optimization in Ride-Hailing")

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------

def plot_comparison_chart(
    title: str,
    windows: list,
    joint_values: list,
    baseline_values: list,
    y_label: str
):
    """Reusable comparison chart."""

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=windows,
            y=joint_values,
            mode="lines+markers",
            name="JointOpt",
            line=dict(color="blue")
        )
    )

    fig.add_trace(
        go.Scatter(
            x=windows,
            y=baseline_values,
            mode="lines+markers",
            name="SeqBaseline",
            line=dict(color="red", dash="dash")
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Time Window",
        yaxis_title=y_label,
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:
    st.header("Simulation Parameters")

    num_windows = st.slider(
        "Time Windows",
        min_value=5,
        max_value=20,
        value=10
    )

    delta = st.slider(
        "Price Stability δ",
        min_value=0.05,
        max_value=0.30,
        value=0.10
    )

    fairness_tol = st.slider(
        "Fairness Tolerance",
        min_value=0.10,
        max_value=0.50,
        value=0.30
    )

    num_zones = st.slider(
        "City Zones",
        min_value=5,
        max_value=15,
        value=10
    )

    seed = st.number_input(
        "Random Seed",
        value=42,
        step=1
    )

    st.markdown("---")

    run_btn = st.button(
        "▶ Run Simulation",
        type="primary",
        use_container_width=True
    )

    st.info(
        "Adjust parameters and run the simulation "
        "to compare JointOpt against SeqBaseline."
    )

# --------------------------------------------------
# Run Simulation
# --------------------------------------------------

if run_btn:
    with st.spinner("Running simulation..."):

        start_time = time.time()

        results = run_simulation(
            num_windows=num_windows,
            delta=delta,
            fairness_tolerance=fairness_tol,
            num_zones=num_zones,
            seed=seed
        )

        elapsed = time.time() - start_time

        st.session_state["results"] = results
        st.session_state["runtime"] = elapsed

# --------------------------------------------------
# Show Results
# --------------------------------------------------

if "results" in st.session_state:

    results = st.session_state["results"]
    runtime = st.session_state.get("runtime", 0)

    st.success(f"Simulation completed in {runtime:.2f} seconds")

    summary = results["summary"]

    tab1, tab2, tab3 = st.tabs(
        ["Overview", "Charts", "Raw Data"]
    )

    # ==================================================
    # TAB 1 - OVERVIEW
    # ==================================================

    with tab1:

        st.subheader("Performance Summary")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Wait Time Reduction",
            f"{summary['wait_time_improvement_pct']:.1f}%"
        )

        col2.metric(
            "Earnings Variance Reduction",
            f"{summary['earnings_variance_improvement_pct']:.1f}%"
        )

        col3.metric(
            "Price Stability Improvement",
            f"{summary['price_deviation_improvement_pct']:.1f}%"
        )

        col4.metric(
            "Matching Rate Improvement",
            f"{summary['matching_rate_improvement_pct']:.1f}%"
        )

        st.markdown("---")

        st.subheader("Summary Statistics")

        summary_df = pd.DataFrame(
            summary.items(),
            columns=["Metric", "Value"]
        )

        st.dataframe(
            summary_df,
            use_container_width=True
        )

    # ==================================================
    # TAB 2 - CHARTS
    # ==================================================

    with tab2:

        windows = list(range(num_windows))

        plot_comparison_chart(
            title="Wait Time per Window",
            windows=windows,
            joint_values=results["joint_opt"]["wait_times"],
            baseline_values=results["seq_baseline"]["wait_times"],
            y_label="Total Wait Cost"
        )

        plot_comparison_chart(
            title="Earnings Variance per Window",
            windows=windows,
            joint_values=results["joint_opt"]["earnings_variances"],
            baseline_values=results["seq_baseline"]["earnings_variances"],
            y_label="Variance"
        )

        plot_comparison_chart(
            title="Price Deviation per Window",
            windows=windows,
            joint_values=results["joint_opt"]["price_deviations"],
            baseline_values=results["seq_baseline"]["price_deviations"],
            y_label="Deviation Rate"
        )

        plot_comparison_chart(
            title="Matching Rate per Window",
            windows=windows,
            joint_values=results["joint_opt"]["matching_rates"],
            baseline_values=results["seq_baseline"]["matching_rates"],
            y_label="Matching Rate"
        )

    # ==================================================
    # TAB 3 - RAW DATA
    # ==================================================

    with tab3:

        windows = list(range(num_windows))

        df = pd.DataFrame({
            "Window": windows,

            "Joint Wait":
                results["joint_opt"]["wait_times"],

            "Baseline Wait":
                results["seq_baseline"]["wait_times"],

            "Joint Earnings Variance":
                results["joint_opt"]["earnings_variances"],

            "Baseline Earnings Variance":
                results["seq_baseline"]["earnings_variances"],

            "Joint Price Deviation":
                results["joint_opt"]["price_deviations"],

            "Baseline Price Deviation":
                results["seq_baseline"]["price_deviations"],

            "Joint Matching Rate":
                results["joint_opt"]["matching_rates"],

            "Baseline Matching Rate":
                results["seq_baseline"]["matching_rates"]
        })

        st.dataframe(
            df,
            use_container_width=True
        )

        csv = df.to_csv(index=False)

        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name="jointopt_results.csv",
            mime="text/csv"
        )

else:
    st.info(
        "Configure parameters in the sidebar and "
        "click 'Run Simulation' to begin."
    )