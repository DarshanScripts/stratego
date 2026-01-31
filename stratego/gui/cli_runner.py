from __future__ import annotations

import argparse
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

from stratego.config import (
    CRITICAL_WARNING_TURN,
    CUSTOM_ENV,
    DEFAULT_ENV,
    DUEL_ENV,
    MAX_AGENT_ATTEMPTS,
    STALLING_WARNING_TURN,
)
from stratego.env.stratego_env import StrategoEnv
from stratego.main import build_agent
from stratego.utils.attack_policy import (
    choose_attack_move,
    choose_chase_move,
    list_attack_moves,
    reverse_move,
)
from stratego.utils.board_stats import (
    count_movable_by_player,
    count_pieces_by_player,
    positions_for_enemy,
)
from stratego.utils.game_move_tracker import GameMoveTracker as MoveTrackerClass
from stratego.utils.move_processor import process_move
from stratego.utils.opponent_inference import OpponentInference
from stratego.utils.parsing import extract_board_block_lines, extract_forbidden, extract_legal_moves

StateCallback = Callable[[dict], None]

RANK_SHORT = {
    "Flag": "FL",
    "Spy": "SP",
    "Scout": "SC",
    "Miner": "MN",
    "Sergeant": "SG",
    "Lieutenant": "LT",
    "Captain": "CP",
    "Major": "MJ",
    "Colonel": "CL",
    "General": "GN",
    "Marshal": "MS",
    "Bomb": "BM",
}


def _call_agent_with_abort(
    agent,
    obs: str,
    stop_event: Optional[object],
    timeout_s: float = 20.0,
) -> Tuple[str, Optional[Exception], bool]:
    result: Dict[str, object] = {"action": "", "error": None, "done": False}

    def _run() -> None:
        try:
            action = agent(obs) if callable(agent) else agent.act(obs)
            result["action"] = action
        except Exception as exc:  # pragma: no cover - bubble up
            result["error"] = exc
        finally:
            result["done"] = True

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if stop_event is not None and getattr(stop_event, "is_set", lambda: False)():
            return "", None, True
        if result["done"]:
            return str(result["action"]), result["error"], False
        time.sleep(0.05)
    return "", None, False


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--p0", required=True, help="Player 0 model (ollama:MODEL or MODEL)")
    p.add_argument("--p1", required=True, help="Player 1 model (ollama:MODEL or MODEL)")
    p.add_argument("--mode", choices=["Original", "Duel", "Custom"], default="Custom")
    p.add_argument("--size", type=int, default=6)
    p.add_argument("--prompt", default="base")
    p.add_argument("--max_turns", type=int, default=200)
    args = p.parse_args()

    run_match(
        p0_model=normalize_model(args.p0),
        p1_model=normalize_model(args.p1),
        mode=args.mode,
        size=args.size,
        prompt_name=args.prompt,
        max_turns=args.max_turns,
    )


