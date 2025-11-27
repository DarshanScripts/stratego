# stratego/logging.py
from __future__ import annotations
import csv, os, datetime
from typing import Optional, Dict, Any


class GameLogger:
    """
    One CSV file per game stored in logs/games/ folder.
    
    CSV Fields (minimal - everything else computed post-game):
      - turn, player, model_name
      - move, from_pos, to_pos, piece_type
    """
    def __init__(self, out_dir: str, game_id: Optional[str] = None):
        # Create games subfolder
        games_dir = os.path.join(out_dir, "games")
        os.makedirs(games_dir, exist_ok=True)
        
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.game_id = game_id or ts
        self.path = os.path.join(games_dir, f"{self.game_id}.csv")
        self._f = open(self.path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(
            self._f,
            fieldnames=[
                "turn", "player", "model_name",
                "move", "from_pos", "to_pos", "piece_type",
            ],
            quoting=csv.QUOTE_MINIMAL,
            escapechar="\\"
        )
        self._writer.writeheader()

    def log_move(
        self,
        turn: int,
        player: int,
        move: str,
        model_name: str = "",
        src: str = "",
        dst: str = "",
        piece_type: str = "",
    ):
        self._writer.writerow({
            "turn": turn,
            "player": player,
            "model_name": model_name,
            "move": move,
            "from_pos": src,
            "to_pos": dst,
            "piece_type": piece_type,
        })
        self._f.flush()
    
    def close(self):
        try:
            self._f.close()
        except Exception:
            pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
