"""
Game Analyzer: Computes detailed statistics from CSV and uses LLM for strategic insights.

Flow:
1. Read CSV game log
2. Compute statistics (piece usage, repetitions, battles, etc.)
3. Send structured summary to LLM
4. Get Stratego-specific feedback
5. Update prompt
"""

import os
import csv
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import ollama


@dataclass
class PlayerStats:
    """Statistics for one player in a game."""
    player_id: int
    model_name: str = ""
    total_moves: int = 0
    
    # Piece usage
    moves_by_piece: Dict[str, int] = field(default_factory=dict) # piece_type -> count | number of moves that piece made
    
    # Repetition analysis
    move_counts: Dict[str, int] = field(default_factory=dict)  # "A5 B5" -> count | how many times this exact move was made
    
    # Direction stats
    directions: Dict[str, int] = field(default_factory=dict)  # N/S/E/W -> count | counts of move directions


@dataclass 
class GameStats:
    """Complete statistics for a game."""
    game_id: str
    total_turns: int = 0
    winner: Optional[int] = None
    loss_reason: str = ""
    game_duration_seconds: float = 0
    
    player_stats: Dict[int, PlayerStats] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.player_stats:
            self.player_stats = {
                0: PlayerStats(player_id=0),
                1: PlayerStats(player_id=1)
            }


def parse_csv_to_stats(csv_path: str) -> GameStats:
    """
    Parse game CSV and compute detailed statistics.
    
    Args:
        csv_path: Path to the game CSV file
        
    Returns:
        GameStats with computed statistics
    """
    if not os.path.exists(csv_path):
        return GameStats(game_id="unknown")
    
    game_id = os.path.basename(csv_path).replace(".csv", "")
    stats = GameStats(game_id=game_id)
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                player = int(row.get('player', 0))
                turn = int(row.get('turn', 0))
                move = row.get('move', '').strip()
                piece_type = row.get('piece_type', 'Unknown')
                from_pos = row.get('from_pos', '')
                
                if player not in stats.player_stats:
                    stats.player_stats[player] = PlayerStats(player_id=player)
                
                ps = stats.player_stats[player]
                ps.total_moves += 1
                ps.model_name = row.get('model_name', '')
                
                # Track piece usage
                if piece_type:
                    ps.moves_by_piece[piece_type] = ps.moves_by_piece.get(piece_type, 0) + 1
                
                # Track move repetitions
                if move:
                    ps.move_counts[move] = ps.move_counts.get(move, 0) + 1
                
                # Track direction (computed from positions)
                direction = _compute_direction(from_pos, row.get('to_pos', ''))
                if direction:
                    ps.directions[direction] = ps.directions.get(direction, 0) + 1
                
                stats.total_turns = max(stats.total_turns, turn)
                
            except Exception as e:
                continue
    
    return stats


def _compute_direction(from_pos: str, to_pos: str) -> str:
    """Compute move direction from positions."""
    if not from_pos or not to_pos:
        return ""
    try:
        src_row = ord(from_pos[0]) - ord('A')
        dst_row = ord(to_pos[0]) - ord('A')
        src_col = int(from_pos[1:])
        dst_col = int(to_pos[1:])
        
        if dst_row < src_row:
            return "N"
        elif dst_row > src_row:
            return "S"
        elif dst_col > src_col:
            return "E"
        elif dst_col < src_col:
            return "W"
    except:
        pass
    return ""


def format_stats_for_llm(stats: GameStats, player_to_analyze: int) -> str:
    """
    Format statistics into a structured summary for LLM analysis.
    """
    ps = stats.player_stats.get(player_to_analyze)
    if not ps:
        return "No data available for this player."
    
    lines = []
    lines.append(f"=== STRATEGO GAME ANALYSIS FOR PLAYER {player_to_analyze} ===")
    lines.append(f"Model: {ps.model_name}")
    lines.append(f"Total turns: {stats.total_turns}")
    lines.append(f"Player moves: {ps.total_moves}")
    
    # Winner info
    if stats.winner is not None:
        if stats.winner == player_to_analyze:
            lines.append(f"Result: WON")
        else:
            lines.append(f"Result: LOST")
            if stats.loss_reason:
                lines.append(f"Loss reason: {stats.loss_reason}")
    
    # Piece usage breakdown
    lines.append("\n--- PIECE USAGE ---")
    total_piece_moves = sum(ps.moves_by_piece.values()) or 1
    for piece, count in sorted(ps.moves_by_piece.items(), key=lambda x: -x[1])[:8]:
        pct = (count / total_piece_moves) * 100
        lines.append(f"  {piece}: {count} moves ({pct:.1f}%)")
    
    # Most repeated moves
    lines.append("\n--- REPEATED MOVES ---")
    top_repeated = sorted(ps.move_counts.items(), key=lambda x: -x[1])[:5]
    for move, count in top_repeated:
        if count >= 3:
            lines.append(f"  '{move}' repeated {count} times")
    
    # Direction analysis
    if ps.directions:
        lines.append("\n--- MOVE DIRECTIONS ---")
        total_dir = sum(ps.directions.values()) or 1
        for d in ['N', 'S', 'E', 'W']:
            count = ps.directions.get(d, 0)
            pct = (count / total_dir) * 100
            direction_name = {'N': 'Forward/North', 'S': 'Backward/South', 
                            'E': 'Right/East', 'W': 'Left/West'}.get(d, d)
            lines.append(f"  {direction_name}: {pct:.1f}%")
    
    return "\n".join(lines)


