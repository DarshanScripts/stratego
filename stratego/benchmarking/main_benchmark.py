# stratego/benchmarking/main_benchmark.py

from stratego.models.ollama_model import OllamaAgent
from .run_benchmark import run_benchmark


def benchmark():
    agent0 = OllamaAgent("llama3.1:70b")
    agent1 = OllamaAgent("gemma3:1b")

    GAMES = 3
    SIZE = 4

    summary, csv_path = run_benchmark(
        agent0,
        agent1,
        games=GAMES,
        size=SIZE
    )

    print("\n=== BENCHMARK SUMMARY ===")
    print(f"Source CSV: {csv_path}")
    for k, v in summary.items():
        print(f"{k:25s}: {v}")


def main():
    benchmark()
