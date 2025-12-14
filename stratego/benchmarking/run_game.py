# stratego/benchmarking/run_game.py

import textarena as ta
from stratego.env.backup.edited_env.StrategoCustom.env import StrategoCustomEnv


def get_last_board_observation(state, player_id):
    for obs in reversed(state.observations[player_id]):
        if ta.ObservationType.GAME_BOARD in obs:
            for elem in obs:
                if isinstance(elem, str):
                    return elem
    return ""


def run_game(agent0, agent1, size=6, seed=None):
    env = StrategoCustomEnv(size=size)
    env.reset(num_players=2, seed=seed)

    agent0.move_history = []
    agent1.move_history = []

    invalid_moves = {0: 0, 1: 0}
    repetitions = 0
    turns = 0

    done = False
    winner = None
    reason = "unknown"

    while not done:
        pid = env.state.current_player_id
        agent = agent0 if pid == 0 else agent1

        obs = get_last_board_observation(env.state, pid)

        action = agent(obs) if callable(agent) else agent.act(obs)

        done, info = env.step(action)
        turns += 1

        if env.state.game_info.get(pid, {}).get("invalid_move"):
            invalid_moves[pid] += 1

        repetitions += env.repetition_count.get(pid, 0)

        if done:
            game_info = env.state.game_info
            game_state = env.state.game_state

            # -----------------------------
            # INVALID TERMINATION (your rule)
            # -----------------------------
            if game_state.get("termination") == "invalid":
                winner = None
                reason = "invalid_move"

            # -----------------------------
            # NORMAL TERMINATION
            # -----------------------------
            else:
                winner = game_info.get("winner", None)
                reason_raw = game_info.get("reason", "")

                if "Flag" in reason_raw:
                    reason = "flag"
                elif "No legal moves" in reason_raw:
                    reason = "no_moves"
                elif "Stalemate" in reason_raw:
                    reason = "draw"
                elif "Turn limit" in reason_raw:
                    reason = "turn_limit"

    return {
        "winner": winner,
        "reason": reason,
        "turns": turns,
        "invalid_moves_p0": invalid_moves[0],
        "invalid_moves_p1": invalid_moves[1],
        "repetitions": repetitions,
        "board_size": size,
    }
