# stratego/benchmarking/metrics.py

def init_metrics():
    return {
        "games": 0,
        "wins_p0": 0,
        "wins_p1": 0,
        "draws": 0,
        "end_draw": 0,
        "end_invalid": 0,
        "end_flag": 0,
        "end_no_moves": 0,
        "end_turn_limit": 0,
        "turns": [],
        "invalid_p0": 0,
        "invalid_p1": 0,
        "repetitions": []
    }


def update_metrics(m, r):
    m["games"] += 1

    if r["winner"] == 0:
        m["wins_p0"] += 1
    elif r["winner"] == 1:
        m["wins_p1"] += 1
    else:
        m["draws"] += 1

    reason = r["game_end_reason"] or ""
    reason_lower = reason.lower()
    winner = r.get("winner", -1)
    flag_captured = r.get("flag_captured", False)

    # If a flag was captured, trust that signal first
    if flag_captured or "flag" in reason_lower:
        m["end_flag"] += 1
    else:
        if winner == -1:
            # Only count draws when the game result is actually a draw
            if "invalid" in reason_lower:
                m["end_invalid"] += 1
            elif "flag" in reason_lower:
                m["end_flag"] += 1
            elif ("no legal" in reason_lower or
                  "no more movable pieces" in reason_lower or
                  "no moves" in reason_lower):
                m["end_draw"] += 1
            elif "turn limit" in reason_lower:
                m["end_turn_limit"] += 1
            elif "draw" in reason_lower or "repetition" in reason_lower or "stalemate" in reason_lower:
                m["end_draw"] += 1
            else:
                m["end_draw"] += 1  # fallback for unknown draw reasons
        else:
            # Non-draw outcomes
            if "invalid" in reason_lower:
                m["end_invalid"] += 1
            elif "repetition" in reason_lower:
                m["end_no_moves"] += 1
            elif "flag" in reason_lower:
                m["end_flag"] += 1
            elif ("no legal" in reason_lower or
                  "no more movable pieces" in reason_lower or
                  "no moves" in reason_lower):
                m["end_no_moves"] += 1
            elif "turn limit" in reason_lower:
                m["end_turn_limit"] += 1
            else:
                # If we have a winner but no clear reason, assume win by flag if captured, else by no-moves.
                if flag_captured:
                    m["end_flag"] += 1
                else:
                    m["end_no_moves"] += 1

    m["turns"].append(r["turns"])
    m["invalid_p0"] += r["invalid_moves_p0"]
    m["invalid_p1"] += r["invalid_moves_p1"]
    m["repetitions"].append(r["repetitions"])


def summarize(m):
    g = max(1, m["games"])
    return {
        "Games": g,
        "Wins P0": m["wins_p0"],
        "Wins P1": m["wins_p1"],
        "Draws": m["draws"],
        "Win Rate P0": m["wins_p0"] / g,
        "Win Rate P1": m["wins_p1"] / g,
        "Avg Turns": sum(m["turns"]) / g,
        "Avg Invalid Moves P0": m["invalid_p0"] / g,
        "Avg Invalid Moves P1": m["invalid_p1"] / g,
        "Avg Repetitions": sum(m["repetitions"]) / g,
        "Ended by Invalid": m["end_invalid"],
        "Ended by Flag": m["end_flag"],
        "Ended by Draw": m["end_draw"],
        "Ended by No Moves": m["end_no_moves"],
        "Ended by Turn Limit": m["end_turn_limit"]
    }
