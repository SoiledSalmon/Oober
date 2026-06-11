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

try:
    from .config import (
        DEFAULT_DELTA,
        DEFAULT_FAIRNESS_TOLERANCE,
        SOLVER_TIME_LIMIT,
        TRAVEL_COST_OFFSET,
    )
except ImportError:
    from config import (
        DEFAULT_DELTA,
        DEFAULT_FAIRNESS_TOLERANCE,
        SOLVER_TIME_LIMIT,
        TRAVEL_COST_OFFSET,
    )

__all__ = ["solve_joint_opt"]


def _get_bipartite_nodes(feasibility_graph: nx.Graph) -> tuple[list[tuple], list[tuple]]:
    """Partition graph nodes into rider and driver node lists."""
    rider_nodes = []
    driver_nodes = []
    for node in feasibility_graph.nodes():
        if node[0] == "rider":
            rider_nodes.append(node)
        elif node[0] == "driver":
            driver_nodes.append(node)
    return rider_nodes, driver_nodes


def _create_decision_variables(
    feasibility_graph: nx.Graph,
) -> tuple[dict[tuple[int, int], pulp.LpVariable], dict[tuple[int, int], pulp.LpVariable]]:
    """Create binary assignment variables x and continuous pricing variables p."""
    x = {}
    p = {}
    for u, v in feasibility_graph.edges():
        r_node, d_node = (u, v) if u[0] == "rider" else (v, u)
        rid = r_node[1]
        did = d_node[1]
        x[(rid, did)] = pulp.LpVariable(f"x_{rid}_{did}", cat="Binary")
        p[(rid, did)] = pulp.LpVariable(f"p_{rid}_{did}", lowBound=0)
    return x, p


def _add_assignment_constraints(
    prob: pulp.LpProblem,
    feasibility_graph: nx.Graph,
    rider_nodes: list[tuple],
    driver_nodes: list[tuple],
    x: dict[tuple[int, int], pulp.LpVariable],
) -> None:
    """Add uniqueness matching constraints for riders and drivers."""
    for rider in rider_nodes:
        rid = rider[1]
        prob += pulp.lpSum(x[(rid, driver[1])] for driver in feasibility_graph.neighbors(rider)) <= 1

    for driver in driver_nodes:
        did = driver[1]
        prob += pulp.lpSum(x[(rider[1], did)] for rider in feasibility_graph.neighbors(driver)) <= 1


def _add_feasibility_constraints(
    prob: pulp.LpProblem,
    feasibility_graph: nx.Graph,
    x: dict[tuple[int, int], pulp.LpVariable],
    p: dict[tuple[int, int], pulp.LpVariable],
) -> None:
    """Add lower and upper bounds for prices of active matches."""
    for u, v in feasibility_graph.edges():
        r_node, d_node = (u, v) if u[0] == "rider" else (v, u)
        rid = r_node[1]
        did = d_node[1]
        edge = feasibility_graph[r_node][d_node]
        prob += p[(rid, did)] >= edge["price_lb"] * x[(rid, did)]
        prob += p[(rid, did)] <= edge["price_ub"] * x[(rid, did)]


def _add_stability_constraints(
    prob: pulp.LpProblem,
    feasibility_graph: nx.Graph,
    price_memory: dict[tuple[int, int], float],
    delta: float,
    x: dict[tuple[int, int], pulp.LpVariable],
    p: dict[tuple[int, int], pulp.LpVariable],
) -> None:
    """Add corridor-level price stability constraints."""
    if delta >= 1.0:
        return
    for u, v in feasibility_graph.edges():
        r_node, d_node = (u, v) if u[0] == "rider" else (v, u)
        rid = r_node[1]
        did = d_node[1]
        edge = feasibility_graph[r_node][d_node]
        corridor = (edge["origin_zone"], edge["dest_zone"])
        if corridor in price_memory:
            prev_price = price_memory[corridor]
            prob += p[(rid, did)] >= prev_price * (1 - delta) * x[(rid, did)]
            prob += p[(rid, did)] <= prev_price * (1 + delta) * x[(rid, did)]


