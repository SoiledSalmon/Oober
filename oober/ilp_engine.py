"""
Formulates and solves the joint pricing and matching integer linear program.

This module is part of the Oober joint price-and-match
optimisation system. It implements the ILP formulation
that simultaneously computes rider-driver assignments
and prices.
"""

import time
from typing import Any

import networkx as nx
import numpy as np
import pulp

try:
    from .config import (
        DEFAULT_DELTA,
        DEFAULT_FAIRNESS_TOLERANCE,
        SOLVER_TIME_LIMIT,
        TRAVEL_COST_OFFSET,
    )
    from .type_defs import OptimizationResult, PriceMemory
except ImportError:
    from config import (
        DEFAULT_DELTA,
        DEFAULT_FAIRNESS_TOLERANCE,
        SOLVER_TIME_LIMIT,
        TRAVEL_COST_OFFSET,
    )
    from type_defs import OptimizationResult, PriceMemory

__all__ = ["solve_joint_opt"]

# Constants
PRICE_STABILITY_RELAXATION_LIMIT = (
    1.0  # Limit above which delta-based stability constraints are ignored/relaxed
)
FAIRNESS_RELAXATION_LIMIT = (
    1.0  # Limit above which driver fairness constraints are ignored/relaxed
)
MATCHING_THRESHOLD = (
    0.5  # Decision variable threshold to consider a rider matched to a driver
)
FAIRNESS_TOLERANCE_RELAXATION_MULTIPLIER = (
    0.5  # Scaling factor for the fairness tolerance in the solver internal checks
)


def _get_bipartite_nodes(
    feasibility_graph: nx.Graph,
) -> tuple[list[tuple], list[tuple]]:
    """Partition graph nodes into rider and driver node lists.

    Args:
        feasibility_graph: Bipartite graph containing rider and driver nodes.

    Returns:
        tuple[list[tuple], list[tuple]]: A tuple containing:
            - list[tuple]: Rider nodes.
            - list[tuple]: Driver nodes.
    """
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
) -> tuple[
    dict[tuple[int, int], pulp.LpVariable],
    dict[tuple[int, int], pulp.LpVariable],
]:
    """Create binary assignment variables x and continuous pricing variables p.

    Args:
        feasibility_graph: Bipartite graph containing feasible rider-driver edges.

    Returns:
        tuple[
            dict[tuple[int, int], pulp.LpVariable],
            dict[tuple[int, int], pulp.LpVariable]
        ]: A tuple containing:
            - dict[tuple[int, int], pulp.LpVariable]: Bipartite matching decision variables x.
            - dict[tuple[int, int], pulp.LpVariable]: Bipartite pricing decision variables p.
    """
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
    """Add uniqueness matching constraints for riders and drivers.

    Args:
        prob: The pulp LpProblem object.
        feasibility_graph: The bipartite candidate graph.
        rider_nodes: List of rider node tuples in the graph.
        driver_nodes: List of driver node tuples in the graph.
        x: Dictionary of assignment decision variables.

    Returns:
        None

    Notes:
        Encodes the matching uniqueness constraints:
        sum_{d in D(r)} x_{rd} <= 1 for all r in R (each rider matched to at most one driver)
        sum_{r in R(d)} x_{rd} <= 1 for all d in D (each driver matched to at most one rider)
    """
    for rider in rider_nodes:
        rid = rider[1]
        prob += (
            pulp.lpSum(
                x[(rid, driver[1])]
                for driver in feasibility_graph.neighbors(rider)
            )
            <= 1
        )

    for driver in driver_nodes:
        did = driver[1]
        prob += (
            pulp.lpSum(
                x[(rider[1], did)]
                for rider in feasibility_graph.neighbors(driver)
            )
            <= 1
        )


