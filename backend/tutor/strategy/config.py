# Strategy configuration

STRATEGY_THRESHOLDS = {
    "mastery_low": 0.4,
    "mastery_high": 0.7,
    "decay_revision": 0.7
}

# scoring weights (can be tuned later)
STRATEGY_WEIGHTS = {
    "mastery": 0.6,
    "decay": 0.4
}

# available strategies
STRATEGIES = [
    "definition",
    "worked_example",
    "practice",
    "revision"
]