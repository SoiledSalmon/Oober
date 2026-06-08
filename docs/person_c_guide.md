# Developer Implementation Guide — UI, Metrics & Integration (Person C)

Welcome to the **Oober** UI and Integration Guide! Since the Algorithmic Core (Person A) and Data/Baseline (Person B) modules are fully completed, this guide provides you with a clear roadmap to complete the evaluation metrics and the Streamlit web dashboard.

---

## 🚀 1. Overview of Tasks

You are responsible for completing the following two files:
1. **`oober/metrics.py`**: Implementation of the 4 key evaluation metrics.
2. **`oober/app.py`**: Building the Streamlit interactive charts, metric cards, and raw data display.

To help you verify your metrics, a unit test suite has been added at `tests/test_metrics.py`.

---

## 📊 2. Metric Specification (`oober/metrics.py`)

Here is how each metric should be computed. Make sure to handle all edge cases as specified.

### 2.1 Wait Time
* **Objective**: Compute the sum of the travel costs for all matched rider-driver pairs.
* **Mathematical Formula**:
  $$\text{Total Wait Cost} = \sum_{(r, d, p) \in \mathcal{A}} \text{travel\_cost}(r, d)$$
  *Where $\mathcal{A}$ is the list of assignments, and each assignment is a tuple `(rider_id, driver_id, price)`.*
* **Implementation Details**:
  - Retrieve the edge `travel_cost` from `feasibility_graph`.
  - The node labels in `feasibility_graph` are `("rider", rider_id)` and `("driver", driver_id)`.
  - Ensure you handle cases where the graph might not have the edge (though in practice it should, a fallback of `0.0` or checking for edge presence is good practice).
  - Return `0.0` if `assignments` is empty.

### 2.2 Earnings Variance
* **Objective**: Measure the variance in total earnings across all drivers in the current scheduling window. This tracks driver fairness.
* **Mathematical Formula**:
  $$\text{Variance} = \frac{1}{N} \sum_{d \in \mathcal{D}} (E_d - \bar{E})^2$$
  *Where $\mathcal{D}$ is the set of all drivers in the system, $E_d$ is the total earnings of driver $d$ (sum of prices of rides assigned to $d$), $\bar{E}$ is the average earnings across all drivers, and $N$ is the total number of drivers.*
* **Implementation Details**:
  - Unmatched drivers earn `0.0` and **must be included** in the variance calculation.
  - Map each driver ID to their total earnings. Sum the prices of assigned rides.
  - Construct a list of earnings of size equal to the number of drivers. Set unmatched drivers' earnings to `0.0`.
  - Use `numpy.var(earnings_list, ddof=0)` (population variance) to compute the final value.
  - Return `0.0` if the drivers list is empty.

### 2.3 Price Deviation
* **Objective**: Compute the fraction of assignments that violate the price stability threshold $\delta$.
* **Mathematical Formula**:
  $$\text{Deviation Fraction} = \frac{\sum_{(r, d, p) \in \mathcal{A}} \mathbb{I}\left( (origin_r, dest_r) \in \mathcal{M} \land |p - \text{prev\_price}| > \delta \cdot \text{prev\_price} \right)}{|\mathcal{A}|}$$
  *Where $\mathcal{M}$ is the price memory, $p$ is the matched price, and $\mathbb{I}$ is the indicator function.*
* **Implementation Details**:
  - For each assignment, look up the rider dict using `rider_id` in the `riders` list to find their `origin_zone` and `dest_zone`.
  - If the corridor `(origin_zone, dest_zone)` exists in `price_memory`, verify if:
    $$\text{abs}(\text{price} - \text{prev\_price}) > \delta \cdot \text{prev\_price}$$
  - Count the number of assignments that violate this stability condition.
  - Return the number of violations divided by the total number of assignments in the list (`len(assignments)`).
  - Return `0.0` if `assignments` is empty.