def _add_fairness_constraints(
    prob: pulp.LpProblem,
    feasibility_graph: nx.Graph,
    driver_nodes: list[tuple],
    fairness_tolerance: float,
    x: dict[tuple[int, int], pulp.LpVariable],
    p: dict[tuple[int, int], pulp.LpVariable],
) -> None:
    """Add driver earnings variance range constraints."""
    if fairness_tolerance >= 1.0:
        return
    midpoints = [(d["price_lb"] + d["price_ub"]) / 2 for _, _, d in feasibility_graph.edges(data=True)]
    target_earnings = np.mean(midpoints) if midpoints else 0.0

    for driver in driver_nodes:
        did = driver[1]
        earnings_terms = []
        assignment_terms = []
        for rider in feasibility_graph.neighbors(driver):
            rid = rider[1]
            earnings_terms.append(p[(rid, did)])
            assignment_terms.append(x[(rid, did)])
        earnings_d = pulp.lpSum(earnings_terms)
        assignments_d = pulp.lpSum(assignment_terms)
        prob += earnings_d <= target_earnings * (1 + fairness_tolerance) * assignments_d
        prob += earnings_d >= target_earnings * (1 - fairness_tolerance) * assignments_d


def _format_results(
    feasibility_graph: nx.Graph,
    x: dict[tuple[int, int], pulp.LpVariable],
    p: dict[tuple[int, int], pulp.LpVariable],
    status: str,
    start_time: float,
) -> dict[str, Any]:
    """Format matching and pricing optimization output."""
    assignments = []
    total_wait_cost = 0.0

    if status in ["Optimal", "Feasible"]:
        for u, v in feasibility_graph.edges():
            r_node, d_node = (u, v) if u[0] == "rider" else (v, u)
            rid, did = r_node[1], d_node[1]
            if pulp.value(x[(rid, did)]) > 0.5:
                price = pulp.value(p[(rid, did)])
                assignments.append((rid, did, round(price, 2)))
                total_wait_cost += feasibility_graph[r_node][d_node]["travel_cost"]

    solve_time = time.perf_counter() - start_time
    return {
        "assignments": assignments,
        "total_wait_cost": float(total_wait_cost),
        "matched_count": len(assignments),
        "solver_status": status,
        "solve_time_sec": round(solve_time, 4),
    }


def solve_joint_opt(
    feasibility_graph: nx.Graph,
    price_memory: dict[tuple[int, int], float],
    earnings_history: dict[int, float],
    delta: float = DEFAULT_DELTA,
    fairness_tolerance: float = DEFAULT_FAIRNESS_TOLERANCE,
    window_id: int = 0,
) -> dict[str, Any]:
    """Solve the joint assignment-and-pricing ILP."""
    start_time = time.perf_counter()
    prob = pulp.LpProblem("JointOpt", pulp.LpMinimize)

    rider_nodes, driver_nodes = _get_bipartite_nodes(feasibility_graph)
    x, p = _create_decision_variables(feasibility_graph)

    # Objective Function: minimize travel cost (with offset to prioritize matches)
    prob += pulp.lpSum(
        (feasibility_graph[r_node][d_node]["travel_cost"] + TRAVEL_COST_OFFSET) * x[(r_node[1], d_node[1])]
        for u, v in feasibility_graph.edges()
        for r_node, d_node in [((u, v) if u[0] == "rider" else (v, u))]
    )

    _add_assignment_constraints(prob, feasibility_graph, rider_nodes, driver_nodes, x)
    _add_feasibility_constraints(prob, feasibility_graph, x, p)
    _add_stability_constraints(prob, feasibility_graph, price_memory, delta, x, p)
    _add_fairness_constraints(prob, feasibility_graph, driver_nodes, fairness_tolerance, x, p)

    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=SOLVER_TIME_LIMIT)
    prob.solve(solver)
    status = pulp.LpStatus[prob.status]

    if status not in ["Optimal", "Feasible"] and (delta < 1.0 or fairness_tolerance < 1.0):
        print(f"[WARN] JointOpt solver status {status} on window {window_id}. Re-running with relaxed constraints...")
        relaxed_res = solve_joint_opt(
            feasibility_graph=feasibility_graph,
            price_memory=price_memory,
            earnings_history=earnings_history,
            delta=1.0,
            fairness_tolerance=1.0,
            window_id=window_id,
        )
        if relaxed_res["solver_status"] in ["Optimal", "Feasible"]:
            relaxed_res["solver_status"] = "Relaxed"
        return relaxed_res

    return _format_results(feasibility_graph, x, p, status, start_time)