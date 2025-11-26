# stratego/logging.py
from __future__ import annotations
import csv, os, datetime
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from stratego.problem_tracker import ProblemTracker, MistakeSummary


class GameLogger:
    """
    One CSV file per game stored in logs/games/ folder.
    
    CSV Fields:
      - Game info: game_id, turn, timestamp
      - Player info: player, model_name
      - Move info: move, from_pos, to_pos, piece_type, piece_rank
      - Battle info: outcome, enemy_piece, enemy_rank, battle_result
      - Analysis: is_repeated, is_back_forth, move_distance, direction
    """
    def __init__(self, out_dir: str, game_id: Optional[str] = None, meta: Optional[Dict[str, Any]] = None):
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
                # Game context
                "game_id", "turn", "timestamp",
                # Player info
                "player", "model_name",
                # Move details
                "move", "from_pos", "to_pos", "piece_type", "piece_rank",
                # Outcome
                "outcome",
                # Move analysis
                "is_repeated", "repeat_count", "direction",
                # Response timing
                "response_time_ms",
            ],
            quoting=csv.QUOTE_MINIMAL,
            escapechar="\\"
        )
        self._writer.writeheader()
        self._meta = meta or {}
        self._move_counts = {}  # Track move repetitions
        
        # Initialize problem tracker
        self._problem_tracker: Optional[ProblemTracker] = None
        self._init_problem_tracker()
    
    def _init_problem_tracker(self):
        """Initialize the problem tracker for real-time issue detection."""
        try:
            from stratego.problem_tracker import ProblemTracker
            self._problem_tracker = ProblemTracker(self.game_id)
        except ImportError:
            print("Warning: ProblemTracker not available")
            self._problem_tracker = None

    def _now(self) -> str:
        return datetime.datetime.now().isoformat(timespec="seconds")
    
    def _calculate_direction(self, src: str, dst: str) -> str:
        """Calculate move direction (N/S/E/W)."""
        if not src or not dst:
            return ""
        try:
            src_row = ord(src[0]) - ord('A')
            src_col = int(src[1:])
            dst_row = ord(dst[0]) - ord('A')
            dst_col = int(dst[1:])
            
            if dst_row < src_row:
                return "N"  # Moving up (towards enemy for P0)
            elif dst_row > src_row:
                return "S"  # Moving down
            elif dst_col > src_col:
                return "E"  # Moving right
            elif dst_col < src_col:
                return "W"  # Moving left
        except:
            pass
        return ""

    def log_move(
        self,
        turn: int,
        player: int,
        move: str,
        model_name: str = "",
        src: str = "",
        dst: str = "",
        piece_type: str = "",
        piece_rank: int = None,
        outcome: str = "move",
        was_repeated: bool = False,
        response_time_ms: int = None,
    ):
        # Track repetitions
        move_key = f"{player}:{move}"
        self._move_counts[move_key] = self._move_counts.get(move_key, 0) + 1
        repeat_count = self._move_counts[move_key]
        
        # Calculate direction
        direction = self._calculate_direction(src, dst)
        
        self._writer.writerow({
            "game_id": self.game_id,
            "turn": turn,
            "timestamp": self._now(),
            "player": player,
            "model_name": model_name,
            "move": move,
            "from_pos": src,
            "to_pos": dst,
            "piece_type": piece_type,
            "piece_rank": piece_rank if piece_rank is not None else "",
            "outcome": outcome,
            "is_repeated": "yes" if was_repeated else "no",
            "repeat_count": repeat_count,
            "direction": direction,
            "response_time_ms": response_time_ms if response_time_ms else "",
        })
        self._f.flush()
        
        # Also log to problem tracker for real-time analysis
        if self._problem_tracker:
            self._problem_tracker.log_move(
                turn=turn,
                player=player,
                move=move,
                piece_type=piece_type,
                outcome=outcome,
                src=src,
                dst=dst
            )
    
    def get_problem_summary(self, winner: Optional[int] = None):
        """Get the mistake summary for this game."""
        if self._problem_tracker:
            return self._problem_tracker.generate_summary(winner=winner)
        return None
    
    def should_trigger_optimization(self) -> bool:
        """Check if problems warrant prompt optimization."""
        if self._problem_tracker:
            return self._problem_tracker.should_trigger_optimization()
        return False

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