def _add_feasibility_constraints(
    prob: pulp.LpProblem,
    feasibility_graph: nx.Graph,
    x: dict[tuple[int, int], pulp.LpVariable],
    p: dict[tuple[int, int], pulp.LpVariable],
) -> None:
    """Add lower and upper bounds for prices of active matches.

    Args:
        prob: The pulp LpProblem object.
        feasibility_graph: Bipartite graph containing travel_cost and pricing bounds.
        x: Dictionary of assignment decision variables.
        p: Dictionary of pricing decision variables.

    Returns:
        None

    Notes:
        Encodes two-sided acceptance constraints:
        p_{rd} >= price_lb_{rd} * x_{rd} (price must be above driver minimum acceptable fare)
        p_{rd} <= price_ub_{rd} * x_{rd} (price must be below rider willingness to pay)
    """
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
    price_memory: PriceMemory,
    delta: float,
    x: dict[tuple[int, int], pulp.LpVariable],
    p: dict[tuple[int, int], pulp.LpVariable],
) -> None:
    """Add corridor-level price stability constraints.

    Args:
        prob: The pulp LpProblem object.
        feasibility_graph: Bipartite graph containing travel_cost and pricing bounds.
        price_memory: Memory of past prices per corridor.
        delta: Price stability threshold.
        x: Dictionary of assignment decision variables.
        p: Dictionary of pricing decision variables.

    Returns:
        None

    Notes:
        Encodes price stability constraints:
        p_{rd} >= prev_price_{cr} * (1 - delta) * x_{rd}
        p_{rd} <= prev_price_{cr} * (1 + delta) * x_{rd}
        where cr is the corridor corresponding to the origin and destination of rider r.
    """
    if delta >= PRICE_STABILITY_RELAXATION_LIMIT:
        return
    for u, v in feasibility_graph.edges():
        r_node, d_node = (u, v) if u[0] == "rider" else (v, u)
        rid = r_node[1]
        did = d_node[1]
        edge = feasibility_graph[r_node][d_node]
        corridor = (edge["origin_zone"], edge["dest_zone"])
        if corridor in price_memory:
            prev_price = price_memory[corridor]
            prob += (
                p[(rid, did)] >= prev_price * (1 - delta) * x[(rid, did)]
            )
            prob += (
                p[(rid, did)] <= prev_price * (1 + delta) * x[(rid, did)]
            )


def _add_fairness_constraints(
    prob: pulp.LpProblem,
    feasibility_graph: nx.Graph,
    driver_nodes: list[tuple],
    fairness_tolerance: float,
    x: dict[tuple[int, int], pulp.LpVariable],
    p: dict[tuple[int, int], pulp.LpVariable],
) -> None:
    """Add driver earnings variance range constraints.

    Args:
        prob: The pulp LpProblem object.
        feasibility_graph: Bipartite graph containing travel_cost and pricing bounds.
        driver_nodes: List of driver node tuples.
        fairness_tolerance: Driver earnings fairness tolerance.
        x: Dictionary of assignment decision variables.
        p: Dictionary of pricing decision variables.

    Returns:
        None

    Notes:
        Encodes driver earnings fairness constraints:
        earnings_d <= target_earnings * (1 + fairness_tolerance) * assignments_d
        earnings_d >= target_earnings * (1 - fairness_tolerance) * assignments_d
        where assignments_d = sum_{r in R(d)} x_{rd} and earnings_d = sum_{r in R(d)} p_{rd}.
    """
    if fairness_tolerance >= FAIRNESS_RELAXATION_LIMIT:
        return
    midpoints = [
        (d["price_lb"] + d["price_ub"]) / 2
        for _, _, d in feasibility_graph.edges(data=True)
    ]
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
        prob += (
            earnings_d
            <= target_earnings * (1 + fairness_tolerance) * assignments_d
        )
        prob += (
            earnings_d
            >= target_earnings * (1 - fairness_tolerance) * assignments_d
        )


