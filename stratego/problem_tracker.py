"""
ProblemTracker: Tracks specific mistakes during Stratego gameplay.

Collects detailed information about:
- Exact moves that were repeated
- Which pieces were overused
- Battle outcomes with details
- Back-and-forth movement patterns
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter


@dataclass
class MistakeSummary:
    """Summary of specific mistakes from a game."""
    game_id: str
    total_turns: int
    winner: Optional[int] = None
    
    # Specific repeated moves: {move: [turn_numbers]}
    repeated_moves: Dict[str, List[int]] = field(default_factory=dict)
    
    # Back-and-forth patterns: [(pos1, pos2, count)]
    back_and_forth: List[Tuple[str, str, int]] = field(default_factory=list)
    
    # Piece usage: {piece_type: count}
    piece_usage: Dict[str, int] = field(default_factory=dict)
    
    # Battle details: [(attacker_piece, outcome, turn)]
    battle_details: List[Dict[str, Any]] = field(default_factory=list)
    
    # Stats
    battles_won: int = 0
    battles_lost: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "total_turns": self.total_turns,
            "winner": self.winner,
            "repeated_moves": self.repeated_moves,
            "back_and_forth": self.back_and_forth,
            "piece_usage": self.piece_usage,
            "battle_details": self.battle_details,
            "battles_won": self.battles_won,
            "battles_lost": self.battles_lost
        }


class ProblemTracker:
    """
    Tracks specific mistakes during a Stratego game.
    
    Usage:
        tracker = ProblemTracker(game_id="game_001")
        tracker.log_move(turn, player, move, piece_type, outcome)
        summary = tracker.generate_summary(winner=0)
    """
    
    def __init__(self, game_id: str):
        self.game_id = game_id
        self.turn_count = 0
        
        # Per-player tracking
        self.player_moves: Dict[int, List[Dict[str, Any]]] = {0: [], 1: []}
        
        # Move occurrence tracking: {move: [turn_numbers]}
        self.move_occurrences: Dict[str, List[int]] = {}
        
        # Piece usage
        self.piece_usage: Counter = Counter()
        
        # Battle tracking
        self.battles: List[Dict[str, Any]] = []
        self.battles_won = 0
        self.battles_lost = 0
        
        # Position tracking for back-and-forth detection
        self.position_sequences: Dict[int, List[Tuple[str, str]]] = {0: [], 1: []}
        
    def log_move(
        self,
        turn: int,
        player: int,
        move: str,
        piece_type: str = "",
        outcome: str = "",
        src: str = "",
        dst: str = "",
        **kwargs
    ):
        """Log a move and track potential mistakes."""
        self.turn_count = max(self.turn_count, turn)
        
        # Store move details
        move_data = {
            "turn": turn,
            "move": move,
            "piece_type": piece_type,
            "outcome": outcome,
            "src": src,
            "dst": dst
        }
        self.player_moves[player].append(move_data)
        
        # Track move occurrences for repetition detection
        if move not in self.move_occurrences:
            self.move_occurrences[move] = []
        self.move_occurrences[move].append(turn)
        
        # Track piece usage
        if piece_type:
            self.piece_usage[piece_type] += 1
        
        # Track position sequence for back-and-forth detection
        if src and dst:
            self.position_sequences[player].append((src, dst))
        
        # Track battle outcomes
        if "won" in outcome.lower():
            self.battles_won += 1
            self.battles.append({
                "turn": turn,
                "piece": piece_type,
                "outcome": "won",
                "player": player
            })
        elif "lost" in outcome.lower():
            self.battles_lost += 1
            self.battles.append({
                "turn": turn,
                "piece": piece_type,
                "outcome": "lost",
                "player": player
            })
    
    def _detect_back_and_forth(self) -> List[Tuple[str, str, int]]:
        """Detect back-and-forth movement patterns."""
        patterns = []
        
        for player in [0, 1]:
            seq = self.position_sequences[player]
            if len(seq) < 2:
                continue
            
            # Count A→B followed by B→A patterns
            pattern_counts: Counter = Counter()
            for i in range(len(seq) - 1):
                src1, dst1 = seq[i]
                src2, dst2 = seq[i + 1]
                
                # Check if it's a back-and-forth (A→B then B→A)
                if dst1 == src2 and src1 == dst2:
                    # Normalize the pattern (alphabetically sort)
                    pattern = tuple(sorted([src1, dst1]))
                    pattern_counts[pattern] += 1
            
            # Add patterns that occurred multiple times
            for (pos1, pos2), count in pattern_counts.items():
                if count >= 2:
                    patterns.append((pos1, pos2, count))
        
        return patterns
    
    def _get_repeated_moves(self) -> Dict[str, List[int]]:
        """Get moves that were repeated (appeared more than once)."""
        return {
            move: turns 
            for move, turns in self.move_occurrences.items() 
            if len(turns) >= 2
        }
    
    def generate_summary(self, winner: Optional[int] = None) -> MistakeSummary:
        """Generate summary of specific mistakes."""
        return MistakeSummary(
            game_id=self.game_id,
            total_turns=self.turn_count,
            winner=winner,
            repeated_moves=self._get_repeated_moves(),
            back_and_forth=self._detect_back_and_forth(),
            piece_usage=dict(self.piece_usage),
            battle_details=self.battles,
            battles_won=self.battles_won,
            battles_lost=self.battles_lost
        )
    
    def should_trigger_optimization(self) -> bool:
        """Check if there are enough mistakes to warrant prompt update."""
        total_moves = len(self.player_moves[0]) + len(self.player_moves[1])
        if total_moves < 5:
            return False
        
        # Check for repeated moves
        repeated = self._get_repeated_moves()
        has_repetitions = len(repeated) > 0
        
        # Check for battle losses
        has_losses = self.battles_lost > self.battles_won
        
        # Check for back-and-forth
        has_back_forth = len(self._detect_back_and_forth()) > 0
        
        return has_repetitions or has_losses or has_back_forth
