"""
Joint ILP Optimizer (Person A)

The heart of the project. Takes the feasibility graph and formulates a full
ILP using PuLP. Solves it to get optimal (rider, driver, price) triples.
"""

import time

import numpy as np
import pulp
import networkx as nx


def solve_joint_opt(
    feasibility_graph: nx.Graph,
    price_memory: dict,
    earnings_history: dict,
    delta: float = 0.10,
    fairness_tolerance: float = 0.30,
    window_id: int = 0
) -> dict:

    start_time = time.time()

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
    for r_node, d_node in feasibility_graph.edges():

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
        feasibility_graph[r][d]["travel_cost"]
        * x[(r[1], d[1])]
        for r, d in feasibility_graph.edges()
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
    for r_node, d_node in feasibility_graph.edges():

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
    for r_node, d_node in feasibility_graph.edges():

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

    assignments = []
    total_wait_cost = 0

    if status in ["Optimal", "Feasible"]:

        for r_node, d_node in feasibility_graph.edges():

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

    solve_time = time.time() - start_time

    return {
        "assignments": assignments,
        "total_wait_cost": float(total_wait_cost),
        "matched_count": len(assignments),
        "solver_status": status,
        "solve_time_sec": round(solve_time, 4)
    }