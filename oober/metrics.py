import numpy as np

def compute_wait_time(assignments, feasibility_graph):
    total_wait = 0.0

    for rider_id, driver_id, _ in assignments:
        total_wait += feasibility_graph[
            ('rider', rider_id)
        ][
            ('driver', driver_id)
        ]['travel_cost']

    return total_wait

import numpy as np

def compute_earnings_variance(assignments):
    earnings = {}

    for _, driver_id, price in assignments:
        earnings[driver_id] = earnings.get(driver_id, 0) + price

    if not earnings:
        return 0.0

    return float(np.var(list(earnings.values())))

def compute_price_deviation(
    assignments,
    price_memory,
    riders,
    delta
):
    rider_lookup = {
        rider['id']: rider
        for rider in riders
    }

    violations = 0
    checked = 0

    for rider_id, _, price in assignments:
        rider = rider_lookup[rider_id]

        corridor = (
            rider['origin_zone'],
            rider['dest_zone']
        )

        if corridor not in price_memory:
            continue

        prev_price = price_memory[corridor]

        checked += 1

        if abs(price - prev_price) > delta * prev_price:
            violations += 1

    return violations / checked if checked else 0.0

def compute_matching_rate(assignments, total_riders):
    if total_riders == 0:
        return 0.0

    return len(assignments) / total_riders