def run_match(
    *,
    p0_model: str,
    p1_model: str,
    mode: str,
    size: int,
    prompt_name: str = "base",
    max_turns: int = 200,
    on_state: Optional[StateCallback] = None,
    stop_event: Optional[object] = None,
) -> None:
    agent0 = build_agent(normalize_model(p0_model), prompt_name)
    agent1 = build_agent(normalize_model(p1_model), prompt_name)

    if mode == "Original":
        env_id = DEFAULT_ENV
        env = StrategoEnv(env_id=env_id)
    elif mode == "Duel":
        env_id = DUEL_ENV
        env = StrategoEnv(env_id=env_id)
    else:
        env_id = CUSTOM_ENV
        env = StrategoEnv(env_id=env_id, size=size)

    env.reset(num_players=2)

    tracker = MoveTrackerClass()
    inferences = {0: OpponentInference(), 1: OpponentInference()}
    move_history = {0: [], 1: []}
    eliminated: Dict[int, List[str]] = {0: [], 1: []}
    turn = 0
    no_capture_streak = 0
    done = False
    display_turn = 0
    last_signature: Optional[str] = None
    initial_counts = count_pieces_by_player(env.env.board)

    while not done:
        if stop_event is not None and getattr(stop_event, "is_set", lambda: False)():
            break
        if max_turns and turn >= max_turns:
            break

        player_id, observation = env.get_observation()
        movable_counts = count_movable_by_player(env.env.board)
        for viewer_id in (0, 1):
            enemy_positions = positions_for_enemy(env.env.board, viewer_id)
            inferences[viewer_id].update_enemy_positions(enemy_positions)
            inferences[viewer_id].set_enemy_remaining(
                total=len(enemy_positions),
                movable=movable_counts.get(1 - viewer_id, 0),
            )

        board_tokens, owners = board_to_tokens_and_owners(env.env.board, size)
        signature = "|".join(",".join(row) for row in board_tokens) if board_tokens else ""
        if signature and signature != last_signature:
            last_signature = signature
            display_turn += 1

        if on_state:
            on_state({
                "player_id": player_id,
                "board": board_tokens,
                "owners": owners,
                "display_turn": display_turn,
                "engine_turn": turn,
                "eliminated": eliminated,
            })

        history_str = tracker.to_prompt_string(player_id)
        obs = observation + history_str
        obs += "\n" + inferences[player_id].to_prompt()
        obs += (
            "\n[ATTACK POLICY]\n"
            "- Prefer probing attacks against enemy pieces that have moved (not Bomb/Flag).\n"
            "- Use low-rank pieces (Scout/Miner/Sergeant) to reveal or trade safely.\n"
            "- Avoid endless shuffling; if safe options exist, attack to gain information.\n"
            "- If there are immobile positions not confirmed as Bombs, treat them as Flag candidates and press toward them.\n"
            "- Use probes to identify the Flag quickly; do not delay when Flag candidates exist.\n"
        )
        if turn > STALLING_WARNING_TURN:
            obs += "\n\n[SYSTEM MESSAGE]: The game is stalling. You MUST ATTACK or ADVANCE immediately. Passive play is forbidden."
        if turn > CRITICAL_WARNING_TURN:
            obs += "\n[CRITICAL]: STOP MOVING BACK AND FORTH. Pick a piece and move it FORWARD now."
        if max_turns:
            remaining_turns = max(max_turns - turn, 0)
            obs += f"\n[TURN LIMIT]: {remaining_turns} turns remaining. End the game within this limit or you will NOT win."
        if no_capture_streak >= 10:
            obs += "\n[FORCE ATTACK]: No pieces have been captured in 10 turns. You MUST ATTACK an enemy piece now."

        agent = agent0 if player_id == 0 else agent1
        if hasattr(agent, "set_move_history"):
            agent.set_move_history(move_history[player_id][-10:])

        action = ""
        max_agent_attempts = MAX_AGENT_ATTEMPTS
        for _ in range(max_agent_attempts):
            action, error, aborted = _call_agent_with_abort(
                agent,
                obs,
                stop_event,
            )
            if aborted:
                break
            if error:
                raise error
            if action:
                break
        if stop_event is not None and getattr(stop_event, "is_set", lambda: False)():
            break
        if not action:
            legal = extract_legal_moves(obs)
            forbidden = set(extract_forbidden(obs))
            legal_filtered = [m for m in legal if m not in forbidden] or legal
            if legal_filtered:
                action = legal_filtered[0]

        legal = extract_legal_moves(obs)
        forbidden = set(extract_forbidden(obs))
        legal_filtered = [m for m in legal if m not in forbidden] or legal
        attack_moves = list_attack_moves(legal_filtered, env.env.board, player_id)
        immobile_positions = inferences[player_id].get_immobile_positions()
        bomb_positions = inferences[player_id].get_bomb_positions()
        enemy_positions = positions_for_enemy(env.env.board, player_id)
        enemy_total = len(enemy_positions)
        threshold = max(2, int(initial_counts.get(1 - player_id, 0) * 0.25))
        aggressive = enemy_total <= threshold or movable_counts.get(1 - player_id, 0) <= threshold
        last_move = move_history[player_id][-1]["move"] if move_history[player_id] else ""
        avoid_move = reverse_move(last_move) if last_move else None

        if attack_moves:
            miner_bomb_moves = [
                mv for mv in attack_moves if mv[2] in bomb_positions and mv[3] == "Miner"
            ]
            if miner_bomb_moves:
                forced = choose_attack_move(miner_bomb_moves, prefer_miner_to_bomb=False)
                if forced and forced != action:
                    action = forced
            elif aggressive:
                forced = choose_attack_move(
                    attack_moves,
                    immobile_targets=immobile_positions,
                    bomb_positions=bomb_positions,
                    prefer_low_rank=True,
                    prefer_miner_to_bomb=True,
                )
                if forced and forced != action:
                    action = forced
            elif aggressive:
                chase = choose_chase_move(
                    legal_filtered,
                    enemy_positions,
                    avoid_move=avoid_move,
                )
                if chase and chase != action:
                    action = chase
        elif aggressive:
            chase = choose_chase_move(
                legal_filtered,
                enemy_positions,
                avoid_move=avoid_move,
            )
            if chase and chase != action:
                action = chase

        move_history[player_id].append({"turn": turn, "move": action})

        move_details = process_move(
            action=action,
            board=env.env.board,
            observation=obs,
            player_id=player_id,
        )

        done, _ = env.step(action)
        turn += 1

        battle_outcome = ""
        if move_details.target_piece:
            dst_row = ord(move_details.dst_pos[0]) - ord("A")
            dst_col = int(move_details.dst_pos[1:])
            cell_after = env.env.board[dst_row][dst_col]

            if cell_after is None:
                battle_outcome = "draw"
            elif isinstance(cell_after, dict):
                if cell_after.get("player") == player_id:
                    battle_outcome = "won"
                else:
                    battle_outcome = "lost"

        if move_details.target_piece:
            no_capture_streak = 0
        else:
            no_capture_streak += 1

        update_inference(inferences, move_details, battle_outcome, player_id)
        update_eliminated(eliminated, move_details, battle_outcome, player_id)

        tracker.record(player=player_id, move=action, event=None, extra=None)

    state = env.get_state()
    rewards = getattr(state, "rewards", None)
    winner = -1
    if rewards:
        max_reward = max(rewards.values())
        winners = [player for player, reward in rewards.items() if reward == max_reward]
        if len(winners) == 1:
            winner = winners[0]

    reason = state.game_info.get(0, {}).get("reason", "") if hasattr(state, "game_info") else ""
    winner_model = "draw"
    if winner == 0:
        winner_model = p0_model
    elif winner == 1:
        winner_model = p1_model

    if on_state:
        on_state({
            "type": "result",
            "winner": winner,
            "winner_model": winner_model,
            "reason": reason,
        })


