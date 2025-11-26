"""
Prompt Optimizer: Improves prompts by analyzing specific mistakes from games.

Instead of generic tips, this adds concrete mistake descriptions:
- Exact moves that were repeated
- Back-and-forth patterns detected
- Piece overuse details
- Battle loss information
"""

from typing import List

from stratego.problem_tracker import MistakeSummary
from stratego.prompt_manager import PromptManager


def generate_mistake_statements(summary: MistakeSummary, max_mistakes: int = 5) -> List[str]:
    """
    Generate percentage-based feedback from game analysis.
    Uses general guidance, not specific moves.
    
    Args:
        summary: Mistake summary from the game
        max_mistakes: Maximum number of feedback points
        
    Returns:
        List of percentage-based feedback
    """
    mistakes = []
    total_turns = summary.total_turns or 1
    
    # 1. Calculate repetition rate
    total_repeated = sum(len(turns) for turns in summary.repeated_moves.values() if len(turns) >= 2)
    repetition_pct = (total_repeated / total_turns) * 100 if total_turns > 0 else 0
    
    if repetition_pct > 20:
        mistakes.append(
            f"Too many repeated moves ({repetition_pct:.0f}% of game). Try more variety in your moves."
        )
    elif repetition_pct > 10:
        mistakes.append(
            f"Some move repetition detected ({repetition_pct:.0f}%). Consider varying your strategy."
        )
    
    # 2. Back-and-forth rate
    back_forth_count = sum(count for _, _, count in summary.back_and_forth)
    back_forth_pct = (back_forth_count * 2 / total_turns) * 100 if total_turns > 0 else 0
    
    if back_forth_pct > 15:
        mistakes.append(
            f"High back-and-forth movement ({back_forth_pct:.0f}%). Commit to advancing instead of retreating."
        )
    
    # 3. Piece usage diversity
    if summary.piece_usage:
        total_moves = sum(summary.piece_usage.values())
        pieces_used = len(summary.piece_usage)
        max_usage = max(summary.piece_usage.values())
        max_piece = max(summary.piece_usage, key=summary.piece_usage.get)
        max_pct = (max_usage / total_moves) * 100 if total_moves > 0 else 0
        
        if max_pct > 40:
            mistakes.append(
                f"Over-reliance on {max_piece} ({max_pct:.0f}% of moves). Use more pieces strategically."
            )
        elif pieces_used < 5 and total_moves > 20:
            mistakes.append(
                f"Limited piece variety (only {pieces_used} piece types used). Engage more of your army."
            )
    
    # 4. Battle win rate
    total_battles = summary.battles_won + summary.battles_lost
    if total_battles > 0:
        win_rate = (summary.battles_won / total_battles) * 100
        if win_rate < 40:
            mistakes.append(
                f"Low battle win rate ({win_rate:.0f}%). Scout unknown pieces before attacking."
            )
    
    return mistakes[:max_mistakes]


def apply_mistakes_to_prompt(base_prompt: str, mistakes: List[str]) -> str:
    """
    Add mistake descriptions to the BASE prompt (replaces, not appends).
    
    Args:
        base_prompt: The base prompt text (clean, no old mistakes)
        mistakes: List of specific mistake descriptions from LAST game only
        
    Returns:
        Base prompt + new mistakes section
    """
    if not mistakes:
        return base_prompt
    
    # Start fresh from base prompt (no old mistakes)
    # Remove any existing mistakes section just in case
    marker = "--- LAST GAME FEEDBACK ---"
    if marker in base_prompt:
        base_prompt = base_prompt.split(marker)[0].rstrip()
    
    # Add new mistakes section
    result = base_prompt + f"\n\n{marker}\n"
    for mistake in mistakes:
        result += f"• {mistake}\n"
    
    return result


def improve_prompt_after_game(
    summary: MistakeSummary,
    prompts_dir: str = "stratego/prompts",
    logs_dir: str = "logs",
    models: list = None,
    game_duration_seconds: float = None
) -> bool:
    """
    Improve prompt based on specific mistakes from a completed game.
    Always logs game to history, updates prompt only if there are issues.
    
    Args:
        summary: Mistake summary from the game
        prompts_dir: Directory containing prompts
        logs_dir: Directory containing logs and fullgame_history.json
        models: List of model names that played the game
        game_duration_seconds: How long the game took in seconds
        
    Returns:
        True if prompt was updated, False otherwise
    """
    manager = PromptManager(prompts_dir, logs_dir)
    
    # Generate feedback (percentage-based)
    mistakes = generate_mistake_statements(summary)
    
    # Always start from BASE prompt
    base_prompt = manager.get_base_prompt()
    
    if mistakes:
        new_prompt = apply_mistakes_to_prompt(base_prompt, mistakes)
        reason = f"Game {summary.game_id}: {len(mistakes)} feedback points"
        print(f"\nPrompt updated with {len(mistakes)} feedback point(s):")
        for mistake in mistakes:
            print(f"  • {mistake}")
    else:
        new_prompt = base_prompt
        reason = f"Game {summary.game_id}: No issues detected"
        print("\nNo significant issues detected. Prompt reset to base.")
    
    # Always log the game to history
    manager.update_prompt(
        new_prompt, 
        reason, 
        models=models or [], 
        mistakes=mistakes,
        game_duration_seconds=game_duration_seconds,
        total_turns=summary.total_turns,
        winner=summary.winner
    )
    
    return len(mistakes) > 0
    
    return True


# Legacy function for backwards compatibility
def improve_prompt(log_dir: str, output_path: str, model_name: str = "phi3:14b"):
    """Legacy function - improvements now happen automatically after each game."""
    print("Note: Prompt improvements now happen automatically after each game.")


if __name__ == "__main__":
    # Test with sample data
    from stratego.problem_tracker import MistakeSummary
    
    test_summary = MistakeSummary(
        game_id="test_game",
        total_turns=15,
        repeated_moves={
            "[G0 F0]": [4, 6, 8],
            "[D4 E4]": [2, 5]
        },
        back_and_forth=[("F0", "G0", 3)],
        piece_usage={"Scout": 10, "Miner": 2, "Captain": 1},
        battle_details=[
            {"turn": 5, "piece": "Scout", "outcome": "lost", "player": 0},
            {"turn": 8, "piece": "Captain", "outcome": "lost", "player": 0},
            {"turn": 10, "piece": "Miner", "outcome": "won", "player": 0}
        ],
        battles_won=1,
        battles_lost=2
    )
    
    mistakes = generate_mistake_statements(test_summary)
    print("Generated mistakes:")
    for m in mistakes:
        print(f"  - {m}")
