# stratego/benchmarking/run_game.py

import random
import textarena as ta
from stratego.env.stratego_env import StrategoEnv
from stratego.utils.game_move_tracker import GameMoveTracker as MoveTrackerClass
from stratego.utils.move_processor import process_move
from stratego.utils.opponent_inference import OpponentInference
from stratego.utils.parsing import extract_legal_moves, extract_forbidden


def get_last_board_observation(state, player_id):
    for obs in reversed(state.observations[player_id]):
        if ta.ObservationType.GAME_BOARD in obs:
            for elem in obs:
                if isinstance(elem, str):
                    return elem
    return ""

def get_last_prompt_observation(state, player_id):
    for obs in reversed(state.observations[player_id]):
        if ta.ObservationType.PROMPT in obs:
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
    tracker = MoveTrackerClass()
    inferences = {0: OpponentInference(), 1: OpponentInference()}
    move_history = {0: [], 1: []}

    done = False
    winner = None
    reason_verbose = "Unknown termination reason"
    flag_captured = False

    while not done:
        state = env.get_state()
        rep = env.repetition_count()
        pid = state.current_player_id
        agent = agent0 if pid == 0 else agent1

        base_prompt = get_last_prompt_observation(state, pid)
        board_obs = get_last_board_observation(state, pid)
        obs = base_prompt + "\n" + board_obs if base_prompt else board_obs
        history_str = tracker.to_prompt_string(pid)
        obs = obs + history_str
        obs += "\n" + inferences[pid].to_prompt()
        obs += (
            "\n[ATTACK POLICY]\n"
            "- Prefer probing attacks against enemy pieces that have moved (not Bomb/Flag).\n"
            "- Use low-rank pieces (Scout/Miner/Sergeant) to reveal or trade safely.\n"
            "- Avoid endless shuffling; if safe options exist, attack to gain information.\n"
        )
        if hasattr(agent, "set_move_history"):
            agent.set_move_history(move_history[pid][-10:])

        if turns > 20:
            obs += "\n\n[SYSTEM MESSAGE]: The game is stalling. You MUST ATTACK or ADVANCE immediately. Passive play is forbidden."
        if turns > 50:
            obs += "\n[CRITICAL]: STOP MOVING BACK AND FORTH. Pick a piece and move it FORWARD now."

        action = ""
        max_agent_attempts = 3
        for _ in range(max_agent_attempts):
            action = agent(obs) if callable(agent) else agent.act(obs)
            if action:
                break
        if not action:
            legal = extract_legal_moves(obs)
            forbidden = set(extract_forbidden(obs))
            legal_filtered = [m for m in legal if m not in forbidden] or legal
            if legal_filtered:
                action = random.choice(legal_filtered)

        move_history[pid].append({
            "turn": turns,
            "move": action,
            "text": f"Turn {turns}: You played {action}"
        })

        move_details = process_move(
            action=action,
            board=env.env.board,
            observation=obs,
            player_id=pid
        )

        done, _ = env.step(action)
        turns += 1

        if state.game_info.get(pid, {}).get("invalid_move"):
            invalid_moves[pid] += 1

        repetitions += rep.get(pid, 0)

        battle_outcome = ""
        if move_details.target_piece:
            dst_row = ord(move_details.dst_pos[0]) - ord('A')
            dst_col = int(move_details.dst_pos[1:])
            cell_after = env.env.board[dst_row][dst_col]

            if cell_after is None:
                battle_outcome = "draw"
            elif isinstance(cell_after, dict):
                if cell_after.get('player') == pid:
                    battle_outcome = "won"
                else:
                    battle_outcome = "lost"

        def update_inference_for_player(viewer_id: int, mover_id: int):
            opponent_id = 1 - viewer_id
            battle_occurred = bool(move_details.target_piece)
            if mover_id == opponent_id:
                inferences[viewer_id].note_enemy_moved(
                    src_pos=move_details.src_pos,
                    dst_pos=move_details.dst_pos,
                )
                if battle_occurred:
                    if battle_outcome == "won":
                        if move_details.piece_type:
                            inferences[viewer_id].note_enemy_revealed(
                                pos=move_details.dst_pos,
                                rank=move_details.piece_type,
                            )
                    else:
                        inferences[viewer_id].note_enemy_removed(move_details.dst_pos)
                        if battle_outcome == "lost" and move_details.piece_type:
                            inferences[viewer_id].record_captured(move_details.piece_type)
            else:
                if battle_occurred and move_details.target_piece:
                    if battle_outcome == "lost":
                        inferences[viewer_id].note_enemy_revealed(
                            pos=move_details.dst_pos,
                            rank=move_details.target_piece,
                        )
                    else:
                        inferences[viewer_id].note_enemy_removed(move_details.dst_pos)
                        if battle_outcome == "won":
                            inferences[viewer_id].record_captured(move_details.target_piece)

        update_inference_for_player(0, pid)
        update_inference_for_player(1, pid)

        tracker.record(
            player=pid,
            move=action,
            event=None,
            extra=None
        )

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
