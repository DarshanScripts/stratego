# stratego/benchmarking/csv_logger.py

import csv
import os
from datetime import datetime

BENCHMARK_DIR = "stratego/benchmarking/output/benchmarks"
SUMMARY_DIR = "stratego/benchmarking/output/summaries"


def create_benchmark_csv(batch_size: int):
    """
    Creates ONE CSV file for ONE benchmark run (multiple games).
    """
    os.makedirs(BENCHMARK_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"benchmark_{timestamp}_games{batch_size}.csv"
    path = os.path.join(BENCHMARK_DIR, filename)

    f = open(path, "w", newline="", encoding="utf-8")
    writer = csv.writer(f)

    writer.writerow([
        "game_id",
        "model_p0",
        "model_p1",
        "board_size",
        "winner",
        "turns",
        "invalid_moves_p0",
        "invalid_moves_p1",
        "repetitions",
        "flag_captured",
        "game_end_reason"
    ])

    return f, writer, path


def write_summary_csv(summary: dict, source_csv: str):
    """
    Writes ONE summary CSV corresponding to ONE benchmark CSV.
    """
    os.makedirs(SUMMARY_DIR, exist_ok=True)

    base = os.path.basename(source_csv).replace(".csv", "")
    path = os.path.join(SUMMARY_DIR, f"{base}_SUMMARY.csv")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow(["metric", "value"])
        writer.writerow(["source_benchmark_csv", source_csv])

        for k, v in summary.items():
            writer.writerow([k, v])