def normalize_model(model: str) -> str:
    if model.startswith("ollama:") or model.startswith("hf:"):
        return model
    return f"ollama:{model}"


def parse_board_tokens(observation: str, size: int) -> Tuple[List[List[str]], str]:
    block = extract_board_block_lines(observation, size)
    if not block:
        return [], ""
    rows = block[1:]
    tokens: List[List[str]] = []
    for line in rows:
        parts = line.split()
        if len(parts) < 2:
            continue
        tokens.append(parts[1:])
    signature = "|".join(",".join(row) for row in tokens)
    return tokens, signature


def board_to_tokens_and_owners(board, size: int) -> Tuple[List[List[str]], List[List[Optional[int]]]]:
    if not board:
        return [], []
    tokens: List[List[str]] = []
    owners: List[List[Optional[int]]] = []
    for r in range(size):
        row_tokens: List[str] = []
        row_owners: List[Optional[int]] = []
        row = board[r]
        for c in range(size):
            cell = row[c]
            if cell is None:
                row_tokens.append(".")
                row_owners.append(None)
            elif cell == "~":
                row_tokens.append("~")
                row_owners.append(None)
            elif isinstance(cell, dict):
                rank = cell.get("rank", "?")
                row_tokens.append(RANK_SHORT.get(rank, rank))
                row_owners.append(cell.get("player"))
            else:
                row_tokens.append(str(cell))
                row_owners.append(None)
        tokens.append(row_tokens)
        owners.append(row_owners)
    return tokens, owners


def update_inference(inferences, move_details, battle_outcome: str, player_id: int) -> None:
    def update_for(viewer_id: int, mover_id: int) -> None:
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

    update_for(0, player_id)
    update_for(1, player_id)


def update_eliminated(eliminated: Dict[int, List[str]], move_details, battle_outcome: str, player_id: int) -> None:
    if not move_details.target_piece:
        return
    if battle_outcome == "won":
        eliminated[1 - player_id].append(move_details.target_piece)
    elif battle_outcome == "lost":
        eliminated[player_id].append(move_details.piece_type or "Unknown")
    elif battle_outcome == "draw":
        eliminated[player_id].append(move_details.piece_type or "Unknown")
        eliminated[1 - player_id].append(move_details.target_piece)
