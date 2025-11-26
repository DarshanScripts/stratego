"""
Stratego AI Game Package
"""

from stratego.problem_tracker import ProblemTracker, MistakeSummary
from stratego.prompt_manager import PromptManager
from stratego.prompt_optimizer import improve_prompt_after_game

__all__ = [
    "ProblemTracker",
    "MistakeSummary", 
    "PromptManager",
    "improve_prompt_after_game"
]