def _format_results(
    feasibility_graph: nx.Graph,
    x: dict[tuple[int, int], pulp.LpVariable],
    p: dict[tuple[int, int], pulp.LpVariable],
    status: str,
    start_time: float,
) -> OptimizationResult:
    """Format matching and pricing optimization output.

    Args:
        feasibility_graph: Bipartite graph containing travel_cost and pricing bounds.
        x: Dictionary of assignment decision variables.
        p: Dictionary of pricing decision variables.
        status: The solver execution status string.
        start_time: Start timestamp of solver execution.

    Returns:
        OptimizationResult: Formatted dictionary containing the matching results.
    """
    assignments = []
    total_wait_cost = 0.0

    if status in ["Optimal", "Feasible"]:
        for u, v in feasibility_graph.edges():
            r_node, d_node = (u, v) if u[0] == "rider" else (v, u)
            rid, did = r_node[1], d_node[1]
            if pulp.value(x[(rid, did)]) > MATCHING_THRESHOLD:
                price = pulp.value(p[(rid, did)])
                assignments.append((rid, did, round(price, 2)))
                total_wait_cost += feasibility_graph[r_node][d_node][
                    "travel_cost"
                ]

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
    price_memory: PriceMemory,
    earnings_history: dict[int, float] = None,  # Deprecated/unused parameter for backward compatibility
    delta: float = DEFAULT_DELTA,
    fairness_tolerance: float = DEFAULT_FAIRNESS_TOLERANCE,
    window_id: int = 0,
) -> OptimizationResult:
    """Solve the joint assignment-and-pricing ILP.

    Args:
        feasibility_graph: Bipartite graph of feasible candidate pairs.
        price_memory: Dictionary mapping corridors to previous prices.
        earnings_history: Dictionary mapping driver ID to cumulative earnings (deprecated).
        delta: Price stability corridor tolerance (delta).
        fairness_tolerance: Driver earnings fairness tolerance.
        window_id: Index of the current simulation time window.

    Returns:
        OptimizationResult: Structured dictionary containing assignments and performance metrics.

    Notes:
        Encodes the joint assignment objective function:
        minimize sum_{(r,d) in E} (travel_cost_{rd} + TRAVEL_COST_OFFSET) * x_{rd}
        where TRAVEL_COST_OFFSET is a large negative constant (e.g. -10000.0) to prioritize matching.
    """
    start_time = time.perf_counter()
    prob = pulp.LpProblem("JointOpt", pulp.LpMinimize)

    rider_nodes, driver_nodes = _get_bipartite_nodes(feasibility_graph)
    x, p = _create_decision_variables(feasibility_graph)

    # Objective Function: minimize travel cost (with offset to prioritize matches)
    prob += pulp.lpSum(
        (
            feasibility_graph[r_node][d_node]["travel_cost"]
            + TRAVEL_COST_OFFSET
        )
        * x[(r_node[1], d_node[1])]
        for u, v in feasibility_graph.edges()
        for r_node, d_node in [((u, v) if u[0] == "rider" else (v, u))]
    )

    _add_assignment_constraints(
        prob, feasibility_graph, rider_nodes, driver_nodes, x
    )
    _add_feasibility_constraints(prob, feasibility_graph, x, p)
    _add_stability_constraints(
        prob, feasibility_graph, price_memory, delta, x, p
    )

    internal_tolerance = (
        fairness_tolerance * FAIRNESS_TOLERANCE_RELAXATION_MULTIPLIER
        if fairness_tolerance < FAIRNESS_RELAXATION_LIMIT
        else fairness_tolerance
    )
    _add_fairness_constraints(
        prob, feasibility_graph, driver_nodes, internal_tolerance, x, p
    )

    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=SOLVER_TIME_LIMIT)
    prob.solve(solver)
    status = pulp.LpStatus[prob.status]

    if status not in ["Optimal", "Feasible"] and (
        delta < PRICE_STABILITY_RELAXATION_LIMIT
        or fairness_tolerance < FAIRNESS_RELAXATION_LIMIT
    ):
        print(
            f"[WARN] JointOpt solver status {status} on window {window_id}. "
            "Re-running with relaxed constraints..."
        )
        relaxed_res = solve_joint_opt(
            feasibility_graph=feasibility_graph,
            price_memory=price_memory,
            earnings_history=earnings_history,
            delta=PRICE_STABILITY_RELAXATION_LIMIT,
            fairness_tolerance=FAIRNESS_RELAXATION_LIMIT,
            window_id=window_id,
        )
        if relaxed_res["solver_status"] in ["Optimal", "Feasible"]:
            relaxed_res["solver_status"] = "Relaxed"
        return relaxed_res

    return _format_results(feasibility_graph, x, p, status, start_time)