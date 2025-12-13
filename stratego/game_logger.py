# stratego/game_logger.py
from __future__ import annotations
import csv, os, datetime
from typing import Optional, List


class GameLogger:
    """
    One CSV file per game stored in logs/games/ folder.
    
    CSV Fields for training:
      - turn, player, model_name
      - move, from_pos, to_pos, piece_type
      - board_state, available_moves, move_direction
      - target_piece, battle_outcome
      - prompt_name
      - game_winner, game_result (filled post-game)
    """
    def __init__(self, out_dir: str, game_id: Optional[str] = None, prompt_name: str = "", game_type: str = "standard", board_size: int = 10):
        # Create games subfolder
        games_dir = os.path.join(out_dir, "games")
        os.makedirs(games_dir, exist_ok=True)
        
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.game_id = game_id or ts
        self.prompt_name = prompt_name
        self.game_type = game_type  # "standard", "duel", or "custom"
        self.board_size = board_size
        self.path = os.path.join(games_dir, f"{self.game_id}.csv")
        self._f = open(self.path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(
            self._f,
            fieldnames=[
                "turn", "player", "model_name",
                "move", "from_pos", "to_pos", "piece_type", "outcome",
            ],
            quoting=csv.QUOTE_MINIMAL,
            escapechar="\\"
        )
        self._writer.writeheader()
        self._rows: List[dict] = []  # Store rows for post-game update

    def log_move(
        self,
        turn: int,
        player: int,
        move: str,
        model_name: str = "",
        src: str = "",
        dst: str = "",
        piece_type: str = "",
        outcome: str = "",
        board_state: str = "",
        available_moves: str = "",
        move_direction: str = "",
        target_piece: str = "",
        battle_outcome: str = "",
    ):
        row = {
            "turn": turn,
            "player": player,
            "model_name": model_name,
            "move": move,
            "from_pos": src,
            "to_pos": dst,
            "piece_type": piece_type,
            "outcome": outcome,
        })
        self._f.flush()
    
    def finalize_game(self, winner: Optional[int], game_result: str = ""):
        """
        Rewrite CSV with game outcome in every row.
        This allows each move to be labeled with the game result for training.
        """
        self._f.close()
        
        # Update all rows with game outcome
        winner_str = str(winner) if winner is not None else "draw"
        for row in self._rows:
            row["game_winner"] = winner_str
            row["game_result"] = game_result
        
        # Rewrite the file with updated data
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "turn", "player", "model_name",
                    "move", "from_pos", "to_pos", "piece_type",
                    "board_state", "available_moves", "move_direction",
                    "target_piece", "battle_outcome",
                    "prompt_name", "game_type", "board_size",
                    "game_winner", "game_result",
                ],
                quoting=csv.QUOTE_MINIMAL,
                escapechar="\\"
            )
            writer.writeheader()
            writer.writerows(self._rows)
    
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
