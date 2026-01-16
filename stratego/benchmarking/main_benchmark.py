# stratego/benchmarking/main_benchmark.py

import argparse
from stratego.main import build_agent
from .run_benchmark import run_benchmark


def benchmark():
    p = argparse.ArgumentParser()
    p.add_argument("--p0", default="ollama:llama3.1:70b")
    p.add_argument("--p1", default="ollama:gemma3:1b")
    p.add_argument("--prompt", default="base", help="Prompt preset name (e.g. base|concise|adaptive)")
    p.add_argument("--size", default="6")
    p.add_argument("--games", default="3")
    args = p.parse_args()
    agent0 = build_agent(args.p0, args.prompt)
    agent1 = build_agent(args.p1, args.prompt)

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
