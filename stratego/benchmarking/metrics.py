# stratego/benchmarking/metrics.py

def init_metrics():
    return {
        "games": 0,

        # outcome
        "wins_p0": 0,
        "wins_p1": 0,
        "draws": 0,

        # termination reasons
        "end_invalid": 0,
        "end_flag": 0,
        "end_no_moves": 0,
        "end_turn_limit": 0,

        # accumulators
        "turns": [],
        "invalid_moves_p0": 0,
        "invalid_moves_p1": 0,
        "repetitions": []
    }


def update_metrics(metrics, result):
    metrics["games"] += 1

    winner = result["winner"]
    reason = result["reason"]

    # ----------------------------
    # GAME OUTCOME (STRICT)
    # ----------------------------
    if reason == "invalid_move":
        # invalid termination is NOT a draw
        pass
    elif winner == 0:
        metrics["wins_p0"] += 1
    elif winner == 1:
        metrics["wins_p1"] += 1
    else:
        metrics["draws"] += 1

    # ----------------------------
    # TERMINATION REASONS
    # ----------------------------
    if reason == "invalid_move":
        metrics["end_invalid"] += 1
    elif reason == "flag":
        metrics["end_flag"] += 1
    elif reason == "no_moves":
        metrics["end_no_moves"] += 1
    elif reason == "turn_limit":
        metrics["end_turn_limit"] += 1

    # ----------------------------
    # ACCUMULATORS
    # ----------------------------
    metrics["turns"].append(result["turns"])
    metrics["invalid_moves_p0"] += result["invalid_moves_p0"]
    metrics["invalid_moves_p1"] += result["invalid_moves_p1"]
    metrics["repetitions"].append(result["repetitions"])


def summarize(metrics):
    g = max(metrics["games"], 1)

    return {
        # === AVERAGE OF ALL GAMES ===
        "Wins P0": metrics["wins_p0"],
        "Wins P1": metrics["wins_p1"],
        "Losses P0": metrics["wins_p1"],
        "Losses P1": metrics["wins_p0"],
        "Draws": metrics["draws"],

        "Win Rate P0": metrics["wins_p0"] / g,
        "Win Rate P1": metrics["wins_p1"] / g,

        "Avg Game Length": sum(metrics["turns"]) / g,

        "Avg Invalid Moves P0": metrics["invalid_moves_p0"] / g,
        "Avg Invalid Moves P1": metrics["invalid_moves_p1"] / g,

        "Avg Repetitions": sum(metrics["repetitions"]) / g,

        # === TERMINATION ===
        "Ended by Invalid Move": metrics["end_invalid"],
        "Ended by Flag": metrics["end_flag"],
        "Ended by No Moves": metrics["end_no_moves"],
        "Ended by Turn Limit": metrics["end_turn_limit"],
    }
