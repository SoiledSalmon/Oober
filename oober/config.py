"""Centralized configuration settings for the Oober project."""

# Optimization Defaults
DEFAULT_DELTA: float = 0.10
DEFAULT_FAIRNESS_TOLERANCE: float = 0.30
DEFAULT_NUM_ZONES: int = 10
DEFAULT_MAX_HOPS: int = 2

# ILP Solver settings
SOLVER_TIME_LIMIT: int = 30
TRAVEL_COST_OFFSET: float = -10000.0

# Synthetic Data Generation Settings (Riders)
RIDER_WTP_MEAN: float = 50.0
RIDER_WTP_STD: float = 15.0
RIDER_WTP_MIN: float = 20.0
RIDER_WTP_MAX: float = 100.0

# Synthetic Data Generation Settings (Drivers)
DRIVER_MAF_MEAN: float = 30.0
DRIVER_MAF_STD: float = 8.0
DRIVER_MAF_MIN: float = 10.0
DRIVER_MAF_MAX: float = 60.0
