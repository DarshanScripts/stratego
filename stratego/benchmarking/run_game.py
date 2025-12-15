# stratego/benchmarking/run_game.py

import textarena as ta
from stratego.env.stratego_env import StrategoEnv


def get_last_board_observation(state, player_id):
    for obs in reversed(state.observations[player_id]):
        if ta.ObservationType.GAME_BOARD in obs:
            for elem in obs:
                if isinstance(elem, str):
                    return elem
    return ""


def run_game(agent0, agent1, size=6, seed=None):
    env = StrategoEnv(env_id = "Stratego-custom",size=size)
    env.reset(num_players=2, seed=seed)

    invalid_moves = {0: 0, 1: 0}
    repetitions = 0
    turns = 0

    done = False
    winner = None
    reason_verbose = "Unknown termination reason"
    flag_captured = False

    while not done:
        state = env.get_state()
        rep = env.repetition_count()
        pid = state.current_player_id
        agent = agent0 if pid == 0 else agent1

        obs = get_last_board_observation(state, pid)
        action = agent(obs) if callable(agent) else agent.act(obs)

        done, _ = env.step(action)
        turns += 1

        if state.game_info.get(pid, {}).get("invalid_move"):
            invalid_moves[pid] += 1

        repetitions += rep.get(pid, 0)

        if done:
            gs = state.game_state
            gi = state.game_info

            if gs.get("termination") == "invalid":
                reason_verbose = f"Invalid move: {gs.get('invalid_reason', 'Invalid move')}"

            else:
                raw = gi.get("reason", "")
                # Normalize reason to string for downstream metrics/logs
                if isinstance(raw, (list, tuple)):
                    raw_reason = "; ".join(map(str, raw))
                else:
                    raw_reason = str(raw)

                raw_lower = raw_reason.lower()

                if "flag" in raw_lower:
                    flag_captured = True
                    reason_verbose = raw_reason
                elif "no legal moves" in raw_lower or "no more movable pieces" in raw_lower or "no moves" in raw_lower:
                    reason_verbose = "Opponent had no legal moves"
                elif "stalemate" in raw_lower:
                    reason_verbose = "Stalemate"
                elif "turn limit" in raw_lower:
                    reason_verbose = "Turn limit reached"
                elif "repetition" in raw_lower:
                    reason_verbose = "Two-squares repetition rule violation"
                else:
                    reason_verbose = raw_reason or "Game ended without explicit winner"

            # TextArena does not store a winner in game_info; derive from rewards
            rewards = getattr(state, "rewards", None)
            if rewards:
                max_reward = max(rewards.values())
                winners = [player for player, reward in rewards.items() if reward == max_reward]
                if len(winners) == 1:
                    winner = winners[0]
                else:
                    winner = -1

    return {
        "winner": winner if winner is not None else -1,
        "turns": turns,
        "invalid_moves_p0": invalid_moves[0],
        "invalid_moves_p1": invalid_moves[1],
        "repetitions": repetitions,
        "flag_captured": flag_captured,
        "game_end_reason": reason_verbose
    }
