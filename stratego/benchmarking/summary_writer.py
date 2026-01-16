# stratego/benchmarking/summary_csv_logger.py

import csv
import os
from datetime import datetime

OUTPUT_DIR = "stratego/benchmarking/output/summaries"


def write_summary_csv(
    summary: dict,
    games: int,
    size: int,
    model_p0: str,
    model_p1: str,
    source_benchmark_csv: str
):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"summary_{timestamp}_{games}games.csv"

    with open(os.path.join(OUTPUT_DIR, filename), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "games",
            "board_size",
            "model_p0",
            "model_p1",
            "source_benchmark_csv",
            "wins_p0",
            "wins_p1",
            "draws",
            "win_rate_p0",
            "win_rate_p1",
            "ended_invalid",
            "ended_flag",
            "ended_no_moves",
            "ended_turn_limit",
            "avg_game_length",
            "avg_invalid_moves_p0",
            "avg_invalid_moves_p1",
            "avg_repetitions"
        ])

        writer.writerow([
            games,
            size,
            model_p0,
            model_p1,
            source_benchmark_csv,
            summary["Wins P0"],
            summary["Wins P1"],
            summary["Draws"],
            summary["Win Rate P0"],
            summary["Win Rate P1"],
            summary["Ended by Invalid Move"],
            summary["Ended by Flag"],
            summary["Ended by No Moves"],
            summary["Ended by Turn Limit"],
            summary["Avg Game Length"],
            summary["Avg Invalid Moves P0"],
            summary["Avg Invalid Moves P1"],
            summary["Avg Repetitions"]
        ])
