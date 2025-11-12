# stratego/logging.py
from __future__ import annotations
import csv, os, datetime
from typing import Optional, Dict, Any

class GameLogger:
    """
    One CSV file per game.
    We write two kinds of rows:
      - type=prompt  (one row per player with the initial prompt)
      - type=move    (one row per move)
    """
    def __init__(self, out_dir: str, game_id: Optional[str] = None, meta: Optional[Dict[str, Any]] = None):
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.game_id = game_id or ts
        self.path = os.path.join(out_dir, f"{ts}_{self.game_id}.csv")
        self._f = open(self.path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(
            self._f,
            fieldnames=[
                "game_id","timestamp","type",
                # prompts
                "player","model_name","role","prompt",
                # moves
                "turn","move","from","to","outcome","captured","board_after",
                # freeform
                "meta_json",
            ],
            quoting=csv.QUOTE_MINIMAL,
            escapechar="\\"
        )
        self._writer.writeheader()
        self._meta = meta or {}

    def _now(self) -> str:
        return datetime.datetime.now().isoformat(timespec="seconds")

    def log_prompt(self, player: int, model_name: str, prompt: str, role: str = "initial"):
        self._writer.writerow({
            "game_id": self.game_id,
            "timestamp": self._now(),
            "type": "prompt",
            "player": player,
            "model_name": model_name,
            "role": role,
            "prompt": prompt,
            "turn": "",
            "move": "",
            "from": "",
            "to": "",
            "outcome": "",
            "captured": "",
            "board_after": "",
            "meta_json": "",
        })
        self._f.flush()

    def log_move(
        self,
        turn: int,
        player: int,
        move: str,
        model_name: str = "",
        src: str = "",
        dst: str = "",
        outcome: str = "",
        captured: str = "",
        board_after: str = "",
    ):
        self._writer.writerow({
            "game_id": self.game_id,
            "timestamp": self._now(),
            "type": "move",
            "player": player,
            "model_name": "",
            "model_name": model_name,
            "role": "",
            "prompt": "",
            "turn": turn,
            "move": move,
            "from": src,
            "to": dst,
            "outcome": outcome,
            "captured": captured,
            "board_after": board_after,
            "meta_json": "",
        })
        self._f.flush()

    def close(self):
        try:
            self._f.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
