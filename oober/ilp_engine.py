"""
Joint ILP Optimizer (Person A)

The heart of the project. Takes the feasibility graph and formulates a full
ILP using PuLP. Solves it to get optimal (rider, driver, price) triples.
"""

import time
from typing import Any

import numpy as np
import pulp
import networkx as nx

__all__ = ["solve_joint_opt"]


def solve_joint_opt(
    feasibility_graph: nx.Graph,
    price_memory: dict[tuple[int, int], float],
    earnings_history: dict[int, float],
    delta: float = 0.10,
    fairness_tolerance: float = 0.30,
    window_id: int = 0
) -> dict[str, Any]:
    """Solve the joint assignment-and-pricing ILP.

    Decision variables
    ------------------
    x_rd : binary
        1 if rider *r* is matched with driver *d*, 0 otherwise.
    p_rd : continuous (>= 0)
        Price paid by rider *r* to driver *d* when matched.

    Objective
    ---------
    Minimize total travel cost:
        min  Σ_{(r,d)∈E}  travel_cost(r,d) · x_rd

    Constraints
    -----------
    1. **Assignment** – each rider matched to at most one driver;
       each driver matched to at most one rider.
    2. **Feasibility** – price must lie within the edge's
       [price_lb, price_ub] when the pair is matched.
    3. **Stability** – if a corridor has a remembered price, the
       new price stays within ±delta of that price.
    4. **Fairness** – every driver's per-trip earnings stay within
       ±fairness_tolerance of the market-wide midpoint average.

    Parameters
    ----------
    feasibility_graph : nx.Graph
        Undirected bipartite graph whose nodes are
        ``('rider', rid)`` / ``('driver', did)`` tuples and whose
        edges carry ``travel_cost``, ``price_lb``, ``price_ub``,
        ``origin_zone``, and ``dest_zone`` attributes.
    price_memory : dict
        Maps ``(origin_zone, dest_zone)`` corridors to the last
        accepted price, used by stability constraints.
    earnings_history : dict
        Historical per-driver earnings (reserved for future use).
    delta : float
        Maximum fractional deviation from the remembered corridor
        price (stability constraint).  Default 0.10 (±10 %).
    fairness_tolerance : float
        Maximum fractional deviation from the market-average
        earnings per trip (fairness constraint).  Default 0.30
        (±30 %).
    window_id : int
        Identifier for the current scheduling window.

    Returns
    -------
    dict
        ``assignments``      – list of ``(rid, did, price)`` tuples
        ``total_wait_cost``  – float, sum of travel costs for
                               matched pairs
        ``matched_count``    – int, number of matched pairs
        ``solver_status``    – str, PuLP solver status
        ``solve_time_sec``   – float, wall-clock seconds
    """

    start_time = time.perf_counter()

    prob = pulp.LpProblem(
        "JointOpt",
        pulp.LpMinimize
    )

    x = {}
    p = {}

    rider_nodes = []
    driver_nodes = []

    for node in feasibility_graph.nodes():

        if node[0] == "rider":
            rider_nodes.append(node)

        elif node[0] == "driver":
            driver_nodes.append(node)

    # Create decision variables
    for u, v in feasibility_graph.edges():
        r_node, d_node = (u, v) if u[0] == 'rider' else (v, u)

        rid = r_node[1]
        did = d_node[1]

        x[(rid, did)] = pulp.LpVariable(
            f"x_{rid}_{did}",
            cat="Binary"
        )

        p[(rid, did)] = pulp.LpVariable(
            f"p_{rid}_{did}",
            lowBound=0
        )

    # Objective Function
    prob += pulp.lpSum(
        (feasibility_graph[r_node][d_node]["travel_cost"] - 10000.0)
        * x[(r_node[1], d_node[1])]
        for u, v in feasibility_graph.edges()
        for r_node, d_node in [((u, v) if u[0] == 'rider' else (v, u))]
    )

    # Assignment Constraints
    for rider in rider_nodes:

        rid = rider[1]

        rider_vars = []

        for driver in feasibility_graph.neighbors(rider):

            rider_vars.append(
                x[(rid, driver[1])]
            )

        prob += pulp.lpSum(rider_vars) <= 1

    # Driver Constraints
    for driver in driver_nodes:

        did = driver[1]

        driver_vars = []

        for rider in feasibility_graph.neighbors(driver):

            driver_vars.append(
                x[(rider[1], did)]
            )

        prob += pulp.lpSum(driver_vars) <= 1

    # Feasibility Constraints
    for u, v in feasibility_graph.edges():
        r_node, d_node = (u, v) if u[0] == 'rider' else (v, u)

        rid = r_node[1]
        did = d_node[1]

        edge = feasibility_graph[r_node][d_node]

        prob += (
            p[(rid, did)]
            >= edge["price_lb"] * x[(rid, did)]
        )

        prob += (
            p[(rid, did)]
            <= edge["price_ub"] * x[(rid, did)]
        )

    # Stability Constraints
    if delta < 1.0:
        for u, v in feasibility_graph.edges():
            r_node, d_node = (u, v) if u[0] == 'rider' else (v, u)

            rid = r_node[1]
            did = d_node[1]

            edge = feasibility_graph[r_node][d_node]

            corridor = (
                edge["origin_zone"],
                edge["dest_zone"]
            )

            if corridor in price_memory:

                prev_price = price_memory[corridor]

                lower = prev_price * (1 - delta)
                upper = prev_price * (1 + delta)

                prob += (
                    p[(rid, did)]
                    >= lower * x[(rid, did)]
                )

                prob += (
                    p[(rid, did)]
                    <= upper * x[(rid, did)]
                )

    # Fairness Constraints
    if fairness_tolerance < 1.0:

        midpoints = []

        for _, _, data in feasibility_graph.edges(data=True):

            midpoint = (
                data["price_lb"] +
                data["price_ub"]
            ) / 2

            midpoints.append(midpoint)

        target_earnings = (
            np.mean(midpoints)
            if midpoints
            else 0
        )

        for driver in driver_nodes:

            did = driver[1]

            earnings_terms = []
            assignment_terms = []

            for rider in feasibility_graph.neighbors(driver):

                rid = rider[1]

                earnings_terms.append(
                    p[(rid, did)]
                )

                assignment_terms.append(
                    x[(rid, did)]
                )

            earnings_d = pulp.lpSum(
                earnings_terms
            )

            assignments_d = pulp.lpSum(
                assignment_terms
            )

            prob += (
                earnings_d
                <= target_earnings
                * (1 + fairness_tolerance)
                * assignments_d
            )

            prob += (
                earnings_d
                >= target_earnings
                * (1 - fairness_tolerance)
                * assignments_d
            )

    solver = pulp.PULP_CBC_CMD(
        msg=0,
        timeLimit=30
    )

    prob.solve(solver)

    status = pulp.LpStatus[
        prob.status
    ]

    # Recursive relaxation if infeasible/undefined
    if status not in ["Optimal", "Feasible"] and (delta < 1.0 or fairness_tolerance < 1.0):
        print(f"[WARN] JointOpt solver status {status} on window {window_id}. Re-running with relaxed constraints (delta=1.0, fairness_tolerance=1.0)...")
        relaxed_res = solve_joint_opt(
            feasibility_graph=feasibility_graph,
            price_memory=price_memory,
            earnings_history=earnings_history,
            delta=1.0,
            fairness_tolerance=1.0,
            window_id=window_id
        )
        if relaxed_res["solver_status"] in ["Optimal", "Feasible"]:
            relaxed_res["solver_status"] = "Relaxed"
        return relaxed_res

    assignments = []
    total_wait_cost = 0

    if status in ["Optimal", "Feasible"]:

        for u, v in feasibility_graph.edges():
            r_node, d_node = (u, v) if u[0] == 'rider' else (v, u)

            rid = r_node[1]
            did = d_node[1]

            if pulp.value(
                x[(rid, did)]
            ) > 0.5:

                price = pulp.value(
                    p[(rid, did)]
                )

                assignments.append(
                    (
                        rid,
                        did,
                        round(price, 2)
                    )
                )

                total_wait_cost += (
                    feasibility_graph[r_node][d_node]["travel_cost"]
                )

    solve_time = time.perf_counter() - start_time

    return {
        "assignments": assignments,
        "total_wait_cost": float(total_wait_cost),
        "matched_count": len(assignments),
        "solver_status": status,
        "solve_time_sec": round(solve_time, 4)
    }