from __future__ import annotations

from collections import Counter
from typing import Dict, Optional, Set


class OpponentInference:
    """
    Track imperfect, publicly knowable information about the opponent.
    - Enemy pieces that moved are not Bomb/Flag.
    - Battle reveals ranks of involved pieces.
    """

    def __init__(self) -> None:
        self._mobile_positions: Set[str] = set()
        self._known_positions: Dict[str, str] = {}
        self._captured_counts: Counter[str] = Counter()
        self._seen_positions: Set[str] = set()
        self._bomb_positions: Set[str] = set()
        self._enemy_remaining_total: Optional[int] = None
        self._enemy_remaining_movable: Optional[int] = None

    def note_enemy_moved(self, src_pos: str, dst_pos: str) -> None:
        if src_pos:
            self._mobile_positions.discard(src_pos)
            self._known_positions.pop(src_pos, None)
        if dst_pos:
            self._mobile_positions.add(dst_pos)

    def note_enemy_revealed(self, pos: str, rank: str) -> None:
        if pos and rank:
            self._known_positions[pos] = rank
            self._mobile_positions.add(pos)

    def note_enemy_removed(self, pos: str) -> None:
        if pos:
            self._mobile_positions.discard(pos)
            self._known_positions.pop(pos, None)
            self._seen_positions.discard(pos)
            self._bomb_positions.discard(pos)

    def record_captured(self, rank: str) -> None:
        if rank:
            self._captured_counts[rank] += 1

    def update_enemy_positions(self, positions: Set[str]) -> None:
        if positions is None:
            return
        self._seen_positions = set(positions)
        # Drop bombs that are no longer present on the board.
        self._bomb_positions.intersection_update(self._seen_positions)
        self._mobile_positions.intersection_update(self._seen_positions)
        self._known_positions = {
            pos: rank for pos, rank in self._known_positions.items() if pos in self._seen_positions
        }

    def note_bomb_confirmed(self, pos: str) -> None:
        if pos:
            self._bomb_positions.add(pos)

    def note_bomb_removed(self, pos: str) -> None:
        if pos:
            self._bomb_positions.discard(pos)

    def set_enemy_remaining(self, total: Optional[int], movable: Optional[int]) -> None:
        self._enemy_remaining_total = total
        self._enemy_remaining_movable = movable

    def get_immobile_positions(self) -> Set[str]:
        return self._seen_positions - self._mobile_positions

    def get_bomb_positions(self) -> Set[str]:
        return set(self._bomb_positions)

    def get_flag_candidates(self) -> Set[str]:
        return self.get_immobile_positions() - self._bomb_positions

    def to_prompt(self) -> str:
        lines = ["[INFERRED ENEMY INFO] (imperfect)"]
        if self._mobile_positions:
            mobiles = ", ".join(sorted(self._mobile_positions))
            lines.append(f"- Enemy mobile pieces (not Bomb/Flag): {mobiles}")
        else:
            lines.append("- Enemy mobile pieces: unknown")

        immobile = self.get_immobile_positions()
        if immobile:
            immobile_str = ", ".join(sorted(immobile))
            lines.append(f"- Enemy immobile positions (likely Bomb/Flag): {immobile_str}")
        else:
            lines.append("- Enemy immobile positions: unknown")

        if self._known_positions:
            known = ", ".join(f"{pos}={rank}" for pos, rank in sorted(self._known_positions.items()))
            lines.append(f"- Known enemy ranks: {known}")
        else:
            lines.append("- Known enemy ranks: none")

        if self._bomb_positions:
            bombs = ", ".join(sorted(self._bomb_positions))
            lines.append(f"- Confirmed Bomb positions: {bombs}")
        else:
            lines.append("- Confirmed Bomb positions: none")

        flag_candidates = self.get_flag_candidates()
        if flag_candidates:
            candidates = ", ".join(sorted(flag_candidates))
            lines.append(f"- Flag candidates (immobile, not Bomb): {candidates}")
        else:
            lines.append("- Flag candidates: unknown")

        if self._captured_counts:
            captured = ", ".join(f"{rank} x{count}" for rank, count in self._captured_counts.items())
            lines.append(f"- Captured enemy ranks: {captured}")
        else:
            lines.append("- Captured enemy ranks: none")

        if self._enemy_remaining_total is not None:
            movable = (
                str(self._enemy_remaining_movable)
                if self._enemy_remaining_movable is not None
                else "unknown"
            )
            lines.append(f"- Enemy pieces remaining: {self._enemy_remaining_total} total, {movable} movable")

        return "\n".join(lines) + "\n"
