from __future__ import annotations

from collections import Counter
from typing import Dict, Set


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

    def record_captured(self, rank: str) -> None:
        if rank:
            self._captured_counts[rank] += 1

    def to_prompt(self) -> str:
        lines = ["[INFERRED ENEMY INFO] (imperfect)"]
        if self._mobile_positions:
            mobiles = ", ".join(sorted(self._mobile_positions))
            lines.append(f"- Enemy mobile pieces (not Bomb/Flag): {mobiles}")
        else:
            lines.append("- Enemy mobile pieces: unknown")

        if self._known_positions:
            known = ", ".join(f"{pos}={rank}" for pos, rank in sorted(self._known_positions.items()))
            lines.append(f"- Known enemy ranks: {known}")
        else:
            lines.append("- Known enemy ranks: none")

        if self._captured_counts:
            captured = ", ".join(f"{rank} x{count}" for rank, count in self._captured_counts.items())
            lines.append(f"- Captured enemy ranks: {captured}")
        else:
            lines.append("- Captured enemy ranks: none")

        return "\n".join(lines) + "\n"
