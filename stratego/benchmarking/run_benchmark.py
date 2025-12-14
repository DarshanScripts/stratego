# stratego/benchmarking/run_benchmark.py
# IMPORTANT: must be first

from .run_game import run_game
from .metrics import init_metrics, update_metrics, summarize


def run_benchmark(agent0, agent1, games=10, size=6):
    metrics = init_metrics()

    for seed in range(games):
        result = run_game(agent0, agent1, size=size, seed=seed)
        update_metrics(metrics, result)

    return summarize(metrics)
