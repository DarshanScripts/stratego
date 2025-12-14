# stratego/benchmarking/main_benchmark.py
from stratego.benchmarking.textarena_bootstrap import *

from stratego.models.ollama_model import OllamaAgent
#from .agents import OllamaAgent
from .run_benchmark import run_benchmark


def benchmark():
    agent0 = OllamaAgent("llama3.1:70b")
    agent1 = OllamaAgent("gemma3:1b")

    SIZE = 4
    GAMES = 3

    summary = run_benchmark(
        agent0,
        agent1,
        games=GAMES,
        size=SIZE
    )

    print("\n=== BENCHMARK SUMMARY ===")
    for k, v in summary.items():
        print(f"{k:25s}: {v}")


if __name__ == "__main__":
    benchmark()
