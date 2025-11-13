# stratego/memory_tracker.py
from __future__ import annotations
import datetime
from typing import List, Dict, Any, Optional

class GameMoveTracker:
    """
    In-memory tracker of all moves (for both players).
    Does NOT reveal piece identities, only events like capture/bomb/flag.
    Produces a clean text summary suitable for LLM prompt injection.
    """

    def __init__(self):
        self.turn: int = 0
        self.history: List[Dict[str, Any]] = []   # global chronological history

    # ---------------------------------------------------------
    # RECORDING MOVES
    # ---------------------------------------------------------
    def record(
        self,
        player: int,
        move: str,
        event: Optional[str] = None,   # "capture", "bomb", "flag", etc.
        extra: Optional[str] = None    # captured piece? "explosion"? etc.
    ):
        """
        Store one full move entry, but without revealing piece identities.
        """
        entry = {
            "turn": self.turn,
            "player": player,
            "move": move,   # e.g. "E4 F4"
            "event": event, # optional special event
            "extra": extra, # optional detail
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        }

        self.history.append(entry)
        self.turn += 1

    # ---------------------------------------------------------
    # ACCESSORS
    # ---------------------------------------------------------
    def get_player_moves(self, pid: int) -> List[Dict[str, Any]]:
        """Moves made by a specific player."""
        return [h for h in self.history if h["player"] == pid]

    def get_opponent_moves(self, pid: int) -> List[Dict[str, Any]]:
        """Moves made by the opponent."""
        return [h for h in self.history if h["player"] != pid]

    def last_move(self) -> Optional[Dict[str, Any]]:
        """Most recent move."""
        return self.history[-1] if self.history else None

    # ---------------------------------------------------------
    # GENERATE STRING FOR PROMPT
    # ---------------------------------------------------------
    def to_prompt_string(self, player_id: int) -> str:
        """
        Return a clean string that summarizes the match so far.
        No secret info, no piece identities, only moves + events.
        You append this AFTER the board slice in the LLM prompt.
        """

        if not self.history:
            return "No previous moves have been played.\n"

        lines = ["Game History (most recent last):"]

        for entry in self.history:
            turn = entry["turn"]
            pid  = entry["player"]
            move = entry["move"]
            event = entry["event"]
            extra = entry["extra"]

            if pid == player_id:
                prefix = f"Turn {turn}: You played {move}"
            else:
                prefix = f"Turn {turn}: Opponent played {move}"

            if event == "capture":
                prefix += " (capture occurred)"
            elif event == "bomb":
                prefix += " (bomb explosion)"
            elif event == "flag":
                prefix += " (FLAG CAPTURE — game-ending)"
            elif event == "invalid":
                prefix += " (invalid move?)"

            if extra:
                prefix += f" — {extra}"

            lines.append(prefix)

        return "\n".join(lines) + "\n"
