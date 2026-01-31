from __future__ import annotations

from typing import Dict, Set, Tuple

ROW_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _pos_from_rc(r: int, c: int) -> str:
    return f"{ROW_LABELS[r]}{c}"


def positions_for_player(board, player_id: int) -> Set[str]:
    positions: Set[str] = set()
    if not board:
        return positions
    for r, row in enumerate(board):
        for c, cell in enumerate(row):
            if isinstance(cell, dict) and cell.get("player") == player_id:
                positions.add(_pos_from_rc(r, c))
    return positions


def positions_for_enemy(board, player_id: int) -> Set[str]:
    positions: Set[str] = set()
    if not board:
        return positions
    for r, row in enumerate(board):
        for c, cell in enumerate(row):
            if isinstance(cell, dict) and cell.get("player") != player_id:
                positions.add(_pos_from_rc(r, c))
    return positions


def count_pieces_by_player(board) -> Dict[int, int]:
    counts: Dict[int, int] = {}
    if not board:
        return counts
    for row in board:
        for cell in row:
            if isinstance(cell, dict):
                pid = cell.get("player")
                counts[pid] = counts.get(pid, 0) + 1
    return counts


def count_movable_by_player(board) -> Dict[int, int]:
    counts: Dict[int, int] = {}
    if not board:
        return counts
    for row in board:
        for cell in row:
            if isinstance(cell, dict):
                if cell.get("rank") in ("Bomb", "Flag"):
                    continue
                pid = cell.get("player")
                counts[pid] = counts.get(pid, 0) + 1
    return counts

