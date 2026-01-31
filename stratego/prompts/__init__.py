"""Prompt management system for Stratego AI agents.

This package provides structured prompt templates and presets for guiding
LLM agents during gameplay. Prompts include strategic guidance, rule
enforcement, and output formatting instructions.

Components:
    - PromptPack: Data structure holding system and guidance prompts
    - get_prompt_pack(): Factory function for loading prompt presets
    - presets.py: Predefined prompt configurations (BASE, CONCISE, ADAPTIVE)
    - schemas.py: Validation and analysis tools (planned)

The prompt system is designed to be modular and version-controlled,
allowing for iterative improvement based on game performance metrics.
"""
from .presets import PromptPack, get_prompt_pack, BASE, CONCISE, ADAPTIVE

__all__ = ["PromptPack", "get_prompt_pack", "BASE", "CONCISE", "ADAPTIVE"]