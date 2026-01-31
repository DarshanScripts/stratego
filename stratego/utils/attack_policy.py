from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Set, Tuple

from stratego.utils.move_processor import get_piece_at_position, parse_move

RANK_ORDER = {
    "Spy": 1,
    "Scout": 2,
    "Miner": 3,
    "Sergeant": 4,
    "Lieutenant": 5,
    "Captain": 6,
    "Major": 7,
    "Colonel": 8,
    "General": 9,
    "Marshal": 10,
    "Bomb": 11,
    "Flag": 0,
}

LOW_RANKS = {"Spy", "Scout", "Miner", "Sergeant"}


def _piece_owner_and_rank(board, position: str) -> Tuple[Optional[int], Optional[str]]:
    if not position:
        return None, None
    try:
        row = ord(position[0]) - ord("A")
        col = int(position[1:])
        cell = board[row][col]
        if isinstance(cell, dict):
            return cell.get("player"), cell.get("rank")
    except (IndexError, ValueError, TypeError):
        pass
    return None, None


def list_attack_moves(legal_moves: Sequence[str], board, player_id: int) -> List[Tuple[str, str, str, str]]:
    attacks: List[Tuple[str, str, str, str]] = []
    for mv in legal_moves:
        src_pos, dst_pos = parse_move(mv)
        if not src_pos or not dst_pos:
            continue
        owner, _ = _piece_owner_and_rank(board, dst_pos)
        if owner is None or owner == player_id:
            continue
        rank = get_piece_at_position(board, src_pos)
        attacks.append((mv, src_pos, dst_pos, rank))
    return attacks


def choose_attack_move(
    attack_moves: Iterable[Tuple[str, str, str, str]],
    *,
    immobile_targets: Optional[Set[str]] = None,
    bomb_positions: Optional[Set[str]] = None,
    prefer_low_rank: bool = True,
    prefer_miner_to_bomb: bool = True,
) -> Optional[str]:
    moves = list(attack_moves)
    if not moves:
        return None

    immobile_targets = immobile_targets or set()
    bomb_positions = bomb_positions or set()

    if prefer_miner_to_bomb and bomb_positions:
        miner_bomb = [
            mv for mv in moves if mv[2] in bomb_positions and mv[3] == "Miner"
        ]
        if miner_bomb:
            return _pick_low_rank(miner_bomb) if prefer_low_rank else miner_bomb[0][0]

    if immobile_targets:
        immobile_attacks = [mv for mv in moves if mv[2] in immobile_targets]
        if immobile_attacks:
            return _pick_low_rank(immobile_attacks) if prefer_low_rank else immobile_attacks[0][0]

    return _pick_low_rank(moves) if prefer_low_rank else moves[0][0]


def _pick_low_rank(moves: List[Tuple[str, str, str, str]]) -> str:
    ranked = sorted(
        moves,
        key=lambda mv: (RANK_ORDER.get(mv[3], 99), mv[0]),
    )
    return ranked[0][0]


def reverse_move(move: str) -> Optional[str]:
    src_pos, dst_pos = parse_move(move)
    if src_pos and dst_pos:
        return f"[{dst_pos} {src_pos}]"
    return None


def choose_chase_move(
    legal_moves: Sequence[str],
    enemy_positions: Iterable[str],
    *,
    avoid_move: Optional[str] = None,
) -> Optional[str]:
    enemy_coords = [_pos_to_rc(p) for p in enemy_positions]
    enemy_coords = [p for p in enemy_coords if p is not None]
    if not enemy_coords:
        return None

    candidates = []
    for mv in legal_moves:
        if avoid_move and mv == avoid_move:
            continue
        _, dst = parse_move(mv)
        dst_rc = _pos_to_rc(dst)
        if dst_rc is None:
            continue
        dist = min(_manhattan(dst_rc, e) for e in enemy_coords)
        candidates.append((dist, mv))

    if not candidates:
        candidates = []
        for mv in legal_moves:
            _, dst = parse_move(mv)
            dst_rc = _pos_to_rc(dst)
            if dst_rc is None:
                continue
            dist = min(_manhattan(dst_rc, e) for e in enemy_coords)
            candidates.append((dist, mv))

    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]))
    return candidates[0][1]


def _pos_to_rc(position: str) -> Optional[Tuple[int, int]]:
    if not position:
        return None
    try:
        row = ord(position[0]) - ord("A")
        col = int(position[1:])
        return row, col
    except (IndexError, ValueError, TypeError):
        return None


def _manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
