# stratego/benchmarking/analysis/analyze_csv.py

import csv
import os
from collections import Counter
from datetime import datetime

OUTPUT_DIR = "stratego/benchmarking/output"
SUMMARY_DIR = "stratego/benchmarking/summaries"


def find_latest_benchmark_csv():
    files = [
        f for f in os.listdir(OUTPUT_DIR)
        if f.startswith("benchmark_") and f.endswith(".csv")
    ]

    if not files:
        raise FileNotFoundError("No benchmark CSV files found in output/")

    files.sort()
    return os.path.join(OUTPUT_DIR, files[-1])


def analyze_benchmark_csv(csv_path: str):
    games = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            games.append(row)

    total_games = len(games)

    wins = Counter()
    terminations = Counter()

    turns = []
    invalid_p0 = 0
    invalid_p1 = 0
    repetitions = []

    for g in games:
        winner = g["winner"]
        reason = g["game_end_reason"]

        if winner == "0":
            wins["p0"] += 1
        elif winner == "1":
            wins["p1"] += 1
        else:
            wins["draw"] += 1

        terminations[reason] += 1

        turns.append(int(g["turns"]))
        invalid_p0 += int(g["invalid_moves_p0"])
        invalid_p1 += int(g["invalid_moves_p1"])
        repetitions.append(int(g["repetitions"]))

    summary = {
        "total_games": total_games,
        "wins_p0": wins["p0"],
        "wins_p1": wins["p1"],
        "draws": wins["draw"],
        "win_rate_p0": wins["p0"] / total_games if total_games else 0,
        "win_rate_p1": wins["p1"] / total_games if total_games else 0,
        "avg_game_length": sum(turns) / total_games if total_games else 0,
        "avg_invalid_moves_p0": invalid_p0 / total_games if total_games else 0,
        "avg_invalid_moves_p1": invalid_p1 / total_games if total_games else 0,
        "avg_repetitions": sum(repetitions) / total_games if total_games else 0,
    }

    return summary, terminations


def write_summary_csv(summary, terminations, source_csv):
    os.makedirs(SUMMARY_DIR, exist_ok=True)

    base = os.path.basename(source_csv).replace("benchmark_", "").replace(".csv", "")
    out_path = os.path.join(SUMMARY_DIR, f"summary_{base}.csv")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow(["metric", "value"])
        for k, v in summary.items():
            writer.writerow([k, v])

        writer.writerow([])
        writer.writerow(["termination_reason", "count"])
        for reason, count in terminations.items():
            writer.writerow([reason, count])

    print(f"[OK] Summary written to {out_path}")


if __name__ == "__main__":
    latest_csv = find_latest_benchmark_csv()
    print(f"[INFO] Analyzing {latest_csv}")

    summary, terminations = analyze_benchmark_csv(latest_csv)
    write_summary_csv(summary, terminations, latest_csv)
