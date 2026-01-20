# stratego/benchmarking/run_benchmark.py

from .run_game import run_game
from .metrics import init_metrics, update_metrics, summarize
from .csv_logger import create_benchmark_csv, write_summary_csv


def run_benchmark(agent0, agent1, games=10, size=6, max_turns=200):
    metrics = init_metrics()

    f, writer, benchmark_csv = create_benchmark_csv(games)

    for game_id in range(games):
        p0 = agent0
        p1 = agent1

        print(f"Starting game {game_id + 1}/{games} (P0: {p0.model_name}, P1: {p1.model_name})")
        result = run_game(p0, p1, size=size, seed=game_id, start_player=None, max_turns=max_turns)
        winner_model = ""
        if result["winner"] == 0:
            winner_model = p0.model_name
        elif result["winner"] == 1:
            winner_model = p1.model_name
        else:
            winner_model = "draw"

        writer.writerow([
            game_id,
            p0.model_name,
            p1.model_name,
            size,
            result["winner"],
            result["turns"],
            result["invalid_moves_p0"],
            result["invalid_moves_p1"],
            result["repetitions"],
            result["flag_captured"],
            result["game_end_reason"],
            winner_model
        ])

        update_metrics(metrics, result)
        print(f"Finished game {game_id + 1}/{games} | Winner: {winner_model} | Turns: {result['turns']}")

    f.close()

    summary = summarize(metrics)
    write_summary_csv(summary, benchmark_csv)

    return summary, benchmark_csv
