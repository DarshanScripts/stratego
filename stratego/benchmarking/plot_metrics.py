# stratego/benchmarking/plot_metrics.py
# [FIXED - 21 Jan 2026] Fixed range/int addition issues in win rate calculations

import pandas as pd
import matplotlib.pyplot as plt
import sys


def plot_from_csv(csv_path: str, rolling_window: int = 3):
    df = pd.read_csv(csv_path)

    # [FIXED - 21 Jan 2026] Convert range to list for proper indexing
    games = list(range(len(df)))

    # ===============================
    # 1. GAME LENGTH PER GAME
    # ===============================
    plt.figure()
    plt.plot(games, df["turns"], marker="o")
    plt.title("Game Length per Game")
    plt.xlabel("Game index")
    plt.ylabel("Turns")
    plt.grid(True)
    plt.show()

    # ===============================
    # 2. INVALID MOVES PER GAME
    # ===============================
    plt.figure()
    plt.plot(games, df["invalid_moves_p0"], label="P0 Invalid Moves", marker="o")
    plt.plot(games, df["invalid_moves_p1"], label="P1 Invalid Moves", marker="o")
    plt.title("Invalid Moves per Game")
    plt.xlabel("Game index")
    plt.ylabel("Invalid moves")
    plt.legend()
    plt.grid(True)
    plt.show()

    # ===============================
    # 3. ROLLING AVERAGE (STALLING)
    # ===============================
    df["rolling_turns"] = df["turns"].rolling(window=rolling_window).mean()

    plt.figure()
    plt.plot(games, df["turns"], alpha=0.3, label="Raw turns")
    plt.plot(games, df["rolling_turns"], linewidth=3, label=f"Rolling avg ({rolling_window})")
    plt.title("Game Stalling (Rolling Average of Turns)")
    plt.xlabel("Game index")
    plt.ylabel("Turns")
    plt.legend()
    plt.grid(True)
    plt.show()

    # ===============================
    # 4. TERMINATION REASONS
    # ===============================
    termination_counts = df["game_end_reason"].value_counts()

    plt.figure()
    termination_counts.plot(kind="bar")
    plt.title("Game Termination Reasons")
    plt.xlabel("Reason")
    plt.ylabel("Number of games")
    plt.grid(axis="y")
    plt.show()

    # ===============================
    # 5. CUMULATIVE WIN RATE
    # ===============================
    # [FIXED - 21 Jan 2026] Use len(df) instead of games+1 for proper calculation
    p0_wins = (df["winner"] == 0).cumsum()
    p1_wins = (df["winner"] == 1).cumsum()

    win_rate_p0 = p0_wins / range(1, len(df) + 1)
    win_rate_p1 = p1_wins / range(1, len(df) + 1)

    plt.figure()
    plt.plot(games, win_rate_p0, label="P0 Win Rate")
    plt.plot(games, win_rate_p1, label="P1 Win Rate")
    plt.title("Cumulative Win Rate")
    plt.xlabel("Game index")
    plt.ylabel("Win rate")
    plt.legend()
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python plot_metrics.py <benchmark_csv>")
        sys.exit(1)

    plot_from_csv(sys.argv[1])
