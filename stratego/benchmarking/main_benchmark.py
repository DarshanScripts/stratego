# stratego/benchmarking/main_benchmark.py

import argparse
from stratego.models.ollama_model import OllamaAgent
from .run_benchmark import run_benchmark


def benchmark():
    p = argparse.ArgumentParser()
    p.add_argument("--p0", default="llama3.1:70b")
    p.add_argument("--p1", default="gemma3:1b")
    p.add_argument("--size", default="6")
    p.add_argument("--games", default="3")
    args = p.parse_args()
    agent0 = OllamaAgent(args.p0)
    agent1 = OllamaAgent(args.p1)

    GAMES = int(args.games)
    SIZE = int(args.size)

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
