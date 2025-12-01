# stratego/datasets/builder.py
"""
Build Hugging Face Datasets from Stratego game CSV logs.
"""

from __future__ import annotations
import os
import csv
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    from datasets import Dataset
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    Dataset = None


class GameDatasetBuilder:
    """
    Builds a Hugging Face Dataset from CSV game logs.
    """
    
    def __init__(self, logs_dir: str = "logs/games"):
        if not HF_AVAILABLE:
            raise ImportError(
                "Hugging Face datasets not installed. "
                "Run: pip install datasets huggingface_hub"
            )
        self.logs_dir = Path(logs_dir)
        self.moves: List[Dict[str, Any]] = []
        
    def _parse_csv_file(self, csv_path: Path) -> List[Dict[str, Any]]:
        """Parse a single game CSV file into move records."""
        moves = []
        game_id = csv_path.stem
        
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    move_record = {
                        "game_id": game_id,
                        "turn": int(row.get("turn", 0)),
                        "player": int(row.get("player", 0)),
                        "model_name": row.get("model_name", "unknown"),
                        "move": row.get("move", ""),
                        "from_pos": row.get("from_pos", ""),
                        "to_pos": row.get("to_pos", ""),
                        "piece_type": row.get("piece_type", ""),
                        # New training-relevant fields
                        "board_state": row.get("board_state", ""),
                        "available_moves": row.get("available_moves", ""),
                        "move_direction": row.get("move_direction", ""),
                        "target_piece": row.get("target_piece", ""),
                        "battle_outcome": row.get("battle_outcome", ""),
                        "prompt_name": row.get("prompt_name", ""),
                        "game_type": row.get("game_type", "standard"),
                        "board_size": int(row.get("board_size", 10)) if row.get("board_size") else 10,
                        "game_winner": row.get("game_winner", ""),
                        "game_result": row.get("game_result", ""),
                    }
                    moves.append(move_record)
        except Exception as e:
            print(f"Error parsing {csv_path}: {e}")
            
        return moves
    
    def scan_logs(self) -> int:
        """Scan logs directory and load all CSV files."""
        self.moves = []
        
        if not self.logs_dir.exists():
            return 0
            
        csv_files = list(self.logs_dir.glob("*.csv"))
        
        for csv_path in csv_files:
            game_moves = self._parse_csv_file(csv_path)
            self.moves.extend(game_moves)
                
        return len(csv_files)
    
    def build(self) -> "Dataset":
        """Build a Dataset from all game logs."""
        if not self.moves:
            self.scan_logs()
            
        if not self.moves:
            raise ValueError("No moves found in logs directory.")
            
        return Dataset.from_list(self.moves)


def build_dataset_from_logs(logs_dir: str = "logs/games") -> "Dataset":
    """
    Build a dataset from game logs.
    
    Args:
        logs_dir: Path to directory containing game CSV files
        
    Returns:
        Dataset with all moves
    """
    builder = GameDatasetBuilder(logs_dir)
    builder.scan_logs()
    return builder.build()