### 2.4 Matching Rate
* **Objective**: Fraction of total riders in the current scheduling window who were successfully matched.
* **Mathematical Formula**:
  $$\text{Matching Rate} = \frac{|\mathcal{A}|}{R}$$
  *Where $R$ is the total number of riders in the current window.*
* **Implementation Details**:
  - Return `len(assignments) / total_riders`.
  - Return `0.0` if `total_riders` is `0`.

---

## 🎨 3. Dashboard Integration (`oober/app.py`)

The basic structure of the Streamlit dashboard is ready. You need to implement the remaining elements under the respective tabs.

### 3.1 Tab 1: Overview (Metric Cards)
Complete the columns to display summary statistics using `st.metric()`.
```python
col1, col2, col3, col4 = st.columns(4)

# Wait Time (Completed)
col1.metric(
    "Wait Time Reduction",
    f"{summary['wait_time_improvement_pct']:.1f}%",
    "vs SeqBaseline",
)

# TODO: Add Earnings Variance
col2.metric(
    "Earnings Variance Reduction",
    f"{summary['earnings_var_improvement_pct']:.1f}%",
    "vs SeqBaseline",
)

# TODO: Add Price Oscillation Reduction
col3.metric(
    "Price Oscillation Reduction",
    f"{summary['price_dev_improvement_pct']:.1f}%",
    "vs SeqBaseline",
)

# TODO: Add Matching Rate Improvement
col4.metric(
    "Matching Rate Improvement",
    f"{summary['matching_rate_improvement_pct']:.1f}%",
    "vs SeqBaseline",
)
```

### 3.2 Tab 2: Charts (Plotly Comparison)
Create three additional Plotly line charts showing the performance of both systems over the time windows:
1. **Earnings Variance**: Compare `results["joint_opt"]["earnings_variances"]` and `results["seq_baseline"]["earnings_variances"]`.
2. **Price Deviation**: Compare `results["joint_opt"]["price_deviations"]` and `results["seq_baseline"]["price_deviations"]`.
3. **Matching Rate**: Compare `results["joint_opt"]["matching_rates"]` and `results["seq_baseline"]["matching_rates"]`.

*Design tip: Use solid blue lines for `JointOpt` and dashed red lines for `SeqBaseline` to maintain consistent branding.*

### 3.3 Tab 3: Raw Data (Combined DataFrame)
Build a single Pandas DataFrame with the raw outputs from both systems and render it using `st.dataframe()`.
```python
# Sample Pandas integration
df_data = {
    "Window": windows,
    "JointOpt Wait Time": results["joint_opt"]["wait_times"],
    "SeqBaseline Wait Time": results["seq_baseline"]["wait_times"],
    "JointOpt Earnings Var": results["joint_opt"]["earnings_variances"],
    "SeqBaseline Earnings Var": results["seq_baseline"]["earnings_variances"],
    "JointOpt Price Dev": results["joint_opt"]["price_deviations"],
    "SeqBaseline Price Dev": results["seq_baseline"]["price_deviations"],
    "JointOpt Match Rate": results["joint_opt"]["matching_rates"],
    "SeqBaseline Match Rate": results["seq_baseline"]["matching_rates"],
    "JointOpt Solve Time (s)": results["joint_opt"]["solve_times"],
    "SeqBaseline Solve Time (s)": results["seq_baseline"]["solve_times"]
}
df = pd.DataFrame(df_data)
st.dataframe(df.style.format(precision=2), use_container_width=True)
```

---

## 🧪 4. Testing and Verification

To test your code locally, run the standard unittest suite from the project root directory:
```bash
python -m unittest tests/test_metrics.py
```
As you implement each function in `metrics.py`, the corresponding unit tests will transition from `Skipped` to `Passed`.

Once both `metrics.py` and `app.py` are complete, launch the dashboard:
```bash
streamlit run oober/app.py
```
Verify that clicking **Run Simulation** populates all charts and the overview cards without errors.
