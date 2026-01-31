"""Aggressive gameplay strategy for Stratego.

This strategy prioritizes attacking and forward movement to apply
pressure on the opponent and gain board control.
"""
from typing import List
from stratego.strategies.base import Strategy

class AggressiveStrategy(Strategy):
    """Strategy focused on aggressive play and attacking.
    
    Guidance provided:
    - Prioritize attacking enemy pieces
    - Focus on front-line pressure
    - Take calculated risks
    - Maintain offensive momentum
    """
    def get_context(self) -> str:
        return (
            "Play aggressively: prioritize attacking enemy pieces, "
            "especially those near your front line. "
            "Take calculated risks and pressure the opponent."
        )