def analyze_with_llm(stats: GameStats, model_name: str = "mistral:7b") -> List[str]:
    """
    Send structured stats to LLM for Stratego-specific analysis.
    
    Returns list of feedback strings.
    """
    # Analyze player 0 (or the loser if there was one)
    player_to_analyze = 0
    if stats.winner == 0:
        player_to_analyze = 1  # Analyze the loser for improvement
    
    stats_summary = format_stats_for_llm(stats, player_to_analyze)
    
    prompt = f"""You are an expert Stratego strategy coach. Analyze this game data and provide specific, actionable feedback.

STRATEGO RULES REMINDER:
- Pieces ranked 1 (Spy) to 10 (Marshal). Higher rank wins battles.
- Scout (rank 2) can move multiple squares and should be used to probe enemy.
- Miner (rank 3) can defuse Bombs.
- Spy (rank 1) can defeat Marshal if attacking first.
- Flag is the objective - capture enemy's Flag to win.
- Bombs don't move and destroy any piece except Miner.

{stats_summary}

Based on this data, provide EXACTLY 3 specific feedback points. Each must:
1. Reference specific data from the stats (e.g., "Scout used 67% of the time")
2. Explain WHY it's a problem in Stratego strategy
3. Give a concrete improvement suggestion

Format each point on a new line starting with "•"
Be specific and use Stratego terminology correctly."""

    try:
        response = ollama.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3, "num_predict": 500}
        )
        
        content = response['message']['content']
        
        # Extract bullet points
        feedback = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                clean = line.lstrip('•-* ').strip()
                if clean and len(clean) > 20:
                    feedback.append(clean)
        
        return feedback[:5]
        
    except Exception as e:
        print(f"LLM analysis failed: {e}")
        return []


def analyze_and_update_prompt(
    csv_path: str,
    prompts_dir: str = "stratego/prompts",
    logs_dir: str = "logs",
    model_name: str = "mistral:7b",
    models_used: List[str] = None,
    game_duration_seconds: float = None,
    winner: Optional[int] = None,
    total_turns: int = 0
):
    """
    Analyze game with computed stats + LLM and update prompt.
    """
    from stratego.prompt_manager import PromptManager
    
    print("\n--- LLM Game Analysis ---")
    print(f"Analyzing: {csv_path}")
    
    # Step 1: Parse CSV and compute statistics
    stats = parse_csv_to_stats(csv_path)
    stats.winner = winner
    stats.game_duration_seconds = game_duration_seconds or 0
    
    if winner is not None:
        if stats.total_turns > 0:
            stats.loss_reason = "Flag captured or invalid move"
    
    # Step 2: Print computed stats
    print(f"\nGame Statistics:")
    print(f"  Total turns: {stats.total_turns}")
    print(f"  Winner: Player {winner}" if winner is not None else "  Winner: Draw/Unknown")
    
    for pid, ps in stats.player_stats.items():
        print(f"\n  Player {pid} ({ps.model_name}):")
        print(f"    Moves: {ps.total_moves}")
        if ps.moves_by_piece:
            top_piece = max(ps.moves_by_piece.items(), key=lambda x: x[1])
            print(f"    Most used piece: {top_piece[0]} ({top_piece[1]} times)")
    
    # Step 3: Get LLM feedback
    feedback = analyze_with_llm(stats, model_name)
    
    if not feedback:
        print("\nNo feedback generated.")
        return
    
    print(f"\nStrategic Feedback ({len(feedback)} points):")
    for fb in feedback:
        print(f"  • {fb}")
    
    # Step 4: Update prompt
    manager = PromptManager(prompts_dir, logs_dir)
    base_prompt = manager.get_base_prompt()
    
    new_prompt = base_prompt + "\n\n--- STRATEGIC IMPROVEMENTS (from last game analysis) ---\n"
    for fb in feedback:
        new_prompt += f"• {fb}\n"
    
    manager.update_prompt(
        new_prompt,
        reason=f"LLM analysis after {'win' if winner == 0 else 'loss'}: {len(feedback)} insights",
        models=models_used or [],
        mistakes=feedback,
        game_duration_seconds=game_duration_seconds,
        total_turns=total_turns,
        winner=winner
    )
    
    print("\nPrompt updated with strategic feedback.")
