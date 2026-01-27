# stratego/benchmarking/run_game.py

import random
import textarena as ta
from stratego.env.stratego_env import StrategoEnv
from stratego.utils.game_move_tracker import GameMoveTracker as MoveTrackerClass
from stratego.utils.move_processor import process_move
from stratego.utils.opponent_inference import OpponentInference
from stratego.utils.parsing import extract_legal_moves, extract_forbidden
from stratego.utils.attack_policy import choose_attack_move, list_attack_moves, reverse_move
from stratego.utils.board_stats import (
    count_movable_by_player,
    count_pieces_by_player,
    positions_for_enemy,
)


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


def run_game(agent0, agent1, size=6, seed=None, start_player=None, max_turns=200):
    env = StrategoEnv(env_id="Stratego-custom", size=size)
    env.reset(num_players=2, seed=seed)
    if start_player in (0, 1):
        try:
            env.env.state.current_player_id = start_player
            if hasattr(env.env, "_observe_current_state"):
                env.env._observe_current_state(player_id=start_player)
        except Exception:
            pass

    invalid_moves = {0: 0, 1: 0}
    repetitions = 0
    turns = 0
    no_capture_streak = 0
    tracker = MoveTrackerClass()
    inferences = {0: OpponentInference(), 1: OpponentInference()}
    move_history = {0: [], 1: []}
    initial_counts = count_pieces_by_player(env.env.board)

    done = False
    winner = None
    reason_verbose = "Unknown termination reason"
    flag_captured = False

    while not done:
        if max_turns and turns >= max_turns:
            reason_verbose = "Turn limit reached"
            winner = -1
            break
        state = env.get_state()
        rep = env.repetition_count()
        pid = state.current_player_id
        agent = agent0 if pid == 0 else agent1
        movable_counts = count_movable_by_player(env.env.board)

        for viewer_id in (0, 1):
            enemy_positions = positions_for_enemy(env.env.board, viewer_id)
            inferences[viewer_id].update_enemy_positions(enemy_positions)
            inferences[viewer_id].set_enemy_remaining(
                total=len(enemy_positions),
                movable=movable_counts.get(1 - viewer_id, 0),
            )

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
            "- If the enemy has only a few pieces left, prioritize attacking.\n"
            "- Probe immobile enemy pieces with low ranks to test for Bombs.\n"
            "- If a Bomb is confirmed and a Miner can attack it, do so.\n"
            "- If there are immobile positions not confirmed as Bombs, treat them as Flag candidates and press toward them.\n"
            "- Use probes to identify the Flag quickly; do not delay when Flag candidates exist.\n"
        )
        if hasattr(agent, "set_move_history"):
            agent.set_move_history(move_history[pid][-10:])

        if turns > 20:
            obs += "\n\n[SYSTEM MESSAGE]: The game is stalling. You MUST ATTACK or ADVANCE immediately. Passive play is forbidden."
        if turns > 50:
            obs += "\n[CRITICAL]: STOP MOVING BACK AND FORTH. Pick a piece and move it FORWARD now."
        if max_turns:
            remaining_turns = max(max_turns - turns, 0)
            obs += f"\n[TURN LIMIT]: {remaining_turns} turns remaining. End the game within this limit or you will NOT win."
        if no_capture_streak >= 10:
            obs += "\n[FORCE ATTACK]: No pieces have been captured in 10 turns. You MUST ATTACK an enemy piece now."

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

        if turns > 30:
            legal = extract_legal_moves(obs)
            forbidden = set(extract_forbidden(obs))
            legal_filtered = [m for m in legal if m not in forbidden] or legal
            attack_moves = list_attack_moves(legal_filtered, env.env.board, pid)
            if attack_moves:
                forced = choose_attack_move(attack_moves, prefer_low_rank=True)
                if forced and forced != action:
                    action = forced
            elif turns > 50 and legal_filtered:
                last_move = move_history[pid][-1]["move"] if move_history[pid] else ""
                avoid_move = reverse_move(last_move) if last_move else None
                if avoid_move and avoid_move in legal_filtered:
                    for mv in legal_filtered:
                        if mv != avoid_move:
                            action = mv
                            break

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
        state = env.get_state()
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

        if move_details.target_piece:
            no_capture_streak = 0
        else:
            no_capture_streak += 1

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
                    if move_details.target_piece == "Bomb":
                        if battle_outcome == "lost":
                            inferences[viewer_id].note_bomb_confirmed(move_details.dst_pos)
                        else:
                            inferences[viewer_id].note_bomb_removed(move_details.dst_pos)
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

            if move_details.target_piece == "Flag" and battle_outcome == "won":
                flag_captured = True

            if gs.get("termination") == "invalid":
                reason_verbose = f"Invalid move: {gs.get('invalid_reason', 'Invalid move')}"
            else:
                raw = gi.get(pid, {}).get("reason", "")
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
                elif raw_reason:
                    reason_verbose = raw_reason
                else:
                    reason_verbose = "Game ended without explicit winner"

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
