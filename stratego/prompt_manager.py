"""
PromptManager: Simple prompt versioning and updates.
"""

from __future__ import annotations
import os
import json
import shutil
from datetime import datetime


class PromptManager:
    """
    Manages prompt versions and updates.
    
    Files:
        prompts/current_prompt.txt    (active prompt)
        prompts/base_prompt.txt       (original/fallback)
        logs/fullgame_history.json    (game log with prompts)
    """
    
    DEFAULT_PROMPT = """You are a strategic Stratego AI. The game rules are already provided.

STRATEGY FOCUS:
- Vary your moves - don't repeat the same move multiple times
- Use different pieces, not just one piece repeatedly
- Be cautious when attacking unknown pieces
- Protect high-value pieces (Marshal, General)
- Use Scouts to gather information before committing valuable pieces

OUTPUT:
- Respond with ONLY the move in format [SRC DST]
- No explanations, no reasoning, just the move
- Example: [D4 E4]"""
    
    def __init__(self, prompts_dir: str, logs_dir: str = "logs"):
        self.prompts_dir = prompts_dir
        self.logs_dir = logs_dir
        self.current_path = os.path.join(prompts_dir, "current_prompt.txt")
        self.base_path = os.path.join(prompts_dir, "base_prompt.txt")
        self.history_path = os.path.join(logs_dir, "fullgame_history.json")
        
        os.makedirs(prompts_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
        self._ensure_base_prompt()
    
    def _ensure_base_prompt(self):
        """Create base prompt if it doesn't exist."""
        if not os.path.exists(self.base_path):
            with open(self.base_path, "w", encoding="utf-8") as f:
                f.write(self.DEFAULT_PROMPT)
    
    def get_base_prompt(self) -> str:
        """Get the base prompt (without any game-specific additions)."""
        if os.path.exists(self.base_path):
            with open(self.base_path, "r", encoding="utf-8") as f:
                return f.read()
        return self.DEFAULT_PROMPT

    @staticmethod
    def extract_improvements(prompt_text: str) -> list[str]:
        """Pull the strategic improvements section (lines starting with bullets)."""
        if not prompt_text:
            return []
        lines = prompt_text.splitlines()
        improvements: list[str] = []
        in_section = False
        for line in lines:
            if line.strip().startswith("--- STRATEGIC IMPROVEMENTS"):
                in_section = True
                continue
            if in_section:
                stripped = line.strip()
                if stripped.startswith(("??", "-", "•", "*")):
                    cleaned = stripped.lstrip("??•-* ").strip()
                    if cleaned:
                        improvements.append(f"• {cleaned}")
        return improvements

    @staticmethod
    def merge_improvements(existing: list[str], new: list[str], limit: int = 20) -> list[str]:
        """Deduplicate improvements while keeping order; cap length to avoid prompt bloat."""
        merged: list[str] = []
        seen = set()

        def _norm(s: str) -> str:
            s_clean = s.lstrip("•-*? ").strip().lower()
            return " ".join(s_clean.split())

        for item in (existing or []) + (new or []):
            if not item:
                continue
            key = _norm(item)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item.strip())
            if len(merged) >= limit:
                break
        return merged

    @staticmethod
    def build_prompt(base_prompt: str, improvements: list[str]) -> str:
        """Reconstruct prompt with a merged improvements section."""
        section = ""
        if improvements:
            section = "\n\n--- STRATEGIC IMPROVEMENTS (from past games) ---\n" + "\n".join(improvements)
        return base_prompt.rstrip() + section
    
    def get_current_prompt(self) -> str:
        """Get the current active prompt (base + last game feedback)."""
        if os.path.exists(self.current_path):
            with open(self.current_path, "r", encoding="utf-8") as f:
                return f.read()
        return self.get_base_prompt()
    
    def update_prompt(self, new_prompt: str, reason: str = "", models: list = None, 
                       mistakes: list = None, game_duration_seconds: float = None,
                       total_turns: int = None, winner: int = None):
        """
        Update the current prompt and log the change.
        
        Args:
            new_prompt: The new prompt text
            reason: Why the prompt was updated
            models: List of models that played the game
            mistakes: List of mistake strings that were added
            game_duration_seconds: How long the game took in seconds
            total_turns: Total number of turns in the game
            winner: Player ID who won (0 or 1), None for draw
        """
        # Backup current
        if os.path.exists(self.current_path):
            backup = self.current_path.replace(".txt", "_prev.txt")
            shutil.copy2(self.current_path, backup)
        
        # Save new prompt
        with open(self.current_path, "w", encoding="utf-8") as f:
            f.write(new_prompt)
        
        # Log the update
        self._log_update(reason, new_prompt, models, mistakes, game_duration_seconds, total_turns, winner)
    
    def _log_update(self, reason: str, prompt_text: str = "", models: list = None, 
                    mistakes: list = None, game_duration_seconds: float = None,
                    total_turns: int = None, winner: int = None):
        """Log game and prompt update to history with full details."""
        history = []
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except:
                history = []
        
        # Format duration nicely
        duration_str = ""
        if game_duration_seconds is not None:
            minutes = int(game_duration_seconds // 60)
            seconds = int(game_duration_seconds % 60)
            duration_str = f"{minutes}m {seconds}s"
        
        entry = {
            "game_number": len(history) + 1,
            "timestamp": datetime.now().isoformat(),
            "models": models or [],
            "winner": winner,
            "total_turns": total_turns,
            "game_duration": duration_str,
            "game_duration_seconds": round(game_duration_seconds, 2) if game_duration_seconds else None,
            "mistakes_detected": len(mistakes) if mistakes else 0,
            "mistakes_added": mistakes or [],
            "reason": reason,
            "prompt_text": prompt_text,
            "prompt_length": len(prompt_text)
        }
        history.append(entry)
        
        # Keep last 50 entries
        history = history[-50:]
        
        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    
    def reset_to_base(self):
        """Reset current prompt to base prompt."""
        if os.path.exists(self.base_path):
            shutil.copy2(self.base_path, self.current_path)
            with open(self.base_path, "r", encoding="utf-8") as f:
                base_text = f.read()
            self._log_update("Reset to base prompt", base_text, [], [], None, None, None)
