# stratego/benchmarking/run_benchmark.py

from .run_game import run_game
from .metrics import init_metrics, update_metrics, summarize
from .csv_logger import create_benchmark_csv, write_summary_csv


def run_benchmark(agent0, agent1, games=10, size=6):
    metrics = init_metrics()

    f, writer, benchmark_csv = create_benchmark_csv(games)

    for game_id in range(games):
        result = run_game(agent0, agent1, size=size, seed=game_id)

        writer.writerow([
            game_id,
            agent0.model_name,
            agent1.model_name,
            size,
            result["winner"],
            result["turns"],
            result["invalid_moves_p0"],
            result["invalid_moves_p1"],
            result["repetitions"],
            result["flag_captured"],
            result["game_end_reason"]
        ])

        update_metrics(metrics, result)

    f.close()

    summary = summarize(metrics)
    write_summary_csv(summary, benchmark_csv)

    return summary, benchmark_csv
